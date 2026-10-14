"""Comprobaciones comunes para los repositorios de actividad.

Este módulo concentra validaciones pequeñas que deben comportarse igual en todas
las operaciones de persistencia. No contiene reglas HTTP ni coordina casos de uso.
"""
from __future__ import annotations

import sqlite3

from . import database


def _require_device(db: sqlite3.Connection, device_id: int | None) -> None:
    """Valida la existencia del dispositivo cuando el alcance está acotado por ID."""
    if device_id is not None and db.execute(
        "SELECT 1 FROM devices WHERE id = ?", (device_id,)
    ).fetchone() is None:
        raise LookupError("No se encontró el dispositivo.")


def require_device_exists(device_id: int) -> None:
    """Comprueba que el dispositivo existe antes de procesar un archivo importado."""
    with database.connect() as db:
        _require_device(db, device_id)
