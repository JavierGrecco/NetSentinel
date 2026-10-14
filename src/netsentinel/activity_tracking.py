"""Seguimiento de actividad basado en metadatos explícitos y fuentes autorizadas.

Este módulo no captura paquetes por sí mismo ni lee contenido HTTPS, credenciales,
cookies o cuerpos HTTP. Las URLs de navegación se guardan normalizadas, no como
la URL original: se eliminan fragmentos y parámetros conocidos sensibles y se
redactan algunos identificadores reconocibles en la ruta. Otros segmentos o
parámetros desconocidos pueden persistir. Las fuentes compatibles envían metadatos
durante una sesión opt-in o mediante importación explícita.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from . import activity_filters, activity_import_service, activity_read_service, activity_repository, database
from .activity_catalog import EVENT_SOURCES, EVENT_TYPES, PROTOCOLS, SESSION_SOURCES
from .activity_privacy import _domain, _email_address_list, _safe_page_url

class InvalidCollectorToken(PermissionError):
    """El secreto de una sesión de recopilación no coincide."""


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
    """Mantiene el punto de entrada histórico y delega la validación pura."""
    return activity_filters.activity_filter_values(event_type, from_date, to_date, source)

def _activity_delete_scope(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Mantiene el punto de entrada histórico para construir un alcance seguro."""
    return activity_filters.activity_delete_scope(
        device_id, event_type, from_date, to_date, source
    )

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
    """Conserva la API pública y delega la consulta y el formato del CSV."""
    return activity_read_service.export_activity_csv(
        device_id=device_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        source=source,
    )

def get_activity(
    device_id: int | None = None,
    limit: int = 100,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Conserva el contrato que consume la API y delega el modelo de lectura."""
    return activity_read_service.get_activity(
        device_id=device_id,
        limit=limit,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        source=source,
    )
