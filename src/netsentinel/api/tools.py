"""Rutas HTTP de las herramientas DNS y TLS de NetSentinel.

Este módulo define el contrato HTTP de esa capacidad. La lógica de red vive en
los módulos especializados; aquí solo validamos entradas y traducimos errores
a respuestas HTTP estables.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from ..dns_config import get_dns_configuration
from ..dns_tools import DNSLookupError, cached_reverse_lookup_ip, lookup_hostname
from ..tls_tools import inspect_tls_endpoint

router = APIRouter(tags=["tools"])

# El middleware HTTP central mantiene la política de protección para estas rutas.
from .security import NETWORK_SIDE_EFFECT_GET_PATHS


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


@router.get("/api/tools/dns/configuration")
def dns_configuration() -> dict:
    """Lee la configuración DNS local sin modificarla ni consultar dominios externos."""
    return get_dns_configuration()


@router.get("/api/tools/dns/lookup")
def dns_lookup(hostname: str = Query(min_length=1, max_length=253)) -> dict:
    """Resuelve registros A/AAAA a pedido del usuario."""
    try:
        return lookup_hostname(hostname)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=502,
            detail="No se pudo resolver el nombre con el DNS configurado en el sistema.",
        ) from exc


@router.get("/api/tools/dns/reverse")
def dns_reverse_lookup(address: str = Query(min_length=1, max_length=64)) -> dict:
    """Consulta PTR para una IP ingresada explícitamente por el usuario."""
    try:
        return cached_reverse_lookup_ip(address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=502,
            detail="No se pudo obtener un registro PTR con el DNS configurado en el sistema.",
        ) from exc
