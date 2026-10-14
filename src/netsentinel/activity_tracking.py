"""Seguimiento de actividad basado en metadatos explícitos y fuentes autorizadas.

Este módulo no captura paquetes por sí mismo ni lee contenido HTTPS, credenciales,
cookies o cuerpos HTTP. Las URLs de navegación se guardan normalizadas, no como
la URL original: se eliminan fragmentos y parámetros conocidos sensibles y se
redactan algunos identificadores reconocibles en la ruta. Otros segmentos o
parámetros desconocidos pueden persistir. Las fuentes compatibles envían metadatos
durante una sesión opt-in o mediante importación explícita.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from . import activity_import_service, activity_repository, database
from .csv_safety import spreadsheet_safe_text as _csv_safe_text
from .activity_privacy import _domain, _email_address_list, _safe_page_url

class InvalidCollectorToken(PermissionError):
    """El secreto de una sesión de recopilación no coincide."""


SESSION_SOURCES = {"router_dns", "router_flow", "device_agent"}
EVENT_SOURCES = SESSION_SOURCES
EVENT_TYPES = {"dns_query", "connection", "tls_sni", "app_usage", "blocked", "page_visit", "search_query", "email_metadata"}
PROTOCOLS = {"tcp", "udp", "quic", "icmp", "other"}
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_timestamp(value: str | None) -> str:
    if not value:
        return _iso(_now())
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("La fecha debe ser ISO 8601, por ejemplo 2026-10-11T18:30:00Z.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now = _now()
    if parsed < now - timedelta(days=365):
        raise ValueError("La fecha no puede tener más de 365 días de antigüedad.")
    if parsed > now + timedelta(minutes=5):
        raise ValueError("La fecha del evento no puede estar más de cinco minutos en el futuro.")
    return _iso(parsed)


def normalize_event(payload: dict[str, Any], *, source_override: str | None = None) -> dict[str, Any]:
    """Valida un evento de metadatos; rechaza silenciosamente no es una opción."""
    event_type = str(payload.get("event_type", "")).strip().lower()
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Tipo de evento no admitido. Usá: {', '.join(sorted(EVENT_TYPES))}.")
    source = source_override or str(payload.get("source", "")).strip().lower()
    if source not in EVENT_SOURCES and source != "manual_import":
        raise ValueError("Fuente no admitida.")
    domain = _domain(payload.get("domain"))
    page_url = _safe_page_url(payload.get("page_url"))
    search_engine = payload.get("search_engine")
    search_engine = str(search_engine).strip()[:40] if search_engine not in (None, "") else None
    if search_engine and any(ord(ch) < 32 for ch in search_engine):
        raise ValueError("search_engine no puede contener caracteres de control.")
    search_terms = payload.get("search_terms")
    search_terms = " ".join(str(search_terms).split())[:500] if search_terms not in (None, "") else None
    email_provider = payload.get("email_provider")
    email_provider = " ".join(str(email_provider).split())[:60] if email_provider not in (None, "") else None
    if email_provider and any(ord(ch) < 32 for ch in email_provider):
        raise ValueError("email_provider no puede contener caracteres de control.")
    email_from_list = _email_address_list(payload.get("email_from"), field="email_from", required=event_type == "email_metadata")
    email_to_list = _email_address_list(payload.get("email_to"), field="email_to", required=event_type == "email_metadata")
    email_subject = payload.get("email_subject")
    if email_subject not in (None, ""):
        raw_subject = str(email_subject)
        if any(ord(ch) < 32 and not ch.isspace() for ch in raw_subject):
            raise ValueError("email_subject contiene caracteres de control.")
        email_subject = " ".join(raw_subject.split())[:200]
    else:
        email_subject = None
    if event_type == "email_metadata":
        if source_override != "manual_import":
            raise ValueError("Los metadatos de correo solo se admiten mediante importación explícita de registros autorizados.")
        if len(email_from_list) != 1 or not email_to_list:
            raise ValueError("El evento email_metadata requiere un emisor y al menos un destinatario.")
    if event_type == "page_visit" and not page_url:
        raise ValueError("El evento page_visit requiere page_url.")
    if event_type == "search_query" and (not search_engine or not search_terms):
        raise ValueError("El evento search_query requiere search_engine y search_terms.")
    if page_url and not domain:
        page_host = urlsplit(page_url).hostname
        if page_host:
            try:
                domain = _domain(page_host)
            except ValueError:
                try:
                    ipaddress.ip_address(page_host)
                    domain = None
                except ValueError:
                    raise
    destination_ip = payload.get("destination_ip")
    if destination_ip is not None and str(destination_ip).strip():
        try:
            destination_ip = str(ipaddress.ip_address(str(destination_ip).strip()))
        except ValueError as exc:
            raise ValueError("destination_ip debe ser una dirección IPv4 o IPv6 válida.") from exc
    else:
        destination_ip = None
    port = payload.get("destination_port")
    if port in ("", None):
        port = None
    else:
        try:
            port = int(port)
        except (ValueError, TypeError) as exc:
            raise ValueError("destination_port debe ser un entero entre 1 y 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("destination_port debe ser un entero entre 1 y 65535.")
    protocol = payload.get("protocol")
    protocol = str(protocol).strip().lower() if protocol not in (None, "") else None
    if protocol is not None and protocol not in PROTOCOLS:
        raise ValueError(f"Protocolo no admitido. Usá: {', '.join(sorted(PROTOCOLS))}.")
    app_name = payload.get("app_name")
    app_name = str(app_name).strip()[:100] if app_name not in (None, "") else None
    if app_name and any(ord(ch) < 32 for ch in app_name):
        raise ValueError("app_name no puede contener caracteres de control.")
    if event_type in {"dns_query", "tls_sni"} and not domain:
        raise ValueError(f"El evento {event_type} requiere un nombre DNS.")
    if event_type == "connection" and not (destination_ip or domain):
        raise ValueError("Una conexión requiere destination_ip o domain.")
    if event_type == "app_usage" and not app_name:
        raise ValueError("El evento app_usage requiere app_name.")
    if event_type == "email_metadata" and source != "manual_import":
        raise ValueError("La actividad de correo no se admite desde fuentes de red en tiempo real.")
    blocked_value = payload.get("blocked", False)
    if isinstance(blocked_value, str):
        normalized_blocked = blocked_value.strip().lower()
        if normalized_blocked not in {"", "0", "1", "true", "false", "yes", "no"}:
            raise ValueError("blocked debe ser verdadero o falso.")
        blocked = normalized_blocked in {"1", "true", "yes"}
    else:
        blocked = bool(blocked_value)
    return {
        "observed_at": _parse_timestamp(payload.get("observed_at")),
        "event_type": event_type,
        "source": source,
        "domain": domain,
        "destination_ip": destination_ip,
        "destination_port": port,
        "protocol": protocol,
        "app_name": app_name,
        "page_url": page_url,
        "search_engine": search_engine,
        "search_terms": search_terms,
        "email_provider": email_provider,
        "email_from": "; ".join(email_from_list) if email_from_list else None,
        "email_to": "; ".join(email_to_list) if email_to_list else None,
        "email_subject": email_subject,
        "blocked": int(blocked or event_type == "blocked"),
    }


def _cleanup(db) -> int:
    """Delegación temporal al repositorio mientras se migra el resto del dominio."""
    return activity_repository.cleanup(db, now=_now())


def start_session(device_id: int, duration_minutes: int, source_mode: str) -> dict[str, Any]:
    """Abre una ventana temporal y devuelve un token de ingestión de un solo vistazo."""
    if not 5 <= int(duration_minutes) <= 720:
        raise ValueError("La duración debe estar entre 5 minutos y 12 horas.")
    source_mode = source_mode.strip().lower()
    if source_mode not in SESSION_SOURCES:
        raise ValueError("Fuente elegible: router_dns, router_flow o device_agent.")
    now = _now()
    started_at = _iso(now)
    ends_at = _iso(now + timedelta(minutes=int(duration_minutes)))
    collector_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(collector_token.encode("utf-8")).hexdigest()
    with database.connect() as db:
        _cleanup(db)
        result = activity_repository.start_session(
            db,
            device_id=device_id,
            source_mode=source_mode,
            started_at=started_at,
            ends_at=ends_at,
            token_hash=token_hash,
        )
    result["collector_token"] = collector_token
    result["token_note"] = "Copiá este token ahora. Solo se almacena su hash y no volverá a mostrarse."
    return result


def stop_session(session_id: int) -> dict[str, Any] | None:
    now = _iso(_now())
    with database.connect() as db:
        _cleanup(db)
        return activity_repository.stop_session(db, session_id, now=now)


def ingest_event(
    session_id: int, device_id: int, collector_token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Guarda metadatos si sesión, dispositivo, fuente, plazo y token coinciden."""
    event = normalize_event(payload)
    now = _iso(_now())
    supplied_hash = hashlib.sha256(collector_token.encode("utf-8")).hexdigest()
    with database.connect() as db:
        _cleanup(db)
        session = activity_repository.get_session_for_device(db, session_id, device_id)
        if session is None:
            raise LookupError("No existe una sesión para ese dispositivo.")
        if not hmac.compare_digest(session["collector_token_hash"], supplied_hash):
            raise InvalidCollectorToken("El token de recopilación no es válido.")
        if session["status"] != "active" or session["ends_at"] <= now:
            raise PermissionError("La sesión no está activa; iniciá otra ventana de seguimiento.")
        if event["source"] != session["source_mode"]:
            raise ValueError("La fuente del evento no coincide con la fuente elegida para esta sesión.")

        # Live collectors can deliver delayed telemetry. Do not accept an event
        # older than the active retention window only to delete it on the next read.
        retention_days = activity_repository.get_retention_days(db)
        retention_cutoff = _iso(_now() - timedelta(days=retention_days))
        if event["observed_at"] < retention_cutoff:
            raise ValueError(
                f"La fecha queda fuera de la retención configurada de {retention_days} día(s). "
                "No se guardó el evento."
            )

        return activity_repository.insert_event(
            db, session_id, device_id, event, received_at=now
        )


