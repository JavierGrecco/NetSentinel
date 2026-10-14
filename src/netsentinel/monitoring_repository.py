"""Persistencia del dominio de monitorización.

Aquí viven las reglas transaccionales para checks, monitores, incidentes y avisos.
El formato de los CSV está en monitoring_export_service.py.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .database_storage import _elapsed_seconds, connect, utc_now
from .events_repository import _insert_event


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


def get_monitor_checks(monitor_id: int, limit: int = 30, path: Path | None = None) -> list[dict[str, Any]] | None:
    with connect(path) as db:
        if db.execute("SELECT 1 FROM monitors WHERE id = ?", (monitor_id,)).fetchone() is None:
            return None
        rows = db.execute(
            "SELECT * FROM monitor_checks WHERE monitor_id = ? ORDER BY id DESC LIMIT ?",
            (monitor_id, max(1, min(int(limit), 200))),
        ).fetchall()
    return [dict(row) for row in rows]


def get_monitor_analytics(window_hours: int = 24, path: Path | None = None) -> dict[str, Any]:
    """Resume comprobaciones por monitor en una ventana reciente sin alterar el historial."""
    hours = max(1, min(int(window_hours), 168))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    with connect(path) as db:
        totals = db.execute(
            """SELECT COUNT(*) AS checks_total,
                      COALESCE(SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END), 0) AS checks_up,
                      COALESCE(SUM(CASE WHEN status = 'down' THEN 1 ELSE 0 END), 0) AS checks_down,
                      AVG(CASE WHEN status = 'up' THEN latency_ms END) AS average_latency_ms
               FROM monitor_checks WHERE checked_at >= ?""",
            (since,),
        ).fetchone()
        monitor_rows = db.execute(
            """SELECT m.id AS monitor_id, m.name, m.kind, m.target, m.enabled,
                      m.interval_seconds, m.timeout_seconds, m.last_status, m.last_checked_at,
                      EXISTS (SELECT 1 FROM incidents i WHERE i.monitor_id = m.id AND i.status = 'open') AS incident_open,
                      COUNT(c.id) AS checks_total,
                      COALESCE(SUM(CASE WHEN c.status = 'up' THEN 1 ELSE 0 END), 0) AS checks_up,
                      COALESCE(SUM(CASE WHEN c.status = 'down' THEN 1 ELSE 0 END), 0) AS checks_down,
                      AVG(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS average_latency_ms,
                      MIN(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS min_latency_ms,
                      MAX(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS max_latency_ms
               FROM monitors m
               LEFT JOIN monitor_checks c
                 ON c.monitor_id = m.id AND c.checked_at >= ?
               GROUP BY m.id
               ORDER BY m.enabled DESC, m.name COLLATE NOCASE""",
            (since,),
        ).fetchall()
        monitors_total = db.execute("SELECT COUNT(*) FROM monitors").fetchone()[0]
        monitors_enabled = db.execute("SELECT COUNT(*) FROM monitors WHERE enabled = 1").fetchone()[0]
        incidents_open = db.execute("SELECT COUNT(*) FROM incidents WHERE status = 'open'").fetchone()[0]
        recovery_rows = db.execute(
            """SELECT opened_at, resolved_at FROM incidents
               WHERE status = 'resolved' AND resolved_at IS NOT NULL AND resolved_at >= ?""",
            (since,),
        ).fetchall()

    recovery_durations = []
    for incident in recovery_rows:
        elapsed = _elapsed_seconds(incident["opened_at"], incident["resolved_at"])
        if elapsed is not None:
            recovery_durations.append(elapsed)

    checks_total = int(totals["checks_total"] or 0)
    checks_up = int(totals["checks_up"] or 0)
    checks_down = int(totals["checks_down"] or 0)
    summary = {
        "checks_total": checks_total,
        "checks_up": checks_up,
        "checks_down": checks_down,
        "success_rate_percent": round(checks_up / checks_total * 100, 2) if checks_total else None,
        "average_latency_ms": round(float(totals["average_latency_ms"]), 2)
        if totals["average_latency_ms"] is not None else None,
        "monitors_total": int(monitors_total),
        "monitors_enabled": int(monitors_enabled),
        "incidents_open": int(incidents_open),
        "incidents_resolved": len(recovery_durations),
        "average_recovery_seconds": int(round(sum(recovery_durations) / len(recovery_durations)))
        if recovery_durations else None,
        "max_recovery_seconds": max(recovery_durations) if recovery_durations else None,
    }
    monitor_stats = []
    for row in monitor_rows:
        item = dict(row)
        total = int(item["checks_total"] or 0)
        up = int(item["checks_up"] or 0)
        item["enabled"] = bool(item["enabled"])
        item["success_rate_percent"] = round(up / total * 100, 2) if total else None
        for field in ("average_latency_ms", "min_latency_ms", "max_latency_ms"):
            item[field] = round(float(item[field]), 2) if item[field] is not None else None
        monitor_stats.append(item)

    return {
        "window_hours": hours,
        "since": since,
        "summary": summary,
        "monitors": monitor_stats,
    }


def get_monitor_latency_trend(monitor_id: int, window_hours: int = 24,
                              path: Path | None = None) -> dict[str, Any] | None:
    """Agrega la latencia histórica en buckets horarios (24 h) o de seis horas (7 días)."""
    hours = max(1, min(int(window_hours), 168))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    bucket_minutes = 60 if hours <= 24 else 360
    if bucket_minutes == 60:
        bucket_expr = "strftime('%Y-%m-%dT%H:00:00+00:00', checked_at)"
    else:
        bucket_expr = (
            "strftime('%Y-%m-%dT', checked_at) || "
            "printf('%02d:00:00+00:00', (CAST(strftime('%H', checked_at) AS INTEGER) / 6) * 6)"
        )
    with connect(path) as db:
        monitor = db.execute(
            "SELECT id, name, kind, target FROM monitors WHERE id = ?", (monitor_id,)
        ).fetchone()
        if monitor is None:
            return None
        rows = db.execute(
            f"""SELECT {bucket_expr} AS bucket_start,
                       COUNT(*) AS checks_total,
                       SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END) AS checks_up,
                       SUM(CASE WHEN status = 'down' THEN 1 ELSE 0 END) AS checks_down,
                       AVG(CASE WHEN status = 'up' THEN latency_ms END) AS average_latency_ms,
                       MIN(CASE WHEN status = 'up' THEN latency_ms END) AS min_latency_ms,
                       MAX(CASE WHEN status = 'up' THEN latency_ms END) AS max_latency_ms
                FROM monitor_checks
                WHERE monitor_id = ? AND checked_at >= ?
                GROUP BY bucket_start ORDER BY bucket_start ASC""",
            (monitor_id, since),
        ).fetchall()
    points = []
    for row in rows:
        point = dict(row)
        for key in ("average_latency_ms", "min_latency_ms", "max_latency_ms"):
            point[key] = round(float(point[key]), 2) if point[key] is not None else None
        points.append(point)
    return {
        "monitor": dict(monitor), "window_hours": hours, "since": since,
        "bucket_minutes": bucket_minutes, "points": points,
    }


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


def get_incidents(path: Path | None = None, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if status in {"open", "resolved"}:
        where = "WHERE i.status = ?"
        params.append(status)
    params.append(max(1, min(int(limit), 5000)))
    with connect(path) as db:
        rows = db.execute(
            f"""SELECT i.*, m.name AS monitor_name, m.kind, m.target
                FROM incidents i JOIN monitors m ON m.id = i.monitor_id
                {where} ORDER BY CASE WHEN i.status = 'open' THEN 0 ELSE 1 END, i.updated_at DESC, i.id DESC LIMIT ?""",
            params,
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        resolved = item["status"] == "resolved" and item.get("resolved_at") is not None
        end_at = item.get("resolved_at") if resolved else None
        duration = _elapsed_seconds(item.get("opened_at"), end_at)
        item["duration_seconds"] = duration
        item["time_to_recovery_seconds"] = duration if resolved else None
        item["duration_is_estimated"] = True
        item["duration_basis"] = (
            "first_failure_to_recovery_check" if resolved else "elapsed_since_first_failed_check"
        )
        items.append(item)
    return items


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
