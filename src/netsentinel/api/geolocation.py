"""API de solo lectura para el mapa mundial de IP observadas."""
from __future__ import annotations

from fastapi import APIRouter, Query, Response

from .. import geolocation_service

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
