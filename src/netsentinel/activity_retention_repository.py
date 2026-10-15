"""Persistencia de la política de retención y limpieza de actividad.

Las funciones reciben la conexión cuando forman parte de una transacción existente.
La actualización completa abre su propia conexión para guardar el ajuste y limpiar
los datos vencidos de forma atómica.
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
