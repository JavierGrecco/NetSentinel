"""Consultas y operaciones SQLite propias del dominio de actividad.

El módulo recibe conexiones existentes cuando debe compartir una transacción y abre
su propia conexión solo para operaciones completas, como actualizar la retención.
No importa FastAPI ni contiene contratos HTTP.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

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
        db.execute(
            "UPDATE activity_settings SET retention_days = ? WHERE id = 1",
            (days,),
        )
        deleted_events = cleanup(db, now=now)
        effective_days = get_retention_days(db)

    return {
        "retention_days": effective_days,
        "deleted_events": deleted_events,
    }
