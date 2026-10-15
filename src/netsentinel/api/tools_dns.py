"""Rutas HTTP para la configuración y las consultas DNS explícitas."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..dns_config import get_dns_configuration
from ..dns_tools import DNSLookupError, cached_reverse_lookup_ip, lookup_hostname

router = APIRouter(tags=["tools"])


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
