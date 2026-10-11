"""Configuración del almacenamiento local de NetSentinel."""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    """Devuelve el directorio de datos, permitiendo sobrescribirlo para pruebas."""
    override = os.environ.get("NETSENTINEL_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".netsentinel").resolve()


def database_path() -> Path:
    return data_dir() / "netsentinel.sqlite3"
