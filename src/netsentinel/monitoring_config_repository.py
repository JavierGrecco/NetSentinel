"""Consultas y cambios de configuración de monitores.

Este módulo mantiene juntas las operaciones CRUD y la consulta enriquecida
de cada monitor que necesitan los formularios y el supervisor.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .database_storage import connect, utc_now

def create_monitor(
    name: str, kind: str, target: str, interval_seconds: int = 60,
    timeout_seconds: int = 3, path: Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    name = name.strip()[:120]
    if not name:
        raise ValueError("El nombre del monitor no puede estar vacío.")
    if kind not in {"ping", "tcp", "http"}:
        raise ValueError("Tipo de monitor no admitido.")
    if not 15 <= int(interval_seconds) <= 86400:
        raise ValueError("El intervalo debe estar entre 15 y 86400 segundos.")
    if not 1 <= int(timeout_seconds) <= 10:
        raise ValueError("El tiempo límite debe estar entre 1 y 10 segundos.")
    with connect(path) as db:
        cursor = db.execute(
            """INSERT INTO monitors(name, kind, target, interval_seconds, timeout_seconds, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (name, kind, target.strip(), int(interval_seconds), int(timeout_seconds), now, now),
        )
        monitor_id = int(cursor.lastrowid)
    result = next((item for item in list_monitors(path) if item["id"] == monitor_id), None)
    if result is None:
        raise RuntimeError("No se pudo recuperar el monitor recién creado.")
    return result

def list_monitors(path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            """SELECT m.*,
                      (SELECT c.latency_ms FROM monitor_checks c WHERE c.monitor_id = m.id ORDER BY c.id DESC LIMIT 1) AS last_latency_ms,
                      (SELECT c.detail FROM monitor_checks c WHERE c.monitor_id = m.id ORDER BY c.id DESC LIMIT 1) AS last_detail,
                      (SELECT i.id FROM incidents i WHERE i.monitor_id = m.id AND i.status = 'open' ORDER BY i.id DESC LIMIT 1) AS open_incident_id,
                      (SELECT COUNT(*) FROM monitor_checks c WHERE c.monitor_id = m.id) AS checks_count
               FROM monitors m ORDER BY m.enabled DESC, m.name COLLATE NOCASE"""
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["enabled"] = bool(item["enabled"])
        item["incident_open"] = item["open_incident_id"] is not None
    return items

def update_monitor(monitor_id: int, *, enabled: bool | None = None, name: str | None = None,
                   interval_seconds: int | None = None, timeout_seconds: int | None = None,
                   path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as db:
        row = db.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        if row is None:
            return None
        new_enabled = int(enabled) if enabled is not None else row["enabled"]
        new_name = name.strip()[:120] if name is not None else row["name"]
        new_interval = int(interval_seconds) if interval_seconds is not None else row["interval_seconds"]
        new_timeout = int(timeout_seconds) if timeout_seconds is not None else row["timeout_seconds"]
        if not new_name:
            raise ValueError("El nombre del monitor no puede estar vacío.")
        if not 15 <= new_interval <= 86400:
            raise ValueError("El intervalo debe estar entre 15 y 86400 segundos.")
        if not 1 <= new_timeout <= 10:
            raise ValueError("El tiempo límite debe estar entre 1 y 10 segundos.")
        db.execute(
            "UPDATE monitors SET name = ?, enabled = ?, interval_seconds = ?, timeout_seconds = ?, updated_at = ? WHERE id = ?",
            (new_name, new_enabled, new_interval, new_timeout, utc_now(), monitor_id),
        )
    return next((item for item in list_monitors(path) if item["id"] == monitor_id), None)

def delete_monitor(monitor_id: int, path: Path | None = None) -> bool:
    with connect(path) as db:
        cursor = db.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        return cursor.rowcount > 0
