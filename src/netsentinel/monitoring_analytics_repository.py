"""Consultas de historial, incidentes y métricas de monitorización."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .database_storage import _elapsed_seconds, connect

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
    # Use one UTC reference for both the query boundary and the completed bucket grid.
    now = datetime.now(timezone.utc).replace(microsecond=0)
    since_at = now - timedelta(hours=hours)
    since = since_at.isoformat(timespec="seconds")
    bucket_minutes = 60 if hours <= 24 else 360
    bucket_seconds = bucket_minutes * 60
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
    observed_by_bucket = {str(row["bucket_start"]): dict(row) for row in rows}
    first_bucket_epoch = (int(since_at.timestamp()) // bucket_seconds) * bucket_seconds
    last_bucket_epoch = (int(now.timestamp()) // bucket_seconds) * bucket_seconds
    cursor = datetime.fromtimestamp(first_bucket_epoch, tz=timezone.utc)
    last_bucket = datetime.fromtimestamp(last_bucket_epoch, tz=timezone.utc)
    points = []
    while cursor <= last_bucket:
        bucket_start = cursor.strftime("%Y-%m-%dT%H:00:00+00:00")
        point = observed_by_bucket.get(bucket_start)
        if point is None:
            # Keep the time axis continuous: a missing check is not a failed check.
            point = {
                "bucket_start": bucket_start,
                "checks_total": 0,
                "checks_up": 0,
                "checks_down": 0,
                "average_latency_ms": None,
                "min_latency_ms": None,
                "max_latency_ms": None,
            }
        else:
            point["checks_total"] = int(point["checks_total"] or 0)
            point["checks_up"] = int(point["checks_up"] or 0)
            point["checks_down"] = int(point["checks_down"] or 0)
            for key in ("average_latency_ms", "min_latency_ms", "max_latency_ms"):
                point[key] = round(float(point[key]), 2) if point[key] is not None else None
        points.append(point)
        cursor += timedelta(seconds=bucket_seconds)

    return {
        "monitor": dict(monitor), "window_hours": hours, "since": since,
        "bucket_minutes": bucket_minutes, "points": points,
    }

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
