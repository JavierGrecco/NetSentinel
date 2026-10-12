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
from urllib.parse import parse_qsl, unquote, unquote_plus, urlencode, urlsplit, urlunsplit

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
IMPORT_DEDUP_FIELDS = (
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)
CSV_PREVIEW_FIELDS = (
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)
SENSITIVE_QUERY_KEY = re.compile(
    r"(?:access.?token|refresh.?token|id.?token|client.?secret|client.?assertion|"
    r"password|passwd|secret|authorization|bearer|api.?key|private.?key|"
    r"username|email|phone|session|sid|csrf|nonce|signature|"
    r"redirect.?uri|return.?url|return.?to|returnto|relay.?state|saml.?request|callback|"
    r"(^|_)(?:token|auth|code|state|otp|jwt|key|user|account|customer|continue|next)(_|$))",
    re.IGNORECASE,
)
SEARCH_QUERY_KEYS = {"q", "query", "text", "wd", "word", "search_query", "search"}
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ttclid",
    "twclid", "li_fat_id", "mkt_tok", "vero_id", "s_cid", "_ga", "_gl", "_hsenc", "_hsmi",
}
_PATH_EMAIL = re.compile(r"^[^/\s@]+@[^/\s@]+\.[^/\s@]+$")
_PATH_PHONE = re.compile(r"^[+()0-9.\-\s]+$")
_PATH_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_PATH_OPAQUE = re.compile(r"^[A-Za-z0-9._~-]+$")
SENSITIVE_HEADERS = {
    "url", "full_url", "path", "query_string", "username", "user",
    "password", "passwd", "token", "cookie", "authorization", "payload",
    "body", "message", "email_body", "message_body", "body_text", "body_html",
    "content", "email_message", "request_body", "response_body", "attachment",
    "attachments", "attachment_content", "message_content",
}

CSV_IGNORED_METADATA_HEADERS = {
    "id", "message_id", "messageid", "message_trace_id", "messagetraceid",
    "status", "delivery_status", "direction", "size", "message_size",
    "from_ip", "fromip", "to_ip", "toip", "sender_ip", "senderip",
    "recipient_ip", "recipientip", "delivery_step", "event", "route",
    "internet_message_id", "internetmessageid", "network_message_id",
    "networkmessageid", "trace_id", "traceid",
}
CSV_HEADER_ALIASES = {
    "observed_at": {
        "date", "datetime", "timestamp", "date_time", "date_and_time",
        "received_datetime", "received_date_time", "sent_datetime", "sent_date_time",
        "received_time", "sent_time", "time",
    },
    "event_type": {"eventtype"},
    "email_provider": {"provider", "mail_provider", "email_service", "service"},
    "email_from": {
        "from", "from_address", "from_email", "sender", "sender_address",
        "senderaddress", "sender_email", "sender_email_address",
    },
    "email_to": {
        "to", "to_address", "to_email", "recipient", "recipient_address",
        "recipientaddress", "recipient_email", "recipients",
    },
    "email_subject": {
        "subject", "subject_line", "message_subject", "subject_or_message_id",
    },
}


def _normalized_csv_header(value: str | None) -> str:
    raw = str(value or "").strip().lstrip(chr(0xFEFF))
    # Provider exports commonly use camelCase fields such as receivedDateTime.
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", raw)
    return re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")

def _is_sensitive_csv_header(value: str | None) -> bool:
    normalized = _normalized_csv_header(value)
    if normalized in SENSITIVE_HEADERS:
        return True
    parts = set(normalized.split("_"))
    if parts.intersection({"body", "content", "payload", "attachment", "attachments"}):
        return True
    # A message identifier is harmless metadata; a message/body/content column is not.
    return "message" in parts and "id" not in parts and "subject" not in parts


def _canonical_csv_header(value: str | None) -> str | None:
    normalized = _normalized_csv_header(value)
    if normalized in CSV_IGNORED_METADATA_HEADERS:
        return None
    if normalized in CSV_FIELDS:
        return normalized
    for canonical, aliases in CSV_HEADER_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized



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


