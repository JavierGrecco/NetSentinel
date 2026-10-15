"""Respuestas seguras para errores de validación de solicitudes HTTP.

Este módulo transforma los errores de entrada en mensajes fijos y accionables.
No refleja los valores enviados por el cliente ni los guarda en el diario local.
"""
from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .security_headers import _error_response, _request_id


def _safe_validation_message(error_type: str) -> str:
    """Mapea tipos de validación a texto fijo para no reflejar valores de entrada."""
    messages = {
        "missing": "Falta completar este campo.",
        "string_too_short": "El texto es más corto que el mínimo permitido.",
        "string_too_long": "El texto supera la longitud máxima permitida.",
        "string_pattern_mismatch": "El texto no cumple el formato requerido.",
        "int_parsing": "Ingresá un número entero válido.",
        "int_type": "Este campo requiere un número entero.",
        "float_parsing": "Ingresá un número válido.",
        "float_type": "Este campo requiere un número.",
        "bool_parsing": "Ingresá un valor verdadero o falso.",
        "bool_type": "Este campo requiere un valor booleano.",
        "greater_than_equal": "El valor es menor que el mínimo permitido.",
        "greater_than": "El valor debe ser mayor que el límite indicado.",
        "less_than_equal": "El valor supera el máximo permitido.",
        "less_than": "El valor debe ser menor que el límite indicado.",
        "extra_forbidden": "Este campo no está permitido.",
        "literal_error": "El valor no coincide con ninguna de las opciones permitidas.",
        "enum": "Elegí una de las opciones permitidas.",
        "url_parsing": "Ingresá una URL válida.",
        "url_scheme": "La URL usa un protocolo no permitido.",
        "json_invalid": "El cuerpo de la solicitud no contiene JSON válido.",
        "value_error": "El valor no cumple una regla de validación.",
    }
    return messages.get(error_type, "El valor no cumple el formato esperado.")


async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return actionable validation details without reflecting submitted field values."""
    safe_errors = []
    for error in exc.errors():
        location = [
            part if isinstance(part, (str, int)) else str(part)
            for part in error.get("loc", ())
        ]
        safe_errors.append({
            "loc": location,
            "msg": _safe_validation_message(str(error.get("type", "value_error"))[:100]),
            "type": str(error.get("type", "value_error"))[:100],
        })
    return _error_response(
        request,
        status_code=422,
        content={
            "detail": safe_errors,
            "error_code": "NS-REQ-422",
            "request_id": _request_id(request),
            "next_action": "Corregí los campos indicados y volvé a enviar la solicitud.",
            "should_log": False,
            "registered_in_log": False,
        },
    )
