"""Fachada de compatibilidad para las operaciones SQLite de NetSentinel.

La implementación está separada por capacidades. Este módulo conserva las funciones
históricas que usan la API, la CLI y los servicios; las nuevas reglas de negocio no
deben agregarse aquí. Para cambiar una consulta, editá el repositorio responsable.
"""
from __future__ import annotations

from contextlib import contextmanager
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterator

from .config import database_path
from .network_models import Neighbor
from . import database_storage as _storage
from .database_storage import (
    _elapsed_seconds,
    _ensure_private_directory,
    _harden_database_file,
    utc_now,
)
from .events_repository import _insert_event, acknowledge_event, get_events
from .inventory_repository import (
    _device_dict,
    _ip_sort_key,
    get_device_addresses,
    get_device_history,
    get_scans,
    list_devices,
    record_scan,
    update_device,
)
from .dashboard_repository import get_summary
from .data_export_service import (
    export_csv,
    export_json,
    export_sqlite_backup as _export_sqlite_backup,
)
from .monitoring_repository import (
    cleanup_monitor_history,
    create_monitor,
    delete_monitor,
    get_incidents,
    get_monitor_analytics,
    get_monitor_checks,
    get_monitor_latency_trend,
    get_notification_log,
    list_monitors,
    record_monitor_check,
    record_notification,
    update_monitor,
)
from .monitoring_export_service import (
    export_incidents_csv,
    export_monitor_latency_csv,
    export_monitoring_csv,
)


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Abre SQLite con el proveedor de ruta de esta fachada.

    El proveedor explícito mantiene compatibles las instalaciones y pruebas que
    sustituyen `database_path` sin obligar a los repositorios a importar esta fachada.
    """
    with _storage.connect(path, default_path_provider=database_path) as connection:
        yield connection


def initialize(path: Path | None = None) -> None:
    """Inicializa el esquema o aplica sus migraciones aditivas."""
    _storage.initialize(path, default_path_provider=database_path)


def export_sqlite_backup(path: Path | None = None) -> bytes:
    """Crea una copia SQLite consistente, conservando la firma pública histórica."""
    return _export_sqlite_backup(path, default_path_provider=database_path)