def _normalized_query_key(value: str) -> str:
    """Normalize repeatedly encoded parameter names before sensitive-key checks."""
    normalized = value.lower()
    for _ in range(3):
        decoded = unquote_plus(normalized)
        if decoded == normalized:
            break
        normalized = decoded
    return re.sub(r"[^a-z0-9_]", "", normalized)


def _sensitive_path_segment(value: str) -> bool:
    """Redact common high-confidence PII/token path segments, not arbitrary usernames."""
    decoded = value
    for _ in range(3):
        expanded = unquote(decoded)
        if expanded == decoded:
            break
        decoded = expanded
    if _PATH_EMAIL.fullmatch(decoded) or _PATH_UUID.fullmatch(decoded):
        return True
    if _PATH_PHONE.fullmatch(decoded) and sum(ch.isdigit() for ch in decoded) >= 10:
        return True
    if (
        len(decoded) >= 32
        and _PATH_OPAQUE.fullmatch(decoded)
        and any(ch.isalpha() for ch in decoded)
        and any(ch.isdigit() for ch in decoded)
    ):
        return True
    return False


def _safe_url_path(path: str) -> str:
    """Replace recognizable email/phone/UUID/opaque-token segments with a marker."""
    if not path:
        return "/"
    segments = path.split("/")
    return "/".join("%5Bredacted%5D" if _sensitive_path_segment(segment) else segment for segment in segments)


def _safe_page_url(value: str | None) -> str | None:
    """Normalize HTTP(S) URLs and redact known sensitive query keys and recognizable path identifiers."""
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
        normalized_host = str(ipaddress.ip_address(hostname)).lower()
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
    try:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=200)
    except ValueError as exc:
        raise ValueError("page_url contiene demasiados parámetros de consulta.") from exc
    safe_pairs = []
    for key, item_value in query_pairs:
        normalized_key = _normalized_query_key(key)
        if (
            SENSITIVE_QUERY_KEY.search(normalized_key)
            or normalized_key in TRACKING_QUERY_KEYS
            or normalized_key.startswith("utm_")
            or normalized_key in SEARCH_QUERY_KEYS
        ):
            continue
        safe_pairs.append((key, item_value))
    safe = urlunsplit((scheme, netloc, _safe_url_path(parsed.path), urlencode(safe_pairs, doseq=True), ""))
    if len(safe) > 2048:
        raise ValueError("page_url supera los 2048 caracteres permitidos.")
    return safe


def _email_address_list(value: str | None, *, field: str, required: bool) -> list[str]:
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"{field} es obligatorio para el evento de correo.")
        return []
    raw = str(value).strip()
    if len(raw) > 1500 or any(ord(ch) < 32 for ch in raw):
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


