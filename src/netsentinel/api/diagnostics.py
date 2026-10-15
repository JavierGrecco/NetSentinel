"""Endpoint HTTP para diagnóstico puntual y explícito de conectividad."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..diagnostics import run_diagnostics

router = APIRouter()


@router.post("/api/diagnostics")
def diagnostics(request: Request) -> dict:
    request_id = getattr(request.state, "request_id", None)
    return run_diagnostics(request_id=request_id)
