"""Persistencia de intentos y resultados de notificaciones de monitores."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .database_storage import connect, utc_now

def record_notification(monitor_id: int, incident_id: int | None, event_type: str,
                        success: bool, detail: str, path: Path | None = None) -> None:
    with connect(path) as db:
        db.execute(
            """INSERT INTO notification_log(monitor_id, incident_id, event_type, attempted_at, success, detail)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (monitor_id, incident_id, event_type, utc_now(), int(success), detail[:500]),
        )

def get_notification_log(path: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            """SELECT n.*, m.name AS monitor_name FROM notification_log n
               JOIN monitors m ON m.id = n.monitor_id ORDER BY n.id DESC LIMIT ?""",
            (max(1, min(int(limit), 200)),),
        ).fetchall()
    return [dict(row) for row in rows]
