"""Aplicación FastAPI de NetSentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from . import database
from .monitoring import MonitorSupervisor
from .api.activity import router as activity_router
from .api.tools import router as tools_router
from .api.findings import router as findings_router
from .api.inventory import router as inventory_router
from .api.monitoring import router as monitoring_router
from .api.pages import router as pages_router
from .api.security import (
    _APP_HTML_PATHS,
    _NETWORK_SIDE_EFFECT_GET_PATHS,
    _apply_security_headers,
    _base_content_security_policy,
    _error_response,
    _host_is_allowed,
    _inline_script_hashes,
    _inline_script_hashes_in_html,
    _is_network_side_effect_get,
    _same_origin,
    protect_local_app,
)
from .api.error_handling import (
    handle_http_exception,
    handle_request_validation_error,
    handle_unexpected_exception,
)


_SUPERVISOR = MonitorSupervisor()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.initialize()
    scheduler_disabled = os.environ.get("NETSENTINEL_DISABLE_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}
    if scheduler_disabled:
        # Keep retention deterministic in local/test deployments that disable the scheduler.
        _SUPERVISOR.cleanup_history_if_due(force=True)
    else:
        _SUPERVISOR.start()
    try:
        yield
    finally:
        _SUPERVISOR.stop()


app = FastAPI(
    title="NetSentinel",
    description="Inventario local, descubrimiento bajo demanda, lista de confianza, eventos y diagnóstico de red.",
    version=__version__,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)

# Las respuestas HTTP de error se registran de forma explícita en el punto de composición.
app.add_exception_handler(RequestValidationError, handle_request_validation_error)
app.add_exception_handler(StarletteHTTPException, handle_http_exception)
app.add_exception_handler(Exception, handle_unexpected_exception)

# La composición registra routers por capacidad; las rutas y sus contratos viven
# en el módulo dueño, no en este archivo de arranque.
app.include_router(tools_router)
app.include_router(activity_router)
app.include_router(findings_router)
app.include_router(inventory_router)
app.include_router(monitoring_router)
app.include_router(pages_router)

# El middleware de seguridad se mantiene en un módulo específico y no importa app.
app.middleware("http")(protect_local_app)

_STATIC_DIR = Path(__file__).parent / "static"


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
