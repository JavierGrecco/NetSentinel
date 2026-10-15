"""Transiciones de estado y limpieza del historial de comprobaciones.

La escritura del check, la apertura/cierre del incidente y el evento asociado
permanecen en una única transacción para evitar estados parciales.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .database_storage import connect, utc_now
from .events_repository import _insert_event

def cleanup_monitor_history(retention_days: int, path: Path | None = None) -> int:
    """Remove detailed monitor checks older than the configured retention window.

    This deliberately leaves monitor state, incidents, events, scans, and inventory
    observations untouched. The latter are lower-volume and have separate product
    semantics; only high-volume raw check samples are pruned here.
    """
    if isinstance(retention_days, bool) or not isinstance(retention_days, int) or not 1 <= retention_days <= 3650:
        raise ValueError("La retención del historial de monitores debe estar entre 1 y 3650 días.")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(timespec="seconds")
    with connect(path) as db:
        cursor = db.execute("DELETE FROM monitor_checks WHERE checked_at < ?", (cutoff,))
        return int(cursor.rowcount)

def record_monitor_check(monitor_id: int, status: str, latency_ms: float | None,
                         detail: str, path: Path | None = None) -> dict[str, Any]:
    if status not in {"up", "down"}:
        raise ValueError("El estado del control debe ser up o down.")
    now = utc_now()
    transition: dict[str, Any] | None = None
    with connect(path) as db:
        monitor = db.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        if monitor is None:
            raise ValueError("El monitor ya no existe.")
        db.execute(
            "INSERT INTO monitor_checks(monitor_id, checked_at, status, latency_ms, detail) VALUES (?, ?, ?, ?, ?)",
            (monitor_id, now, status, latency_ms, detail[:1000]),
        )
        db.execute(
            "UPDATE monitors SET last_checked_at = ?, last_status = ?, updated_at = ? WHERE id = ?",
            (now, status, now, monitor_id),
        )
        open_incident = db.execute(
            "SELECT * FROM incidents WHERE monitor_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
            (monitor_id,),
        ).fetchone()
        if status == "down":
            if open_incident is None:
                cursor = db.execute(
                    """INSERT INTO incidents(monitor_id, status, opened_at, updated_at, failure_count, last_detail)
                       VALUES (?, 'open', ?, ?, 1, ?)""",
                    (monitor_id, now, now, detail[:1000]),
                )
                incident_id = int(cursor.lastrowid)
                message = f"El monitor '{monitor['name']}' no responde: {detail[:500]}"
                _insert_event(db, "monitor_down", "warning", None, message, now)
                transition = {"transition": "down", "incident_id": incident_id, "monitor_name": monitor["name"],
                              "target": monitor["target"], "message": message, "at": now}
            else:
                incident_id = int(open_incident["id"])
                db.execute(
                    "UPDATE incidents SET updated_at = ?, failure_count = failure_count + 1, last_detail = ? WHERE id = ?",
                    (now, detail[:1000], incident_id),
                )
        elif open_incident is not None:
            incident_id = int(open_incident["id"])
            db.execute(
                "UPDATE incidents SET status = 'resolved', updated_at = ?, resolved_at = ?, last_detail = ? WHERE id = ?",
                (now, now, detail[:1000], incident_id),
            )
            message = f"El monitor '{monitor['name']}' se recuperó. {detail[:500]}"
            _insert_event(db, "monitor_recovered", "info", None, message, now)
            transition = {"transition": "recovered", "incident_id": incident_id, "monitor_name": monitor["name"],
                          "target": monitor["target"], "message": message, "at": now}
        check = db.execute("SELECT * FROM monitor_checks WHERE monitor_id = ? ORDER BY id DESC LIMIT 1", (monitor_id,)).fetchone()
    return {"check": dict(check), "transition": transition}
