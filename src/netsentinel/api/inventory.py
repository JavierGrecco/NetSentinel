"""Composición de las rutas HTTP del inventario.

Las rutas se mantienen en módulos por tarea: consulta/cambios de activos,
descubrimiento explícito y exportaciones. Este archivo conserva el punto de
registro histórico y no altera las URL, los métodos ni los cuerpos de respuesta.
"""
from __future__ import annotations

from fastapi import APIRouter

from .inventory_assets import router as assets_router
from .inventory_discovery import router as discovery_router
from .inventory_exports import router as exports_router

router = APIRouter()
router.include_router(assets_router)
router.include_router(discovery_router)
router.include_router(exports_router)
