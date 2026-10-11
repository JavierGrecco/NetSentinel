"""Aplicación FastAPI de NetSentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from . import __version__
from . import database
from .diagnostics import run_diagnostics
from .discovery import read_neighbor_table


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.initialize()
    yield


app = FastAPI(
    title="NetSentinel",
    description="Inventario pasivo, lista de confianza y eventos de red local.",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
_STATIC = Path(__file__).parent / "static" / "index.html"


class DeviceUpdate(BaseModel):
    trusted: bool | None = None
    display_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class EventUpdate(BaseModel):
    acknowledged: bool = True


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC)


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
    neighbors, errors = read_neighbor_table()
    result = database.record_scan(neighbors, errors)
    result["message"] = (
        "Se combinaron las fuentes locales disponibles."
        if neighbors
        else "No se encontraron entradas reconocibles; esta versión no hace un barrido activo."
    )
    return result


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
