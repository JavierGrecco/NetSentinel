"""Aplicación FastAPI de NetSentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
import base64
import hashlib
import ipaddress
import logging
import os
from pathlib import Path
import re
import traceback
import uuid
from typing import AsyncIterator
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from . import database
from .error_reporting import describe_http_error, describe_unhandled_exception
from .monitoring import MonitorSupervisor
from .api.activity import router as activity_router
from .api.tools import NETWORK_SIDE_EFFECT_GET_PATHS, router as tools_router
from .api.findings import router as findings_router
from .api.inventory import router as inventory_router
from .api.monitoring import router as monitoring_router
from .api.pages import router as pages_router


logger = logging.getLogger(__name__)


_supervisor = MonitorSupervisor()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.initialize()
    scheduler_disabled = os.environ.get("NETSENTINEL_DISABLE_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}
    if scheduler_disabled:
        # Keep retention deterministic in local/test deployments that disable the scheduler.
        _supervisor.cleanup_history_if_due(force=True)
    else:
        _supervisor.start()
    try:
        yield
    finally:
        _supervisor.stop()


_RFC1918_HOST_NETWORKS = tuple(
    ipaddress.IPv4Network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_IPV6_UNIQUE_LOCAL = ipaddress.IPv6Network("fc00::/7")
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# These GET routes initiate DNS traffic. They must not be triggerable by pages
# from another origin merely by embedding a local URL in an image/link/script.
_NETWORK_SIDE_EFFECT_GET_PATHS = NETWORK_SIDE_EFFECT_GET_PATHS
_DEVICE_DNS_REVERSE_PATH = re.compile(r"^/api/devices/\d+/dns-reverse$")


def _host_is_allowed(host: str | None) -> bool:
    """Allow loopback/private LAN IPs and explicit extra hostnames only."""
    if not host:
        return False
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        extras = {
            item.strip().rstrip(".").lower()
            for item in os.environ.get("NETSENTINEL_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        }
        return normalized in extras
    if address.is_loopback:
        return True
    if isinstance(address, ipaddress.IPv4Address):
        return any(address in network for network in _RFC1918_HOST_NETWORKS)
    return address in _IPV6_UNIQUE_LOCAL


def _same_origin(origin: str, request: Request) -> bool:
    """Compare scheme, normalized host and effective port without trusting Origin."""
    try:
        parsed = urlsplit(origin)
        origin_host_value = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not origin_host_value:
        return False
    request_host = (request.url.hostname or "").rstrip(".").lower()
    origin_host = origin_host_value.rstrip(".").lower()
    request_scheme = request.url.scheme.lower()
    origin_scheme = parsed.scheme.lower()
    if request_host != origin_host or request_scheme != origin_scheme:
        return False
    try:
        request_port = request.url.port or (443 if request_scheme == "https" else 80)
        origin_port = parsed.port or (443 if origin_scheme == "https" else 80)
    except ValueError:
        return False
    return request_port == origin_port


def _is_network_side_effect_get(path: str) -> bool:
    """Identify GET endpoints that can initiate outbound DNS lookups."""
    return path in _NETWORK_SIDE_EFFECT_GET_PATHS or bool(_DEVICE_DNS_REVERSE_PATH.fullmatch(path))


app = FastAPI(
    title="NetSentinel",
    description="Inventario local, descubrimiento bajo demanda, lista de confianza, eventos y diagnóstico de red.",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# La composición registra routers por capacidad; las rutas y sus contratos viven
# en el módulo dueño, no en este archivo de arranque.
app.include_router(tools_router)
app.include_router(activity_router)
app.include_router(findings_router)
app.include_router(inventory_router)
app.include_router(monitoring_router)
app.include_router(pages_router)

_STATIC_DIR = Path(__file__).parent / "static"
_STATIC = _STATIC_DIR / "index.html"
_MONITORS_STATIC = _STATIC_DIR / "monitors.html"
_ACTIVITY_STATIC = _STATIC_DIR / "activity.html"


_APP_HTML_PATHS = {
    "/": _STATIC,
    "/monitors": _MONITORS_STATIC,
    "/activity": _ACTIVITY_STATIC,
    "/tools": _STATIC_DIR / "tools.html",
    "/findings": _STATIC_DIR / "findings.html",
}
_INLINE_SCRIPT_PATTERN = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def _inline_script_hashes_in_html(content: str) -> tuple[str, ...]:
    """Return CSP SHA-256 sources for non-empty inline scripts in trusted HTML."""
    # The HTML parser normalizes CRLF and CR to LF before calculating script hashes.
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    hashes: list[str] = []
    for match in _INLINE_SCRIPT_PATTERN.finditer(normalized):
        script = match.group(1)
        if not script.strip():
            continue
        digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
        hashes.append(f"'sha256-{digest}'")
    return tuple(hashes)


def _inline_script_hashes(path: str) -> tuple[str, ...]:
    """Hash trusted inline script blocks in one packaged HTML page for CSP."""
    html_path = _APP_HTML_PATHS.get(path)
    if html_path is None or not html_path.is_file():
        return ()
    return _inline_script_hashes_in_html(html_path.read_text(encoding="utf-8"))


def _base_content_security_policy(path: str) -> str:
    """Allow fixed inline scripts by content hash, not by the unsafe-inline escape."""
    script_sources = " ".join(("'self'", *_inline_script_hashes(path)))
    return (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "frame-src 'none'; form-action 'self'; "
        f"script-src {script_sources}; style-src 'self'; "
        "img-src 'self' data:; font-src 'self' data:; connect-src 'self'"
    )


def _apply_security_headers(response: Response, *, page_path: str = "") -> Response:
    """Evita cachés locales y aplica una política defensiva uniforme al navegador."""
    # El inventario, el historial y las exportaciones pueden revelar topología y
    # actividad sensibles. No permitimos que navegadores o proxies los almacenen.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", _base_content_security_policy(page_path))
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
    return response


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


def _request_id(request: Request) -> str:
    """Return the identifier created for this request, including handler fallbacks."""
    current = getattr(request.state, "request_id", None)
    if isinstance(current, str) and re.fullmatch(r"[A-F0-9]{12}", current):
        return current
    return uuid.uuid4().hex[:12].upper()


def _error_response(
    request: Request,
    *,
    status_code: int,
    content: dict,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Add correlation metadata and the app's defensive headers to an error."""
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = _request_id(request)
    return _apply_security_headers(
        JSONResponse(status_code=status_code, content=content, headers=response_headers)
    )


