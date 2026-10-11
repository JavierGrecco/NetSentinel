"""Seguimiento familiar basado solo en metadatos explícitos y fuentes autorizadas.

Este módulo no captura paquetes por sí mismo ni lee contenido HTTPS, credenciales,
cookies, cuerpos HTTP ni rutas completas de URL. Las fuentes externas compatibles
deben normalizar y enviar eventos de metadatos a la API durante una sesión opt-in.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import ipaddress
import re
import secrets
from datetime import datetime, timedelta, timezone
from email.utils import getaddresses
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import database

class InvalidCollectorToken(PermissionError):
    """El secreto de una sesión de recopilación no coincide."""


SESSION_SOURCES = {"router_dns", "router_flow", "device_agent"}
EVENT_SOURCES = SESSION_SOURCES
EVENT_TYPES = {"dns_query", "connection", "tls_sni", "app_usage", "blocked", "page_visit", "search_query", "email_metadata"}
PROTOCOLS = {"tcp", "udp", "quic", "icmp", "other"}
CSV_FIELDS = {
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "blocked", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject",
}
SENSITIVE_QUERY_KEY = re.compile(
    r"(?:access.?token|refresh.?token|id.?token|password|passwd|secret|authorization|"
    r"username|email|phone|session|sid|csrf|nonce|signature|"
    r"(^|_)(?:token|auth|code|state|otp|jwt|key|user|account|customer)(_|$))",
    re.IGNORECASE,
)
SEARCH_QUERY_KEYS = {"q", "query", "text", "wd", "word", "search_query", "search"}
TRACKING_QUERY_KEYS = {"fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid"}
SENSITIVE_HEADERS = {
    "url", "full_url", "path", "query_string", "username", "user",
    "password", "passwd", "token", "cookie", "authorization", "payload",
    "body", "message", "email_body", "message_body", "body_text", "body_html",
    "content", "email_message", "request_body", "response_body", "attachment",
    "attachments", "attachment_content", "message_content",
}


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


def _domain(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    raw = value.strip().rstrip(".")
    if len(raw) > 253 or any(ch in raw for ch in "/\\@?#") or "://" in raw:
        raise ValueError("El campo domain acepta solo un nombre DNS, no una URL ni una ruta.")
    try:
        # IP literals are represented in destination_ip, not as DNS names.
        ipaddress.ip_address(raw)
    except ValueError:
        pass
    else:
        raise ValueError("Usá destination_ip para direcciones IP; domain debe ser un nombre DNS.")
    try:
        normalized = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("El nombre DNS no es válido.") from exc
    labels = normalized.split(".")
    if any(
        not label or len(label) > 63
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        raise ValueError("El nombre DNS contiene etiquetas no válidas.")
    return normalized


def _safe_page_url(value: str | None) -> str | None:
    """Normalize an HTTP(S) URL; remove fragments, search terms and secret-like parameters."""
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if len(raw) > 4096 or any(ord(ch) < 32 for ch in raw):
        raise ValueError("page_url supera el límite o contiene caracteres de control.")
    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("page_url no es una URL válida.") from exc
    if scheme not in {"http", "https"} or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("page_url debe ser una URL HTTP(S) sin credenciales embebidas.")
    try:
        ipaddress.ip_address(hostname)
        normalized_host = hostname.lower()
    except ValueError:
        try:
            normalized_host = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("El host de page_url no es válido.") from exc
    if len(normalized_host) > 253:
        raise ValueError("El host de page_url es demasiado largo.")
    netloc = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    if port is not None and port != (443 if scheme == "https" else 80):
        netloc += f":{port}"
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=200)
    safe_pairs = []
    for key, item_value in query_pairs:
        normalized_key = re.sub(r"[^a-z0-9_]", "", key.lower())
        if SENSITIVE_QUERY_KEY.search(normalized_key) or normalized_key in TRACKING_QUERY_KEYS or normalized_key.startswith("utm_"):
            continue
        if normalized_key in SEARCH_QUERY_KEYS:
            continue
        safe_pairs.append((key, item_value))
    safe = urlunsplit((scheme, netloc, parsed.path or "/", urlencode(safe_pairs, doseq=True), ""))
    if len(safe) > 2048:
        raise ValueError("page_url supera los 2048 caracteres permitidos.")
    return safe


def _email_address_list(value: str | None, *, field: str, required: bool) -> list[str]:
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"{field} es obligatorio para el evento de correo.")
        return []
    raw = str(value).strip()
    if len(raw) > 1500 or any(ord(ch) < 32 and ch not in "\\t\\r\\n" for ch in raw):
        raise ValueError(f"{field} supera el límite o contiene caracteres de control.")
    addresses = getaddresses([raw.replace(";", ",")])
    normalized: list[str] = []
    for _display, address in addresses:
        address = address.strip()
        if not address or "@" not in address:
            continue
        local, domain = address.rsplit("@", 1)
        if not local or len(local) > 64 or not domain or "." not in domain or len(address) > 254:
            continue
        try:
            domain = domain.encode("idna").decode("ascii").lower()
        except UnicodeError:
            continue
        if any(ch.isspace() for ch in local) or any(ch in local for ch in "<>,;"):
            continue
        address = f"{local}@{domain}"
        if address not in normalized:
            normalized.append(address)
    if not normalized and required:
        raise ValueError(f"{field} no contiene una dirección de correo válida.")
    if len(normalized) > 10:
        raise ValueError(f"{field} admite como máximo 10 direcciones por evento.")
    return normalized


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
    email_subject = " ".join(str(email_subject).replace("\\r", " ").replace("\\n", " ").split())[:200] if email_subject not in (None, "") else None
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
    row = db.execute("SELECT retention_days FROM activity_settings WHERE id = 1").fetchone()
    retention_days = int(row["retention_days"]) if row else 7
    cutoff = _iso(_now() - timedelta(days=retention_days))
    cursor = db.execute("DELETE FROM activity_events WHERE observed_at < ?", (cutoff,))
    db.execute(
        "UPDATE activity_sessions SET status = 'expired' WHERE status = 'active' AND ends_at <= ?",
        (_iso(_now()),),
    )
    db.execute(
        "DELETE FROM activity_sessions WHERE status != 'active' AND ends_at < ?",
        (_iso(_now() - timedelta(days=90)),),
    )
    return cursor.rowcount


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
        device = db.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
        if device is None:
            raise LookupError("No se encontró el dispositivo.")
        db.execute(
            "UPDATE activity_sessions SET status = 'stopped', stopped_at = ?, ends_at = ? WHERE device_id = ? AND status = 'active'",
            (started_at, started_at, device_id),
        )
        cursor = db.execute(
            """INSERT INTO activity_sessions
               (device_id, source_mode, started_at, ends_at, status, collector_token_hash)
               VALUES (?, ?, ?, ?, 'active', ?)""",
            (device_id, source_mode, started_at, ends_at, token_hash),
        )
        row = db.execute(
            """SELECT s.id, s.device_id, s.source_mode, s.started_at, s.ends_at, s.stopped_at, s.status,
                      d.display_name, d.ip_address, d.mac_address
               FROM activity_sessions s JOIN devices d ON d.id=s.device_id WHERE s.id=?""",
            (cursor.lastrowid,),
        ).fetchone()
        result = dict(row)
        result["collector_token"] = collector_token
        result["token_note"] = "Copiá este token ahora. Solo se almacena su hash y no volverá a mostrarse."
        return result


def stop_session(session_id: int) -> dict[str, Any] | None:
    now = _iso(_now())
    with database.connect() as db:
        _cleanup(db)
        row = db.execute("SELECT id FROM activity_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        status = db.execute("SELECT status FROM activity_sessions WHERE id=?", (session_id,)).fetchone()["status"]
        if status == "active":
            db.execute(
                "UPDATE activity_sessions SET status='stopped', stopped_at=?, ends_at=? WHERE id=?",
                (now, now, session_id),
            )
        return dict(db.execute(
            """SELECT id, device_id, source_mode, started_at, ends_at, stopped_at, status
               FROM activity_sessions WHERE id=?""",
            (session_id,),
        ).fetchone())


def ingest_event(
    session_id: int, device_id: int, collector_token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Guarda metadatos si sesión, dispositivo, fuente, plazo y token coinciden."""
    event = normalize_event(payload)
    now = _iso(_now())
    supplied_hash = hashlib.sha256(collector_token.encode("utf-8")).hexdigest()
    with database.connect() as db:
        _cleanup(db)
        session = db.execute(
            "SELECT * FROM activity_sessions WHERE id = ? AND device_id = ?",
            (session_id, device_id),
        ).fetchone()
        if session is None:
            raise LookupError("No existe una sesión para ese dispositivo.")
        if not hmac.compare_digest(session["collector_token_hash"], supplied_hash):
            raise InvalidCollectorToken("El token de recopilación no es válido.")
        if session["status"] != "active" or session["ends_at"] <= now:
            raise PermissionError("La sesión no está activa; iniciá otra ventana de seguimiento.")
        if event["source"] != session["source_mode"]:
            raise ValueError("La fuente del evento no coincide con la fuente elegida para esta sesión.")
        cursor = db.execute(
            """INSERT INTO activity_events
               (session_id, device_id, observed_at, received_at, event_type, source, domain,
                destination_ip, destination_port, protocol, app_name, page_url, search_engine, search_terms,
                email_provider, email_from, email_to, email_subject, blocked)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, device_id, event["observed_at"], now, event["event_type"], event["source"],
                event["domain"], event["destination_ip"], event["destination_port"], event["protocol"],
                event["app_name"], event["page_url"], event["search_engine"], event["search_terms"],
                event["email_provider"], event["email_from"], event["email_to"], event["email_subject"], event["blocked"],
            ),
        )
        return dict(db.execute("SELECT * FROM activity_events WHERE id=?", (cursor.lastrowid,)).fetchone())


def import_csv(device_id: int, csv_data: str) -> dict[str, Any]:
    """Importa un CSV local de metadatos, con esquema cerrado y hasta 1000 filas."""
    if len(csv_data.encode("utf-8")) > 1_000_000:
        raise ValueError("El archivo CSV supera el máximo de 1 MB.")
    reader = csv.DictReader(io.StringIO(csv_data))
    headers = [str(name or "").strip().lstrip("\ufeff").lower() for name in (reader.fieldnames or [])]
    if not headers:
        raise ValueError("El CSV está vacío o no contiene cabeceras.")
    forbidden = SENSITIVE_HEADERS.intersection(headers)
    if forbidden:
        raise ValueError("El CSV incluye campos que no se importan por privacidad: " + ", ".join(sorted(forbidden)) + ".")
    if len(set(headers)) != len(headers) or not {"observed_at", "event_type"}.issubset(headers):
        raise ValueError("El CSV requiere cabeceras únicas observed_at y event_type.")
    unknown = set(headers) - CSV_FIELDS
    if unknown:
        raise ValueError("Cabeceras CSV no admitidas: " + ", ".join(sorted(unknown)) + ".")
    if set(headers) - {"observed_at", "event_type"} - CSV_FIELDS:
        raise ValueError("El CSV contiene columnas no compatibles.")
    raw_rows = list(reader)
    if len(raw_rows) > 1000:
        raise ValueError("Se permiten hasta 1000 eventos por importación.")
    with database.connect() as db:
        device = db.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
        if device is None:
            raise LookupError("No se encontró el dispositivo.")
    normalized: list[dict[str, Any]] = []
    for line, row in enumerate(raw_rows, start=2):
        if row.get(None):
            raise ValueError(f"Fila {line}: contiene más columnas que las cabeceras del CSV.")
        mapped = {
            str(key or "").strip().lstrip("\ufeff").lower(): value
            for key, value in row.items() if key is not None
        }
        if not mapped.get("observed_at") or not mapped.get("event_type"):
            raise ValueError(f"Fila {line}: observed_at y event_type son obligatorios.")
        try:
            normalized.append(normalize_event(mapped, source_override="manual_import"))
        except ValueError as exc:
            raise ValueError(f"Fila {line}: {exc}") from exc
    if not normalized:
        return {"device_id": device_id, "imported": 0, "note": "El CSV no contiene eventos."}
    with database.connect() as db:
        _cleanup(db)
        for item in normalized:
            db.execute(
                """INSERT INTO activity_events
                   (session_id, device_id, observed_at, received_at, event_type, source, domain,
                    destination_ip, destination_port, protocol, app_name, page_url, search_engine, search_terms,
                    email_provider, email_from, email_to, email_subject, blocked)
                   VALUES (NULL, ?, ?, ?, ?, 'manual_import', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    device_id, item["observed_at"], _iso(_now()), item["event_type"], item["domain"],
                    item["destination_ip"], item["destination_port"], item["protocol"], item["app_name"],
                    item["page_url"], item["search_engine"], item["search_terms"],
                    item["email_provider"], item["email_from"], item["email_to"], item["email_subject"], item["blocked"],
                ),
            )
    return {
        "device_id": device_id,
        "imported": len(normalized),
        "note": "Importado como metadatos históricos. Las filas no prueban que una persona haya interactuado con el servicio.",
    }


