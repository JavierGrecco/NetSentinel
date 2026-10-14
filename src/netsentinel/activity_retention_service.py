"""Política de retención y utilidades temporales compartidas para actividad.

Centraliza la normalización UTC, el vencimiento y la actualización de retención.
La persistencia transaccional sigue perteneciendo a activity_repository.
"""
from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Any

from . import activity_repository, database


MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 90


def now() -> datetime:
    """Obtiene la hora actual como datetime consciente de UTC."""
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    """Normaliza fechas conscientes o ingenuas a UTC sin depender de la zona local."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def cleanup(db: sqlite3.Connection) -> int:
    """Aplica la política de retención usando una conexión/transacción existente."""
    return activity_repository.cleanup(db, now=now())


def _validated_days(retention_days: Any) -> int:
    """Valida el rango sin aceptar booleanos ni truncar valores fraccionarios."""
    if isinstance(retention_days, bool):
        raise ValueError("La retención debe ser de 1 a 90 días.")
    try:
        days = int(retention_days)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("La retención debe ser de 1 a 90 días.") from exc
    if not isinstance(retention_days, str) and retention_days != days:
        raise ValueError("La retención debe ser de 1 a 90 días.")
    if not MIN_RETENTION_DAYS <= days <= MAX_RETENTION_DAYS:
        raise ValueError("La retención debe ser de 1 a 90 días.")
    return days


def update_retention(retention_days: int) -> dict[str, int]:
    """Actualiza la política y aplica la nueva retención mediante el repositorio."""
    days = _validated_days(retention_days)
    return activity_repository.update_retention(days, now=now())
