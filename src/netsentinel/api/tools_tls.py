"""Rutas HTTP para la inspección TLS puntual y acotada."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ..tls_tools import inspect_tls_endpoint

router = APIRouter(tags=["tools"])


class TLSInspectionRequest(BaseModel):
    """Datos permitidos para inspeccionar un endpoint TLS puntual."""

    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=443, ge=1, le=65535, strict=True)


@router.post("/api/tools/tls/inspect")
def tls_endpoint_inspection(body: TLSInspectionRequest) -> dict:
    """Inspecciona un handshake TLS sin solicitar contenido HTTP ni guardar resultados."""
    try:
        return inspect_tls_endpoint(body.host, body.port)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
