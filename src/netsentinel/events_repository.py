"""Persistencia de eventos del sistema y su estado de reconocimiento.

Tanto el inventario como la monitorización pueden producir eventos; este repositorio
mantiene las operaciones comunes de la línea temporal.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .database_storage import connect, utc_now


def _insert_event(db: sqlite3.Connection, event_type: str, severity: str, device_id: int, message: str, now: str) -> None:
    db.execute(
        "INSERT INTO events(event_type, severity, device_id, created_at, message) VALUES (?, ?, ?, ?, ?)",
        (event_type, severity, device_id, now, message),
    )


def get_events(
    path: Path | None = None,
    limit: int = 50,
    acknowledged: bool | None = None,
    exclude_event_types: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    """Lista eventos con filtros aplicados en SQL antes del límite de resultados."""
    conditions: list[str] = []
    params: list[Any] = []
    if acknowledged is not None:
        conditions.append("e.acknowledged = ?")
        params.append(int(acknowledged))
    excluded = tuple(dict.fromkeys(item for item in exclude_event_types if item))
    if excluded:
        placeholders = ", ".join("?" for _ in excluded)
        conditions.append(f"e.event_type NOT IN ({placeholders})")
        params.extend(excluded)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(max(1, min(int(limit), 200)))
    with connect(path) as db:
        rows = db.execute(
            f"""SELECT e.*, d.mac_address, d.ip_address, d.display_name, d.manufacturer
                FROM events e LEFT JOIN devices d ON d.id = e.device_id
                {where}
                ORDER BY e.created_at DESC, e.id DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def acknowledge_event(event_id: int, path: Path | None = None) -> bool:
    with connect(path) as db:
        cursor = db.execute("UPDATE events SET acknowledged = 1 WHERE id = ?", (event_id,))
        return cursor.rowcount > 0
