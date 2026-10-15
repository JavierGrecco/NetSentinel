"""Respuestas de error HTTP seguras y útiles para el panel.

Convierte fallos conocidos en mensajes claros, conserva un identificador para
diagnóstico y evita devolver valores sensibles enviados por el usuario.
"""
from __future__ import annotations

import logging
from pathlib import Path
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..error_reporting import describe_http_error, describe_unhandled_exception, record_error_event
from .security import _error_response, _request_id


logger = logging.getLogger(__name__)


# Se mantienen los nombres históricos para el arranque y posibles consumidores internos.
from .validation_errors import _safe_validation_message, handle_request_validation_error


# Mensajes propios y revisados que pueden conservarse para errores DNS conocidos.
# Cualquier detalle 5xx que no esté en esta lista se reemplaza por un mensaje genérico.
_DNS_TIMEOUT_DETAIL = "El resolvedor DNS no respondió a tiempo; probá nuevamente."
_SAFE_HTTP_5XX_DETAILS = {
    502: frozenset({
        "No se pudo resolver el nombre con el DNS configurado en el sistema.",
        "No se pudo obtener un registro PTR con el DNS configurado en el sistema.",
        "El resolvedor DNS devolvió un error.",
        "El resolvedor DNS devolvió un error al consultar PTR.",
        "No se pudo iniciar una consulta limitada al resolvedor del sistema.",
    }),
    503: frozenset({_DNS_TIMEOUT_DETAIL}),
}


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Añade referencias y códigos sin revelar texto arbitrario de errores del servidor."""
    code, next_action = describe_http_error(exc.status_code)
    request_id = _request_id(request)
    safe_path = getattr(request.scope.get("route"), "path", "<unmatched-route>")

    # Un timeout del resolvedor es una condición de red esperable, no necesariamente
    # un fallo del programa. Conservamos su mensaje conocido y no lo registramos como
    # un error interno; otros errores 5xx siguen la política normal de registro.
    is_dns_timeout = (
        exc.status_code == 503
        and isinstance(exc.detail, str)
        and exc.detail == _DNS_TIMEOUT_DETAIL
    )
    should_log = exc.status_code >= 500 and not is_dns_timeout
    registered = False
    if should_log:
        registered = record_error_event({
            "error_code": code,
            "request_id": request_id,
            "category": "http_server",
            "severity": "error",
            "exception_type": "StarletteHTTPException",
            "method": request.method,
            "path": safe_path,
            "reason": "Explicit HTTP 5xx response",
        })
        logger.error(
            "HTTP server failure code=%s request_id=%s status=%s method=%s path=%s persisted=%s",
            code, request_id, exc.status_code, request.method, safe_path, registered,
        )

    safe_detail = exc.detail
    if exc.status_code >= 500:
        allowed_details = _SAFE_HTTP_5XX_DETAILS.get(exc.status_code, frozenset())
        if not isinstance(exc.detail, str) or exc.detail not in allowed_details:
            safe_detail = {
                502: "La comprobación externa no pudo completarse.",
                503: "El servicio todavía no está disponible temporalmente.",
            }.get(
                exc.status_code,
                "NetSentinel no pudo completar la operación por un error interno.",
            )

    return _error_response(
        request,
        status_code=exc.status_code,
        content={
            "detail": safe_detail,
            "error_code": code,
            "request_id": request_id,
            "next_action": next_action,
            "should_log": should_log,
            "registered_in_log": registered,
        },
        headers=dict(exc.headers or {}),
    )


async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
    """Log a classified failure without exception text, request values, or query strings."""
    error = describe_unhandled_exception(exc)
    request_id = _request_id(request)
    # Traceback locations help developers find the fault without formatting exception
    # messages or source lines that could contain submitted secrets.
    frames = " <- ".join(
        f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
        for frame in traceback.extract_tb(exc.__traceback__)
    )
    safe_path = getattr(request.scope.get("route"), "path", "<unmatched-route>")
    registered = record_error_event({
        "error_code": error.code,
        "request_id": request_id,
        "category": error.category,
        "severity": error.log_level,
        "exception_type": type(exc).__name__,
        "method": request.method,
        "path": safe_path,
        "reason": error.log_reason,
        "frames": frames,
    })
    logger.log(
        getattr(logging, error.log_level.upper(), logging.ERROR),
        "Application failure code=%s request_id=%s category=%s exception_type=%s method=%s path=%s reason=%s frames=%s persisted=%s",
        error.code, request_id, error.category, type(exc).__name__,
        request.method, safe_path, error.log_reason, frames, registered,
    )
    next_action = error.next_action
    if not registered:
        next_action += " No se pudo guardar el registro local de errores; revisá el espacio disponible y los permisos de la carpeta de datos."
    return _error_response(
        request,
        status_code=500,
        content={
            "detail": error.message,
            "error_code": error.code,
            "request_id": request_id,
            "next_action": next_action,
            "should_log": True,
            "registered_in_log": registered,
        },
    )
