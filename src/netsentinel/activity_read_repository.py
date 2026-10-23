"""Consultas SQLite para el panel de actividad y sus exportaciones.

Los filtros deben proceder de los predicados permitidos y todos sus valores se
envían como parámetros. Este módulo no formatea respuestas HTTP.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from . import database
from .activity_repository_support import _require_device
from .activity_retention_repository import cleanup, get_retention_days


_ACTIVITY_READ_FILTER_CLAUSES = frozenset({
    "e.device_id = ?",
    "e.source_event_id = ?",
    "event_type = ?",
    "source = ?",
    "observed_at >= ?",
    "observed_at < ?",
})


def _require_activity_read_filters(where_sql: str, params: tuple[Any, ...]) -> None:
    """Acepta solo los predicados fijos del servicio de lectura y valores enlazados."""
    normalized = where_sql.strip() if isinstance(where_sql, str) else None
    if normalized == "":
        if params:
            raise ValueError("Los filtros de lectura no coinciden con sus parámetros.")
        return
    if not normalized or not normalized.startswith("WHERE "):
        raise ValueError("Los filtros de lectura de actividad no son válidos.")
    clauses = normalized[6:].strip().split(" AND ")
    if (
        not clauses
        or any(clause not in _ACTIVITY_READ_FILTER_CLAUSES for clause in clauses)
        or len(set(clauses)) != len(clauses)
        or len(clauses) != len(params)
    ):
        raise ValueError("Los filtros de lectura de actividad no son válidos.")


def get_activity_snapshot(
    *,
    device_id: int | None,
    event_filter: str,
    event_params: tuple[Any, ...],
    limit: int,
) -> dict[str, Any]:
    """Lee eventos y resúmenes para el panel dentro de una operación consistente."""
    _require_activity_read_filters(event_filter, event_params)
    if device_id is not None and int(device_id) < 1:
        raise ValueError("device_id debe ser un entero positivo.")

    with database.connect() as db:
        cleanup(db, now=datetime.now(timezone.utc))
        _require_device(db, device_id)
        device_params: tuple[Any, ...] = () if device_id is None else (device_id,)
        session_filter = "" if device_id is None else "WHERE s.device_id = ?"
        sessions = db.execute(
            f"""SELECT s.id, s.device_id, s.source_mode, s.started_at, s.ends_at, s.stopped_at, s.status,
                       d.display_name, d.ip_address, d.mac_address
                FROM activity_sessions s JOIN devices d ON d.id=s.device_id
                {session_filter} ORDER BY s.started_at DESC, s.id DESC LIMIT 100""",
            device_params,
        ).fetchall()
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address, d.mac_address
                FROM activity_events e JOIN devices d ON d.id=e.device_id
                {event_filter} ORDER BY e.observed_at DESC, e.id DESC LIMIT ?""",
            (*event_params, max(1, min(int(limit), 500))),
        ).fetchall()

        domain_filter = (
            "WHERE domain IS NOT NULL AND domain <> ''"
            if device_id is None
            else "WHERE device_id = ? AND domain IS NOT NULL AND domain <> ''"
        )
        top_domains = db.execute(
            f"""SELECT domain, COUNT(*) AS events, MAX(observed_at) AS last_seen
                FROM activity_events {domain_filter}
                GROUP BY domain ORDER BY events DESC, last_seen DESC LIMIT 15""",
            device_params,
        ).fetchall()
        blocked_filter = " WHERE blocked = 1" if device_id is None else " WHERE blocked = 1 AND device_id = ?"
        blocked_count = db.execute(
            "SELECT COUNT(*) FROM activity_events" + blocked_filter,
            device_params,
        ).fetchone()[0]
        retention_days = get_retention_days(db)
        session_count_sql = (
            "SELECT COUNT(*) FROM activity_sessions WHERE status='active'"
            + ("" if device_id is None else " AND device_id = ?")
        )
        event_count_sql = (
            "SELECT COUNT(*) FROM activity_events"
            + ("" if device_id is None else " WHERE device_id = ?")
        )
        active_count = db.execute(session_count_sql, device_params).fetchone()[0]
        event_count = db.execute(event_count_sql, device_params).fetchone()[0]
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
    }


def get_activity_export_rows(
    *,
    where_sql: str,
    params: tuple[Any, ...],
    device_id: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Recupera filas para exportación aplicando solo filtros permitidos."""
    _require_activity_read_filters(where_sql, params)
    if device_id is not None and int(device_id) < 1:
        raise ValueError("device_id debe ser un entero positivo.")

    with database.connect() as db:
        cleanup(db, now=datetime.now(timezone.utc))
        _require_device(db, device_id)
        rows = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address
                FROM activity_events e
                JOIN devices d ON d.id = e.device_id
                {where_sql}
                ORDER BY e.observed_at DESC, e.id DESC
                LIMIT ?""",
            (*params, max(1, min(int(limit), 10000))),
        ).fetchall()
    return [dict(row) for row in rows]