def update_retention(retention_days: int) -> dict[str, Any]:
    if not 1 <= int(retention_days) <= 90:
        raise ValueError("La retención debe ser de 1 a 90 días.")
    with database.connect() as db:
        db.execute("UPDATE activity_settings SET retention_days = ? WHERE id = 1", (int(retention_days),))
        deleted = _cleanup(db)
        row = db.execute("SELECT retention_days FROM activity_settings WHERE id = 1").fetchone()
    return {"retention_days": int(row["retention_days"]), "deleted_events": deleted}


def get_activity(device_id: int | None = None, limit: int = 100) -> dict[str, Any]:
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
        event_filter = "WHERE e.device_id = ?" if device_id is not None else ""
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address, d.mac_address
                FROM activity_events e JOIN devices d ON d.id=e.device_id
                {event_filter} ORDER BY e.observed_at DESC, e.id DESC LIMIT ?""",
            (*params, max(1, min(int(limit), 500))),
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
        setting = db.execute("SELECT retention_days FROM activity_settings WHERE id=1").fetchone()
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
        "retention_days": int(setting["retention_days"]) if setting else 7,
        "active_sessions": int(active_count),
        "total_events": int(event_count),
        "sources": sorted(SESSION_SOURCES),
        "event_types": sorted(EVENT_TYPES),
        "note": (
            "La aplicación no captura tráfico por sí misma. El correo solo se incorpora como metadatos importados "
            "de registros autorizados, sin cuerpos ni adjuntos. Las sesiones habilitan una ventana para que un adaptador "
            "autorizado envíe metadatos; la importación CSV añade registros históricos. No se guardan credenciales, "
            "cookies, cargas útiles, rutas ni URLs completas. DNS/SNI/conexiones son indicios de tráfico, no prueba "
            "de que una persona haya usado una cuenta o visto una página concreta."
        ),
    }
