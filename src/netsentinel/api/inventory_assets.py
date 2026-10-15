"""Rutas HTTP para consultar y mantener los activos y eventos locales."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .. import __version__, database
from ..dns_tools import DNSLookupError, cached_reverse_lookup_ip

router = APIRouter()


class DeviceUpdate(BaseModel):
    """Campos que el usuario puede modificar en un dispositivo."""

    trusted: bool | None = None
    display_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class EventUpdate(BaseModel):
    """Campos permitidos al actualizar el estado de un evento."""

    acknowledged: bool = True


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "name": "NetSentinel", "version": __version__}


@router.get("/api/summary")
def summary() -> dict:
    return database.get_summary()


@router.get("/api/devices")
def devices(q: str = Query(default="", max_length=160)) -> list[dict]:
    return database.list_devices(query=q)


@router.get("/api/events")
def events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return database.get_events(limit=limit)


@router.get("/api/scans")
def scans(limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return database.get_scans(limit=limit)


@router.get("/api/devices/{device_id}/history")
def device_history(device_id: int, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Consulta el historial de observaciones del inventario para un dispositivo."""
    result = database.get_device_history(device_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return result


@router.get("/api/devices/{device_id}/addresses")
def device_addresses(device_id: int) -> list[dict]:
    addresses = database.get_device_addresses(device_id)
    if addresses is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return addresses


@router.get("/api/devices/{device_id}/dns-reverse")
def device_dns_reverse_lookup(device_id: int) -> dict:
    """Consulta PTR de la dirección observada más recientemente, solo bajo demanda."""
    addresses = database.get_device_addresses(device_id)
    if addresses is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    if not addresses:
        raise HTTPException(status_code=404, detail="El dispositivo no tiene direcciones observadas para consultar.")
    address = addresses[0]["ip_address"]
    try:
        result = cached_reverse_lookup_ip(address)
        result["device_id"] = device_id
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail="No se pudo obtener un registro PTR para la dirección observada.") from exc


@router.patch("/api/devices/{device_id}")
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


@router.patch("/api/events/{event_id}")
def edit_event(event_id: int, body: EventUpdate) -> dict[str, bool]:
    if body.acknowledged:
        updated = database.acknowledge_event(event_id)
    else:
        # No se ofrece reabrir eventos en esta primera versión.
        updated = False
    if not updated:
        raise HTTPException(status_code=404, detail="No se encontró el evento o no se admite el cambio solicitado.")
    return {"ok": True}
