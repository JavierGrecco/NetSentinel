"""API de solo lectura para el mapa mundial de IP observadas."""
from __future__ import annotations

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, Field

from .. import geolocation_service

class GeolocationLookupRequest(BaseModel):
    """Direcciones ya resueltas por el usuario; esta API no ejecuta DNS."""

    addresses: list[str] = Field(min_length=1, max_length=32)


router = APIRouter(tags=["geolocation"])


@router.get("/api/geolocation/map")
def get_world_map(
    response: Response,
    limit: int = Query(default=250, ge=1, le=500),
) -> dict:
    """Devuelve ubicaciones aproximadas a partir de eventos guardados localmente."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return geolocation_service.get_world_map_data(limit=limit)


@router.post("/api/geolocation/lookup")
def lookup_current_dns_addresses(
    request: GeolocationLookupRequest,
    response: Response,
) -> dict:
    """Enriquece IP recibidas por una consulta explícita, sin guardarlas como eventos."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return geolocation_service.lookup_public_ips(request.addresses)
