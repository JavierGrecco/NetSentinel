"""API de solo lectura para reconstruir la topología de una lectura guardada.

La API publica el mismo modelo neutral que pueden consumir distintas interfaces.
No realiza descubrimientos ni dibuja enlaces físicos o tráfico no observado.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Path

from ..topology_graph import build_topology_graph
from ..topology_service import load_topology_for_scan

router = APIRouter()


@router.get("/api/scans/{scan_id}/topology")
def scan_topology(scan_id: int = Path(..., ge=1)) -> dict:
    """Devuelve nodos, relaciones, contadores y advertencias de una lectura."""
    model = load_topology_for_scan(scan_id)
    if model.scan_id is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró la lectura solicitada.",
        )
    return asdict(build_topology_graph(model))