@app.exception_handler(RequestValidationError)
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
            "registered_in_log": False,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Attach stable error metadata without logging expected client-side rejections."""
    code, next_action = describe_http_error(exc.status_code)
    request_id = _request_id(request)
    if exc.status_code >= 500:
        logger.error(
            "HTTP server failure code=%s request_id=%s status=%s method=%s path=%s",
            code, request_id, exc.status_code, request.method, request.url.path,
        )
    return _error_response(
        request,
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": code,
            "request_id": request_id,
            "next_action": next_action,
            "registered_in_log": exc.status_code >= 500,
        },
        headers=dict(exc.headers or {}),
    )


@app.exception_handler(Exception)
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
    logger.log(
        getattr(logging, error.log_level.upper(), logging.ERROR),
        "Application failure code=%s request_id=%s category=%s exception_type=%s method=%s path=%s reason=%s frames=%s",
        error.code, request_id, error.category, type(exc).__name__,
        request.method, request.url.path, error.log_reason, frames,
    )
    return _error_response(
        request,
        status_code=500,
        content={
            "detail": error.message,
            "error_code": error.code,
            "request_id": request_id,
            "next_action": error.next_action,
            "registered_in_log": True,
        },
    )


@app.middleware("http")
async def protect_local_app(request: Request, call_next):
    """Mitiga DNS rebinding/CSRF y aplica cabeceras a todas las respuestas."""
    request_id = uuid.uuid4().hex[:12].upper()
    request.state.request_id = request_id
    if not _host_is_allowed(request.url.hostname):
        return _error_response(
            request,
            status_code=400,
            content={
                "detail": "Host no permitido para NetSentinel.",
                "error_code": "NS-HTTP-400",
                "request_id": request_id,
                "next_action": "Abrí NetSentinel usando la dirección local indicada por la aplicación.",
                "registered_in_log": False,
            },
        )

    if request.method.upper() == "GET" and _is_network_side_effect_get(request.url.path):
        # Modern browsers expose Fetch Metadata even for image/link requests
        # whose Origin header may be absent. Direct navigation (Sec-Fetch-Site:
        # none) remains available; requests initiated by the app are same-origin.
        fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
        origin = request.headers.get("origin")
        cross_site_fetch = fetch_site and fetch_site not in {"same-origin", "none"}
        cross_origin_header = origin and not _same_origin(origin, request)
        if cross_site_fetch or cross_origin_header:
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Consulta de red iniciada desde otro origen bloqueada.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Iniciá la consulta desde el panel local de NetSentinel.",
                    "registered_in_log": False,
                },
            )

    if request.method.upper() in _MUTATING_METHODS:
        fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
        # Reject same-site as well as cross-site requests. A malicious sibling
        # origin may be "same-site" without being the exact UI origin; browser
        # Fetch Metadata is available even when an Origin header is omitted.
        non_same_origin_fetch = fetch_site and fetch_site not in {"same-origin", "none"}
        if non_same_origin_fetch:
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Solicitud desde otro origen bloqueada.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Iniciá la operación desde el panel local de NetSentinel.",
                    "registered_in_log": False,
                },
            )
        origin = request.headers.get("origin")
        if origin and not _same_origin(origin, request):
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Origen no permitido para esta operación.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Recargá el panel local y volvé a intentar la operación desde allí.",
                    "registered_in_log": False,
                },
            )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return _apply_security_headers(response, page_path=request.url.path)


@app.get("/api/docs", include_in_schema=False)
def api_docs() -> Response:
    """Serve Swagger UI with a per-response hash for its generated inline initializer."""
    response = get_swagger_ui_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
    html = response.body.decode("utf-8")
    inline_hashes = _inline_script_hashes_in_html(html)
    script_sources = " ".join(("'self'", *inline_hashes, "https://cdn.jsdelivr.net"))
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "frame-src 'none'; form-action 'self'; "
        f"script-src {script_sources}; style-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; font-src 'self' data:; connect-src 'self'"
    )
    return response

# Sirve CSS y otros recursos desde el paquete local.
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
