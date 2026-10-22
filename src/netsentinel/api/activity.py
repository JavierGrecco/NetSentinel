"""Composición de los routers HTTP de actividad autorizada.

Cada grupo de rutas tiene un dueño claro. Se reexportan los modelos, funciones
de ruta y módulo de servicio históricos para conservar imports internos existentes.
"""
from __future__ import annotations

from fastapi import APIRouter

from .. import activity_tracking
from .activity_deletion import (
    delete_family_activity,
    preview_family_activity_delete,
    router as deletion_router,
)
from .activity_import import (
    import_family_activity,
    preview_family_activity,
    router as import_router,
)
from .activity_zeek_import import (
    import_zeek_activity,
    preview_zeek_activity,
    router as zeek_import_router,
)
from .activity_models import (
    ActivityCSVImport,
    ActivityDeleteRequest,
    ActivityDeleteSelection,
    ActivityEventIngest,
    ActivityRetentionUpdate,
    ActivitySessionCreate,
    ActivityZeekImport,
)
from .activity_read import (
    export_family_activity_csv,
    get_family_activity,
    router as read_router,
)
from .activity_retention import (
    router as retention_router,
    set_family_activity_retention,
)
from .activity_sessions import (
    ingest_family_activity,
    router as sessions_router,
    start_family_activity,
    stop_family_activity,
)

router = APIRouter()
router.include_router(read_router)
router.include_router(sessions_router)
router.include_router(import_router)
router.include_router(zeek_import_router)
router.include_router(deletion_router)
router.include_router(retention_router)
