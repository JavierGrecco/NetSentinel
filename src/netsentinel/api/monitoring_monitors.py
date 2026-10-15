"""Rutas HTTP para administrar monitores, incidentes y notificaciones locales."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import database
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
