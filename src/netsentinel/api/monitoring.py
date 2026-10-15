"""Composición de las rutas HTTP de monitorización.

Los contratos se mantienen en routers pequeños: gestión operativa, informes y
exportaciones, y diagnóstico puntual. Este módulo conserva el punto de registro
que ya utiliza la aplicación, sin cambiar las URL ni los métodos HTTP.
"""
from __future__ import annotations

from fastapi import APIRouter

from .diagnostics import router as diagnostics_router
from .monitoring_monitors import router as monitors_router
from .monitoring_reports import router as reports_router

router = APIRouter()
router.include_router(monitors_router)
router.include_router(reports_router)
router.include_router(diagnostics_router)