def import_csv(device_id: int, csv_data: str, *, preview: bool = False) -> dict[str, Any]:
    """Valida un CSV y, salvo en vista previa, importa hasta 1000 filas normalizadas."""
    if len(csv_data.encode("utf-8")) > 1_000_000:
        raise ValueError("El archivo CSV supera el máximo de 1 MB.")
    reader = csv.DictReader(io.StringIO(csv_data))
    raw_headers = list(reader.fieldnames or [])
    if not raw_headers:
        raise ValueError("El CSV está vacío o no contiene cabeceras.")
    forbidden = [name for name in raw_headers if _is_sensitive_csv_header(name)]
    if forbidden:
        raise ValueError(
            "El CSV incluye campos que no se importan por privacidad: "
            + ", ".join(sorted(str(name) for name in forbidden)) + "."
        )
    normalized_headers = [_normalized_csv_header(name) for name in raw_headers]
    headers = [_canonical_csv_header(name) for name in raw_headers]
    effective_headers = [name for name in headers if name is not None]
    if len(set(effective_headers)) != len(effective_headers):
        raise ValueError("El CSV repite una cabecera tras normalizar los nombres de columna.")
    email_audit_csv = {"email_from", "email_to"}.issubset(set(effective_headers))
    if "observed_at" not in effective_headers or (
        "event_type" not in effective_headers and not email_audit_csv
    ):
        raise ValueError(
            "El CSV requiere fecha y tipo de evento, o fecha más emisor/destinatario "
            "para una exportación de auditoría de correo."
        )
    unknown = set(effective_headers) - CSV_FIELDS
    if unknown:
        raise ValueError("Cabeceras CSV no admitidas: " + ", ".join(sorted(unknown)) + ".")
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
        mapped: dict[str, Any] = {}
        for raw_name, value in row.items():
            if raw_name is None:
                continue
            canonical = _canonical_csv_header(raw_name)
            if canonical is None:
                continue
            if canonical in mapped:
                raise ValueError(f"Fila {line}: hay varias columnas que representan {canonical}.")
            mapped[canonical] = value
        if not mapped.get("observed_at"):
            raise ValueError(f"Fila {line}: falta una fecha/hora.")
        if not mapped.get("event_type") and email_audit_csv:
            mapped["event_type"] = "email_metadata"
            raw_header_set = set(normalized_headers)
            if not mapped.get("email_provider"):
                if {"received_datetime", "received_date_time", "sender_address", "recipient_address"}.issubset(raw_header_set) or {"received_date_time", "sender_address", "recipient_address"}.issubset(raw_header_set):
                    mapped["email_provider"] = "Microsoft 365"
                elif "subject_or_message_id" in raw_header_set:
                    mapped["email_provider"] = "Google Workspace"
        if not mapped.get("event_type"):
            raise ValueError(f"Fila {line}: event_type es obligatorio para eventos no relacionados con correo.")
        try:
            normalized.append(normalize_event(mapped, source_override="manual_import"))
        except ValueError as exc:
            raise ValueError(f"Fila {line}: {exc}") from exc
    if not normalized:
        if preview:
            return {
                "device_id": device_id,
                "valid_rows": 0,
                "would_import": 0,
                "skipped_duplicates": 0,
                "preview_rows": [],
                "note": "El CSV no contiene eventos. No se guardó ningún dato.",
            }
        return {
            "device_id": device_id,
            "imported": 0,
            "skipped_duplicates": 0,
            "note": "El CSV no contiene eventos.",
        }

    # Null-safe equality makes re-importing the same normalized CSV idempotent.
    # Only manual imports are deduplicated; events from live sources remain intact.
    duplicate_sql = (
        "SELECT 1 FROM activity_events "
        "WHERE device_id = ? AND source = 'manual_import' AND "
        + " AND ".join(f"{field} IS ?" for field in IMPORT_DEDUP_FIELDS)
        + " LIMIT 1"
    )
    imported_count = 0
    skipped_duplicates = 0
    seen_in_batch: set[tuple[Any, ...]] = set()
    preview_rows: list[dict[str, Any]] = []
    with database.connect() as db:
        cutoff = None
        if preview:
            # A preview is read-only: mirror the cleanup boundary without deleting rows.
            setting = db.execute(
                "SELECT retention_days FROM activity_settings WHERE id = 1"
            ).fetchone()
            retention_days = int(setting["retention_days"]) if setting else 7
            cutoff = _iso(_now() - timedelta(days=retention_days))
            duplicate_sql = duplicate_sql.replace(
                "source = 'manual_import' AND",
                "source = 'manual_import' AND observed_at >= ? AND",
            )
        else:
            _cleanup(db)

        for item in normalized:
            values = tuple(item[field] for field in IMPORT_DEDUP_FIELDS)
            disposition = "new"
            if values in seen_in_batch:
                skipped_duplicates += 1
                disposition = "duplicate"
            else:
                seen_in_batch.add(values)
                params = (device_id, cutoff, *values) if preview else (device_id, *values)
                duplicate = db.execute(duplicate_sql, params).fetchone()
                if duplicate:
                    skipped_duplicates += 1
                    disposition = "duplicate"
                else:
                    if not preview:
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
                    imported_count += 1

            if preview and len(preview_rows) < 10:
                row = {field: item.get(field) for field in CSV_PREVIEW_FIELDS}
                row["disposition"] = disposition
                preview_rows.append(row)

    if preview:
        return {
            "device_id": device_id,
            "valid_rows": len(normalized),
            "would_import": imported_count,
            "skipped_duplicates": skipped_duplicates,
            "preview_rows": preview_rows,
            "note": "Vista previa únicamente: no se guardó ningún evento. Se muestran hasta 10 filas de ejemplo.",
        }

    return {
        "device_id": device_id,
        "imported": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "note": (
            "Importado como metadatos históricos. Las filas no prueban que una persona haya "
            "interactuado con el servicio. Las filas idénticas ya importadas para este dispositivo "
            "se omitieron."
        ),
    }


