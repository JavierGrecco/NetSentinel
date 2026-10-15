"""Endpoint de descubrimiento local bajo demanda y con concurrencia limitada."""
from __future__ import annotations

from threading import Lock

from fastapi import APIRouter, HTTPException

from .. import database
from ..local_discovery import discover_local_network

router = APIRouter()
_scan_lock = Lock()


@router.post("/api/scan")
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
