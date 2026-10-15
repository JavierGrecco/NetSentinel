"""Composición de los routers HTTP de actividad autorizada.

Cada grupo de rutas tiene un dueño claro. Se reexportan los modelos históricos
para conservar los imports internos que usan los tests y consumidores del paquete.
"""
from __future__ import annotations

from fastapi import APIRouter

from .activity_deletion import router as deletion_router
from .activity_import import router as import_router
from .activity_models import (
    ActivityCSVImport,
    ActivityDeleteRequest,
    ActivityDeleteSelection,
    ActivityEventIngest,
    ActivityRetentionUpdate,
    ActivitySessionCreate,
)
from .activity_read import router as read_router
from .activity_retention import router as retention_router
from .activity_sessions import router as sessions_router

router = APIRouter()
router.include_router(read_router)
router.include_router(sessions_router)
router.include_router(import_router)
router.include_router(deletion_router)
router.include_router(retention_router)
