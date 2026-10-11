"""Aplicación FastAPI de NetSentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from typing import AsyncIterator
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from . import database
from .diagnostics import run_diagnostics
from .local_discovery import discover_local_network
from .monitoring import MonitorSupervisor, check_once, validate_spec


_supervisor = MonitorSupervisor()
_scan_lock = Lock()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.initialize()
    scheduler_disabled = os.environ.get("NETSENTINEL_DISABLE_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}
    if not scheduler_disabled:
        _supervisor.start()
    try:
        yield
    finally:
        _supervisor.stop()


app = FastAPI(
    title="NetSentinel",
    description="Inventario local, descubrimiento bajo demanda, lista de confianza, eventos y diagnóstico de red.",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC = _STATIC_DIR / "index.html"
_MONITORS_STATIC = _STATIC_DIR / "monitors.html"


class DeviceUpdate(BaseModel):
    trusted: bool | None = None
    display_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class EventUpdate(BaseModel):
    acknowledged: bool = True


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


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC)


@app.get("/monitors", include_in_schema=False)
def monitors_page() -> FileResponse:
    return FileResponse(_MONITORS_STATIC)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "name": "NetSentinel", "version": __version__}


@app.get("/api/summary")
def summary() -> dict:
    return database.get_summary()


@app.get("/api/devices")
def devices(q: str = Query(default="", max_length=160)) -> list[dict]:
    return database.list_devices(query=q)


@app.get("/api/events")
def events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return database.get_events(limit=limit)


@app.get("/api/scans")
def scans(limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return database.get_scans(limit=limit)


@app.get("/api/devices/{device_id}/addresses")
def device_addresses(device_id: int) -> list[dict]:
    addresses = database.get_device_addresses(device_id)
    if addresses is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return addresses


@app.post("/api/scan")
def scan() -> dict:
    """Ejecuta un único descubrimiento local a la vez para evitar tráfico duplicado."""
    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Ya hay un descubrimiento de red en curso. Esperá a que termine antes de iniciar otro.",
        )
    try:
        neighbors, errors, discovery = discover_local_network()
        result = database.record_scan(neighbors, errors, discovery=discovery)
        result["discovery"] = discovery
        result["message"] = (
            "Se completó el descubrimiento automático de las subredes locales indicadas."
            if discovery["networks"]
            else "No se pudo identificar una subred privada adecuada para buscar dispositivos."
        )
        return result
    finally:
        _scan_lock.release()


@app.patch("/api/devices/{device_id}")
def edit_device(device_id: int, body: DeviceUpdate) -> dict:
    try:
        result = database.update_device(
            device_id,
            trusted=body.trusted,
            display_name=body.display_name,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return result


@app.patch("/api/events/{event_id}")
def edit_event(event_id: int, body: EventUpdate) -> dict[str, bool]:
    if body.acknowledged:
        updated = database.acknowledge_event(event_id)
    else:
        # No se ofrece reabrir eventos en esta primera versión.
        updated = False
    if not updated:
        raise HTTPException(status_code=404, detail="No se encontró el evento o no se admite el cambio solicitado.")
    return {"ok": True}


@app.get("/api/monitors")
def monitors() -> list[dict]:
    return database.list_monitors()


@app.post("/api/monitors", status_code=201)
def add_monitor(body: MonitorCreate) -> dict:
    try:
        kind, target, interval, timeout = validate_spec(body.kind, body.target, body.interval_seconds, body.timeout_seconds)
        return database.create_monitor(body.name, kind, target, interval, timeout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/monitors/{monitor_id}")
def edit_monitor(monitor_id: int, body: MonitorUpdate) -> dict:
    try:
        result = database.update_monitor(monitor_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return result


@app.delete("/api/monitors/{monitor_id}")
def remove_monitor(monitor_id: int) -> dict[str, bool]:
    if not database.delete_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return {"ok": True}


@app.post("/api/monitors/{monitor_id}/check")
def run_monitor_check(monitor_id: int) -> dict:
    monitor = next((item for item in database.list_monitors() if item["id"] == monitor_id), None)
    if monitor is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    try:
        return check_once(monitor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/monitors/{monitor_id}/checks")
def monitor_checks(monitor_id: int, limit: int = Query(default=30, ge=1, le=200)) -> list[dict]:
    checks = database.get_monitor_checks(monitor_id, limit=limit)
    if checks is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return checks


@app.get("/api/incidents")
def incidents(limit: int = Query(default=50, ge=1, le=200), status: str | None = Query(default=None)) -> list[dict]:
    if status not in {None, "open", "resolved"}:
        raise HTTPException(status_code=422, detail="El estado debe ser open o resolved.")
    return database.get_incidents(limit=limit, status=status)


@app.get("/api/notifications")
def notifications(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {
        "webhook_configured": bool(os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip()),
        "history": database.get_notification_log(limit=limit),
    }


@app.post("/api/diagnostics")
def diagnostics() -> dict:
    return run_diagnostics()


@app.get("/api/export/devices.csv")
def export_devices_csv() -> Response:
    return Response(
        content=database.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-devices.csv"'},
    )


@app.get("/api/export/data.json")
def export_data_json() -> Response:
    return Response(
        content=database.export_json(),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-export.json"'},
    )


# Sirve CSS y otros recursos desde el paquete local.
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
