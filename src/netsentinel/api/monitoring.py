"""Rutas HTTP de monitorización, incidentes y diagnóstico de NetSentinel.

La composición de la aplicación y el ciclo de vida del supervisor permanecen
en `main.py`; este módulo concentra únicamente los contratos HTTP del dominio.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import database
from ..diagnostics import run_diagnostics
from ..monitoring import check_once, validate_spec


router = APIRouter()


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=16)
    target: str = Field(min_length=1, max_length=500)
    interval_seconds: int = Field(default=60, ge=15, le=86400)
    timeout_seconds: int = Field(default=3, ge=1, le=10)


class MonitorUpdate(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    interval_seconds: int | None = Field(default=None, ge=15, le=86400)
    timeout_seconds: int | None = Field(default=None, ge=1, le=10)


@router.get("/api/monitors")
def monitors() -> list[dict]:
    return database.list_monitors()


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


@router.post("/api/monitors", status_code=201)
def add_monitor(body: MonitorCreate) -> dict:
    try:
        kind, target, interval, timeout = validate_spec(body.kind, body.target, body.interval_seconds, body.timeout_seconds)
        return database.create_monitor(body.name, kind, target, interval, timeout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/api/monitors/{monitor_id}")
def edit_monitor(monitor_id: int, body: MonitorUpdate) -> dict:
    try:
        result = database.update_monitor(monitor_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return result


@router.delete("/api/monitors/{monitor_id}")
def remove_monitor(monitor_id: int) -> dict[str, bool]:
    if not database.delete_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return {"ok": True}


@router.post("/api/monitors/{monitor_id}/check")
def run_monitor_check(monitor_id: int) -> dict:
    monitor = next((item for item in database.list_monitors() if item["id"] == monitor_id), None)
    if monitor is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    try:
        return check_once(monitor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/api/monitors/{monitor_id}/checks")
def monitor_checks(monitor_id: int, limit: int = Query(default=30, ge=1, le=200)) -> list[dict]:
    checks = database.get_monitor_checks(monitor_id, limit=limit)
    if checks is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return checks


@router.get("/api/incidents")
def incidents(limit: int = Query(default=50, ge=1, le=200), status: str | None = Query(default=None)) -> list[dict]:
    if status not in {None, "open", "resolved"}:
        raise HTTPException(status_code=422, detail="El estado debe ser open o resolved.")
    return database.get_incidents(limit=limit, status=status)


@router.get("/api/notifications")
def notifications(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {
        "webhook_configured": bool(os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip()),
        "history": database.get_notification_log(limit=limit),
    }


@router.post("/api/diagnostics")
def diagnostics(request: Request) -> dict:
    request_id = getattr(request.state, "request_id", None)
    return run_diagnostics(request_id=request_id)