def import_csv(device_id: int, csv_data: str, *, preview: bool = False) -> dict[str, Any]:
    """Delega la validación CSV al servicio y conserva la firma pública actual."""
    return activity_import_service.import_csv(
        device_id,
        csv_data,
        preview=preview,
        normalize_event=normalize_event,
    )


def preview_csv(device_id: int, csv_data: str) -> dict[str, Any]:
    """Valida y muestra una vista previa de CSV sin almacenar los eventos."""
    return import_csv(device_id, csv_data, preview=True)


def update_retention(retention_days: int) -> dict[str, Any]:
    if not 1 <= int(retention_days) <= 90:
        raise ValueError("La retención debe ser de 1 a 90 días.")
    return activity_repository.update_retention(int(retention_days), now=_now())


def _activity_filter_values(
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[list[str], list[Any]]:
    """Validate event type/source and inclusive UTC calendar-date filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if event_type not in (None, ""):
        normalized_type = str(event_type).strip().lower()
        if normalized_type not in EVENT_TYPES:
            raise ValueError("El tipo de evento no es válido.")
        clauses.append("event_type = ?")
        params.append(normalized_type)

    if source not in (None, ""):
        normalized_source = str(source).strip().lower()
        if normalized_source not in EVENT_SOURCES and normalized_source != "manual_import":
            raise ValueError("La fuente de actividad no es válida.")
        clauses.append("source = ?")
        params.append(normalized_source)

    parsed_from: datetime | None = None
    parsed_to: datetime | None = None
    for raw, name in ((from_date, "from_date"), (to_date, "to_date")):
        if raw in (None, ""):
            continue
        try:
            parsed = datetime.strptime(str(raw), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} debe tener formato AAAA-MM-DD.") from exc
        if name == "from_date":
            parsed_from = parsed
        else:
            parsed_to = parsed

    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    if parsed_from:
        clauses.append("observed_at >= ?")
        params.append(_iso(parsed_from))
    if parsed_to:
        clauses.append("observed_at < ?")
        params.append(_iso(parsed_to + timedelta(days=1)))
    return clauses, params


def _activity_delete_scope(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Build a scoped DELETE/COUNT predicate; an unbounded operation is never allowed."""
    if device_id is None and event_type in (None, "") and from_date in (None, "") and to_date in (None, "") and source in (None, ""):
        raise ValueError("Elegí al menos un alcance: dispositivo, tipo de evento, fuente o fechas.")
    clauses, params = _activity_filter_values(event_type, from_date, to_date, source)
    if device_id is not None:
        if int(device_id) < 1:
            raise ValueError("device_id debe ser un entero positivo.")
        clauses.insert(0, "device_id = ?")
        params.insert(0, int(device_id))
    return " WHERE " + " AND ".join(clauses), tuple(params)


def preview_delete_activity(
    device_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Count matching activity rows without writing or running retention cleanup."""
    where_sql, params = _activity_delete_scope(device_id, event_type, from_date, to_date, source)
    count = activity_repository.count_activity_scope(
        where_sql, params, device_id=device_id
    )
    return {
        "device_id": device_id,
        "event_type": event_type or None,
        "from_date": from_date or None,
        "to_date": to_date or None,
        "source": source or None,
        "matching_events": count,
        "confirmation_required": f"BORRAR {count}",
        "deleted": False,
        "note": "Vista previa únicamente: no se borró ningún evento.",
    }


def delete_activity(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    confirmation: str,
    source: str | None = None,
) -> dict[str, Any]:
    """Delete only a scoped selection after matching the exact current count."""
    where_sql, params = _activity_delete_scope(device_id, event_type, from_date, to_date, source)
    if not isinstance(confirmation, str) or len(confirmation) > 40:
        raise PermissionError("La frase de confirmación no es válida.")

    deleted = activity_repository.delete_activity_scope(
        where_sql, params, device_id=device_id, confirmation=confirmation
    )
    return {
        "deleted_events": deleted,
        "device_id": device_id,
        "event_type": event_type or None,
        "from_date": from_date or None,
        "to_date": to_date or None,
        "source": source or None,
        "note": "Se borraron únicamente los eventos que coincidían con el alcance confirmado.",
    }


def export_activity_csv(
    device_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 10000,
    source: str | None = None,
) -> str:
    """Export up to 10,000 filtered activity metadata rows as formula-safe CSV."""
    clauses, filter_params = _activity_filter_values(event_type, from_date, to_date, source)
    if device_id is not None:
        if int(device_id) < 1:
            raise ValueError("device_id debe ser un entero positivo.")
        clauses.insert(0, "e.device_id = ?")
        filter_params.insert(0, int(device_id))
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    with database.connect() as db:
        _cleanup(db)
        if device_id is not None and db.execute(
            "SELECT 1 FROM devices WHERE id = ?", (device_id,)
        ).fetchone() is None:
            raise LookupError("No se encontró el dispositivo.")
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address
                FROM activity_events e
                JOIN devices d ON d.id = e.device_id
                {where_sql}
                ORDER BY e.observed_at DESC, e.id DESC
                LIMIT ?""",
            (*filter_params, max(1, min(int(limit), 10000))),
        ).fetchall()

    buffer = io.StringIO(newline="")
    fields = [
        "observed_at", "event_type", "device_id", "device_name", "ip_address", "source",
        "domain", "page_url", "search_engine", "search_terms", "destination_ip",
        "destination_port", "protocol", "app_name", "blocked", "email_provider",
        "email_from", "email_to", "email_subject",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for event in events:
        row = {
            "observed_at": event["observed_at"],
            "event_type": event["event_type"],
            "device_id": event["device_id"],
            "device_name": event["display_name"],
            "ip_address": event["ip_address"],
            "source": event["source"],
            "domain": event["domain"],
            "page_url": event["page_url"],
            "search_engine": event["search_engine"],
            "search_terms": event["search_terms"],
            "destination_ip": event["destination_ip"],
            "destination_port": event["destination_port"],
            "protocol": event["protocol"],
            "app_name": event["app_name"],
            "blocked": event["blocked"],
            "email_provider": event["email_provider"],
            "email_from": event["email_from"],
            "email_to": event["email_to"],
            "email_subject": event["email_subject"],
        }
        writer.writerow({key: _csv_safe_text(value) for key, value in row.items()})
    return "\ufeff" + buffer.getvalue()


def get_activity(
    device_id: int | None = None,
    limit: int = 100,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    event_clauses, event_params = _activity_filter_values(event_type, from_date, to_date, source)
    if device_id is not None:
        if int(device_id) < 1:
            raise ValueError("device_id debe ser un entero positivo.")
        event_clauses.insert(0, "e.device_id = ?")
        event_params.insert(0, int(device_id))
    event_filter = "WHERE " + " AND ".join(event_clauses) if event_clauses else ""
    with database.connect() as db:
        _cleanup(db)
        params: tuple[Any, ...] = (device_id,) if device_id is not None else ()
        if device_id is not None and db.execute("SELECT 1 FROM devices WHERE id=?", (device_id,)).fetchone() is None:
            raise LookupError("No se encontró el dispositivo.")
        session_filter = "WHERE s.device_id = ?" if device_id is not None else ""
        sessions = db.execute(
            f"""SELECT s.id, s.device_id, s.source_mode, s.started_at, s.ends_at, s.stopped_at, s.status,
                       d.display_name, d.ip_address, d.mac_address
                FROM activity_sessions s JOIN devices d ON d.id=s.device_id
                {session_filter} ORDER BY s.started_at DESC, s.id DESC LIMIT 100""",
            params,
        ).fetchall()
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address, d.mac_address
                FROM activity_events e JOIN devices d ON d.id=e.device_id
                {event_filter} ORDER BY e.observed_at DESC, e.id DESC LIMIT ?""",
            (*event_params, max(1, min(int(limit), 500))),
        ).fetchall()
        domain_filter = "WHERE domain IS NOT NULL AND domain <> ''" if device_id is None else "WHERE device_id = ? AND domain IS NOT NULL AND domain <> ''"
        domain_params: tuple[Any, ...] = () if device_id is None else (device_id,)
        top_domains = db.execute(
            f"""SELECT domain, COUNT(*) AS events, MAX(observed_at) AS last_seen
                FROM activity_events {domain_filter}
                GROUP BY domain ORDER BY events DESC, last_seen DESC LIMIT 15""",
            domain_params,
        ).fetchall()
        blocked_params: tuple[Any, ...] = () if device_id is None else (device_id,)
        blocked_count = db.execute(
            "SELECT COUNT(*) FROM activity_events WHERE blocked = 1" + ("" if device_id is None else " AND device_id = ?"),
            blocked_params,
        ).fetchone()[0]
        retention_days = activity_repository.get_retention_days(db)
        session_count_sql = "SELECT COUNT(*) FROM activity_sessions WHERE status='active'" + ("" if device_id is None else " AND device_id = ?")
        event_count_sql = "SELECT COUNT(*) FROM activity_events" + ("" if device_id is None else " WHERE device_id = ?")
        active_count = db.execute(session_count_sql, blocked_params).fetchone()[0]
        event_count = db.execute(event_count_sql, blocked_params).fetchone()[0]
        devices = db.execute(
            "SELECT id, display_name, ip_address, mac_address FROM devices ORDER BY display_name, ip_address"
        ).fetchall()
    return {
        "sessions": [dict(row) for row in sessions],
        "events": [dict(row) for row in events],
        "top_domains": [dict(row) for row in top_domains],
        "blocked_events": int(blocked_count),
        "devices": [dict(row) for row in devices],
        "retention_days": retention_days,
        "active_sessions": int(active_count),
        "total_events": int(event_count),
        "sources": sorted(SESSION_SOURCES),
        "activity_sources": sorted(EVENT_SOURCES | {"manual_import"}),
        "event_types": sorted(EVENT_TYPES),
        "note": (
            "La aplicación no captura tráfico por sí misma. El correo solo se incorpora como metadatos importados "
            "de registros autorizados, sin cuerpos ni adjuntos. Las sesiones habilitan una ventana para que un adaptador "
            "autorizado envíe metadatos; la importación CSV añade registros históricos. No se guardan credenciales, "
            "cookies ni cargas útiles. Las URLs de navegación se normalizan: se quitan fragmentos y parámetros "
            "conocidos sensibles, y se redactan algunos identificadores reconocibles en la ruta; otros segmentos o "
            "parámetros no reconocidos pueden persistir. DNS/SNI/conexiones son indicios de tráfico, no prueba de "
            "que una persona haya usado una cuenta o visto una página concreta."
        ),
    }
