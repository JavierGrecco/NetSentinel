"""Composición de los routers HTTP de herramientas DNS y TLS."""
from __future__ import annotations

from fastapi import APIRouter

from .tools_dns import router as dns_router
from .tools_tls import router as tls_router

router = APIRouter()
# Conserva el registro histórico de rutas para que main.py no tenga que cambiar.
router.include_router(tls_router)
router.include_router(dns_router)