def preview_csv(device_id: int, csv_data: str) -> dict[str, Any]:
    """Valida y muestra una vista previa de CSV sin almacenar los eventos."""
    return import_csv(device_id, csv_data, preview=True)


def update_retention(retention_days: int) -> dict[str, Any]:
    if not 1 <= int(retention_days) <= 90:
        raise ValueError("La retención debe ser de 1 a 90 días.")
    with database.connect() as db:
        db.execute("UPDATE activity_settings SET retention_days = ? WHERE id = 1", (int(retention_days),))
        deleted = _cleanup(db)
        row = db.execute("SELECT retention_days FROM activity_settings WHERE id = 1").fetchone()
    return {"retention_days": int(row["retention_days"]), "deleted_events": deleted}


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


def _csv_safe_text(value: Any) -> Any:
    """Neutralize spreadsheet formulas in text exported to CSV."""
    if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


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
    with database.connect() as db:
        if device_id is not None and db.execute(
            "SELECT 1 FROM devices WHERE id = ?", (device_id,)
        ).fetchone() is None:
            raise LookupError("No se encontró el dispositivo.")
        count = int(db.execute(
            "SELECT COUNT(*) FROM activity_events" + where_sql, params
        ).fetchone()[0])
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

    with database.connect() as db:
        # Lock the SQLite write transaction before counting, so inserts/deletes cannot
        # race between checking the count and deleting the selected rows.
        db.execute("BEGIN IMMEDIATE")
        if device_id is not None and db.execute(
            "SELECT 1 FROM devices WHERE id = ?", (device_id,)
        ).fetchone() is None:
            raise LookupError("No se encontró el dispositivo.")
        count = int(db.execute(
            "SELECT COUNT(*) FROM activity_events" + where_sql, params
        ).fetchone()[0])
        expected = f"BORRAR {count}"
        if confirmation != expected:
            raise PermissionError(
                f"No se borró nada: la selección contiene {count} evento(s). "
                f"Escribí exactamente «{expected}» para confirmar."
            )
        cursor = db.execute("DELETE FROM activity_events" + where_sql, params)
        deleted = int(cursor.rowcount)
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
        "activity_sources": sorted(EVENT_SOURCES | {"manual_import"}),
        "event_types": sorted(EVENT_TYPES),
        "note": (
            "La aplicación no captura tráfico por sí misma. El correo solo se incorpora como metadatos importados "
            "de registros autorizados, sin cuerpos ni adjuntos. Las sesiones habilitan una ventana para que un adaptador "
            "autorizado envíe metadatos; la importación CSV añade registros históricos. No se guardan credenciales, "
            "cookies, cargas útiles, rutas ni URLs completas. DNS/SNI/conexiones son indicios de tráfico, no prueba "
            "de que una persona haya usado una cuenta o visto una página concreta."
        ),
    }
