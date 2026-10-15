"""Fachada de compatibilidad para el almacenamiento de actividad.

Las operaciones SQLite están separadas por responsabilidad en módulos específicos.
Se conservan los nombres históricos para que los servicios actuales y sus contratos
sigan funcionando mientras la migración interna avanza de forma gradual.
"""
from __future__ import annotations

# Se conserva este atributo porque algunos consumidores internos antiguos acceden a
# activity_repository.database. El código nuevo debe usar los servicios de aplicación.
from . import database
from .activity_deletion_repository import (
    _ALLOWED_ACTIVITY_SCOPE_CLAUSES,
    _require_bounded_scope,
    count_activity_scope,
    delete_activity_scope,
)
from .activity_import_repository import (
    _MANUAL_IMPORT_DEDUP_FIELDS,
    import_manual_events,
)
from .activity_read_repository import (
    _ACTIVITY_READ_FILTER_CLAUSES,
    _require_activity_read_filters,
    get_activity_export_rows,
    get_activity_snapshot,
)
from .activity_repository_support import _require_device, require_device_exists
from .activity_retention_repository import (
    DEFAULT_RETENTION_DAYS,
    MAX_RETENTION_DAYS,
    _utc_iso,
    cleanup,
    get_retention_days,
    update_retention,
)
from .activity_session_repository import (
    get_session_for_device,
    insert_event,
    start_session,
    stop_session,
)
