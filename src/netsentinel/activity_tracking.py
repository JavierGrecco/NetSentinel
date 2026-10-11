"""Seguimiento familiar basado solo en metadatos explícitos y fuentes autorizadas.

Este módulo no captura paquetes por sí mismo ni lee contenido HTTPS, credenciales,
cookies, cuerpos HTTP ni rutas completas de URL. Las fuentes externas compatibles
deben normalizar y enviar eventos de metadatos a la API durante una sesión opt-in.
"""
from __future__ import annotations

import csv
import io
import ipaddress
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from . import database

SESSION_SOURCES = {"router_dns", "router_flow", "device_agent"}
EVENT_SOURCES = SESSION_SOURCES
EVENT_TYPES = {"dns_query", "connection", "tls_sni", "app_usage", "blocked"}
PROTOCOLS = {"tcp", "udp", "quic", "icmp", "other"}
CSV_FIELDS = {
    "observed_at", "event_type", "domain", "destination_ip",
    "destination_port", "protocol", "app_name", "blocked",
}
SENSITIVE_HEADERS = {
    "url", "full_url", "path", "query_string", "username", "user",
    "password", "passwd", "token", "cookie", "authorization", "payload",
    "body", "request_body", "response_body",
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


def normalize_event(payload: dict[str, Any], *, source_override: str | None = None) -> dict[str, Any]:
    """Valida un evento de metadatos; rechaza silenciosamente no es una opción."""
    event_type = str(payload.get("event_type", "")).strip().lower()
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Tipo de evento no admitido. Usá: {', '.join(sorted(EVENT_TYPES))}.")
    source = source_override or str(payload.get("source", "")).strip().lower()
    if source not in EVENT_SOURCES and source != "manual_import":
        raise ValueError("Fuente no admitida.")
    domain = _domain(payload.get("domain"))
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
    """Arma una ventana de recopilación; no inicia una captura automática."""
    if not 5 <= int(duration_minutes) <= 720:
        raise ValueError("La duración debe estar entre 5 minutos y 12 horas.")
    source_mode = source_mode.strip().lower()
    if source_mode not in SESSION_SOURCES:
        raise ValueError("Fuente elegible: router_dns, router_flow o device_agent.")
    now = _now()
    started_at = _iso(now)
    ends_at = _iso(now + timedelta(minutes=int(duration_minutes)))
    with database.connect() as db:
        _cleanup(db)
        device = db.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
        if device is None:
            raise LookupError("No se encontró el dispositivo.")
        db.execute(
            "UPDATE activity_sessions SET status = 'stopped', ends_at = ? WHERE device_id = ? AND status = 'active'",
            (started_at, device_id),
        )
        cursor = db.execute(
            """INSERT INTO activity_sessions(device_id, source_mode, started_at, ends_at, status)
               VALUES (?, ?, ?, ?, 'active')""",
            (device_id, source_mode, started_at, ends_at),
        )
        row = db.execute(
            """SELECT s.*, d.display_name, d.ip_address, d.mac_address
               FROM activity_sessions s JOIN devices d ON d.id=s.device_id WHERE s.id=?""",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def stop_session(session_id: int) -> dict[str, Any] | None:
    now = _iso(_now())
    with database.connect() as db:
        _cleanup(db)
        row = db.execute("SELECT * FROM activity_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        if row["status"] == "active":
            db.execute(
                "UPDATE activity_sessions SET status='stopped', stopped_at=?, ends_at=? WHERE id=?",
                (now, now, session_id),
            )
        return dict(db.execute("SELECT * FROM activity_sessions WHERE id=?", (session_id,)).fetchone())


def ingest_event(session_id: int, device_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Guarda metadatos solo si coinciden con una sesión activa y la fuente declarada."""
    event = normalize_event(payload)
    now = _iso(_now())
    with database.connect() as db:
        _cleanup(db)
        session = db.execute(
            "SELECT * FROM activity_sessions WHERE id = ? AND device_id = ?",
            (session_id, device_id),
        ).fetchone()
        if session is None:
            raise LookupError("No existe una sesión para ese dispositivo.")
        if session["status"] != "active" or session["ends_at"] <= now:
            raise PermissionError("La sesión no está activa; iniciá otra ventana de seguimiento.")
        if event["source"] != session["source_mode"]:
            raise ValueError("La fuente del evento no coincide con la fuente elegida para esta sesión.")
        cursor = db.execute(
            """INSERT INTO activity_events
               (session_id, device_id, observed_at, received_at, event_type, source, domain,
                destination_ip, destination_port, protocol, app_name, blocked)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, device_id, event["observed_at"], now, event["event_type"], event["source"],
                event["domain"], event["destination_ip"], event["destination_port"], event["protocol"],
                event["app_name"], event["blocked"],
            ),
        )
        return dict(db.execute("SELECT * FROM activity_events WHERE id=?", (cursor.lastrowid,)).fetchone())


def import_csv(device_id: int, csv_data: str) -> dict[str, Any]:
    """Importa un CSV local de metadatos, con esquema cerrado y hasta 1000 filas."""
    if len(csv_data.encode("utf-8")) > 1_000_000:
        raise ValueError("El archivo CSV supera el máximo de 1 MB.")
    reader = csv.DictReader(io.StringIO(csv_data))
    headers = [str(name or "").strip().lower() for name in (reader.fieldnames or [])]
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
        mapped = {str(key or "").strip().lower(): value for key, value in row.items() if key is not None}
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
                    destination_ip, destination_port, protocol, app_name, blocked)
                   VALUES (NULL, ?, ?, ?, ?, 'manual_import', ?, ?, ?, ?, ?, ?)""",
                (
                    device_id, item["observed_at"], _iso(_now()), item["event_type"], item["domain"],
                    item["destination_ip"], item["destination_port"], item["protocol"], item["app_name"],
                    item["blocked"],
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
        where = "WHERE s.device_id = ?" if device_id is not None else ""
        params: tuple[Any, ...] = (device_id,) if device_id is not None else ()
        if device_id is not None and db.execute("SELECT 1 FROM devices WHERE id=?", (device_id,)).fetchone() is None:
            raise LookupError("No se encontró el dispositivo.")
        sessions = db.execute(
            """SELECT s.*, d.display_name, d.ip_address, d.mac_address
               FROM activity_sessions s JOIN devices d ON d.id=s.device_id
               ORDER BY s.started_at DESC, s.id DESC LIMIT 100"""
        ).fetchall()
        event_filter = "WHERE e.device_id = ?" if device_id is not None else ""
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address, d.mac_address
                FROM activity_events e JOIN devices d ON d.id=e.device_id
                {event_filter} ORDER BY e.observed_at DESC, e.id DESC LIMIT ?""",
            (*params, max(1, min(int(limit), 500))),
        ).fetchall()
        setting = db.execute("SELECT retention_days FROM activity_settings WHERE id=1").fetchone()
        active_count = db.execute("SELECT COUNT(*) FROM activity_sessions WHERE status='active'").fetchone()[0]
        event_count = db.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0]
        devices = db.execute(
            "SELECT id, display_name, ip_address, mac_address FROM devices ORDER BY display_name, ip_address"
        ).fetchall()
    return {
        "sessions": [dict(row) for row in sessions],
        "events": [dict(row) for row in events],
        "devices": [dict(row) for row in devices],
        "retention_days": int(setting["retention_days"]) if setting else 7,
        "active_sessions": int(active_count),
        "total_events": int(event_count),
        "sources": sorted(SESSION_SOURCES),
        "event_types": sorted(EVENT_TYPES),
        "note": (
            "La aplicación no captura tráfico por sí misma. Las sesiones habilitan una ventana para que un adaptador "
            "autorizado envíe metadatos; la importación CSV añade registros históricos. No se guardan credenciales, "
            "cookies, cargas útiles, rutas ni URLs completas. DNS/SNI/conexiones son indicios de tráfico, no prueba "
            "de que una persona haya usado una cuenta o visto una página concreta."
        ),
    }
