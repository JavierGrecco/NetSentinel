"""Resumen y exportación de resultados de monitorización."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from .. import database

router = APIRouter()


@router.get("/api/monitoring/summary")
def monitoring_summary(hours: int = Query(default=24, ge=1, le=168)) -> dict:
    """Resume los resultados medidos en las últimas horas (máximo siete días)."""
    return database.get_monitor_analytics(window_hours=hours)


@router.get("/api/export/monitoring.csv")
def export_monitoring_csv(hours: int = Query(default=24, ge=1, le=168)) -> Response:
    return Response(
        content=database.export_monitoring_csv(window_hours=hours),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-monitoring-report.csv"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/export/incidents.csv")
def export_incidents_csv(status: str | None = Query(default=None)) -> Response:
    if status not in {None, "open", "resolved"}:
        raise HTTPException(status_code=422, detail="El estado debe ser open o resolved.")
    return Response(
        content=database.export_incidents_csv(status=status),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-incidents.csv"', "Cache-Control": "no-store"},
    )


@router.get("/api/monitors/{monitor_id}/latency")
def monitor_latency_trend(monitor_id: int, hours: int = Query(default=24, ge=1, le=168)) -> dict:
    trend = database.get_monitor_latency_trend(monitor_id, window_hours=hours)
    if trend is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return trend


@router.get("/api/export/monitor-latency.csv")
def export_monitor_latency_csv(monitor_id: int = Query(ge=1),
                               hours: int = Query(default=24, ge=1, le=168)) -> Response:
    content = database.export_monitor_latency_csv(monitor_id, window_hours=hours)
    if content is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-latency-trend.csv"', "Cache-Control": "no-store"},
    )
