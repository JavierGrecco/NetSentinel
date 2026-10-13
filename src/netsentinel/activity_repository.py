"""Consultas y operaciones SQLite propias del dominio de actividad.

El módulo recibe conexiones existentes cuando debe compartir una transacción y abre
su propia conexión solo para operaciones completas, como actualizar la retención.
No importa FastAPI ni contiene contratos HTTP.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from . import database

DEFAULT_RETENTION_DAYS = 7
MAX_RETENTION_DAYS = 90


def _utc_iso(value: datetime) -> str:
    """Serializa una fecha en UTC con la precisión usada por la base existente."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def get_retention_days(db: sqlite3.Connection) -> int:
    """Lee la política actual, manteniendo el valor histórico por defecto."""
    row = db.execute(
        "SELECT retention_days FROM activity_settings WHERE id = 1"
    ).fetchone()
    return int(row["retention_days"]) if row else DEFAULT_RETENTION_DAYS


def cleanup(db: sqlite3.Connection, *, now: datetime) -> int:
    """Aplica retención y vence sesiones sin cambiar el esquema ni sus datos válidos."""
    now_utc = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    now_text = _utc_iso(now_utc)
    retention_cutoff = _utc_iso(
        now_utc - timedelta(days=get_retention_days(db))
    )
    stale_session_cutoff = _utc_iso(now_utc - timedelta(days=MAX_RETENTION_DAYS))

    deleted_events = db.execute(
        "DELETE FROM activity_events WHERE observed_at < ?",
        (retention_cutoff,),
    )
    db.execute(
        "UPDATE activity_sessions SET status = 'expired' "
        "WHERE status = 'active' AND ends_at <= ?",
        (now_text,),
    )
    db.execute(
        "DELETE FROM activity_sessions WHERE status != 'active' AND ends_at < ?",
        (stale_session_cutoff,),
    )
    return int(deleted_events.rowcount)


def update_retention(retention_days: int, *, now: datetime) -> dict[str, int]:
    """Actualiza el ajuste y aplica la nueva retención dentro de una transacción."""
    days = int(retention_days)
    if not 1 <= days <= MAX_RETENTION_DAYS:
        raise ValueError("La retención debe ser de 1 a 90 días.")

    with database.connect() as db:
        # Restore the singleton row if an older or repaired database lacks it.
        # Otherwise, UPDATE would silently keep the default while reporting success.
        db.execute(
            """INSERT INTO activity_settings (id, retention_days) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET retention_days = excluded.retention_days""",
            (days,),
        )
        deleted_events = cleanup(db, now=now)
        effective_days = get_retention_days(db)

    return {
        "retention_days": effective_days,
        "deleted_events": deleted_events,
    }

def start_session(
    db: sqlite3.Connection,
    *,
    device_id: int,
    source_mode: str,
    started_at: str,
    ends_at: str,
    token_hash: str,
) -> dict[str, Any]:
    """Reemplaza sesiones activas del dispositivo y crea la nueva sesión."""
    device = db.execute(
        "SELECT id FROM devices WHERE id = ?", (device_id,)
    ).fetchone()
    if device is None:
        raise LookupError("No se encontró el dispositivo.")

    db.execute(
        "UPDATE activity_sessions SET status = 'stopped', stopped_at = ?, ends_at = ? "
        "WHERE device_id = ? AND status = 'active'",
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
    if row is None:
        raise RuntimeError("No se pudo recuperar la sesión recién creada.")
    return dict(row)


def get_session_for_device(
    db: sqlite3.Connection, session_id: int, device_id: int
) -> dict[str, Any] | None:
    """Obtiene una sesión con alcance de dispositivo para validar la ingesta."""
    row = db.execute(
        "SELECT * FROM activity_sessions WHERE id = ? AND device_id = ?",
        (session_id, device_id),
    ).fetchone()
    return dict(row) if row is not None else None


def stop_session(
    db: sqlite3.Connection, session_id: int, *, now: str
) -> dict[str, Any] | None:
    """Detiene una sesión activa; repetir la operación conserva el primer cierre."""
    current = db.execute(
        "SELECT id, status FROM activity_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if current is None:
        return None
    if current["status"] == "active":
        db.execute(
            "UPDATE activity_sessions SET status='stopped', stopped_at=?, ends_at=? WHERE id=?",
            (now, now, session_id),
        )
    row = db.execute(
        """SELECT id, device_id, source_mode, started_at, ends_at, stopped_at, status
           FROM activity_sessions WHERE id=?""",
        (session_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def insert_event(
    db: sqlite3.Connection,
    session_id: int,
    device_id: int,
    event: Mapping[str, Any],
    *,
    received_at: str,
) -> dict[str, Any]:
    """Persiste un evento previamente validado por la capa de actividad."""
    cursor = db.execute(
        """INSERT INTO activity_events
           (session_id, device_id, observed_at, received_at, event_type, source, domain,
            destination_ip, destination_port, protocol, app_name, page_url, search_engine, search_terms,
            email_provider, email_from, email_to, email_subject, blocked)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, device_id, event["observed_at"], received_at, event["event_type"], event["source"],
            event["domain"], event["destination_ip"], event["destination_port"], event["protocol"],
            event["app_name"], event["page_url"], event["search_engine"], event["search_terms"],
            event["email_provider"], event["email_from"], event["email_to"], event["email_subject"], event["blocked"],
        ),
    )
    row = db.execute(
        "SELECT * FROM activity_events WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    if row is None:
        raise RuntimeError("No se pudo recuperar el evento recién guardado.")
    return dict(row)

