"""Caso de uso para previsualizar y borrar actividad con alcance confirmado.

El servicio mantiene las reglas de negocio fuera de la fachada compatible y no
depende de FastAPI ni abre conexiones SQLite directamente.
"""
from __future__ import annotations

from typing import Any

from . import activity_filters, activity_repository


def _scope(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None,
) -> tuple[str, tuple[Any, ...]]:
    """Construye el alcance permitido antes de consultar o borrar eventos."""
    return activity_filters.activity_delete_scope(
        device_id, event_type, from_date, to_date, source
    )


def preview_delete_activity(
    device_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Cuenta eventos dentro del alcance sin escribir ni ejecutar limpieza."""
    where_sql, params = _scope(device_id, event_type, from_date, to_date, source)
    count = activity_repository.count_activity_scope(
        where_sql, params, device_id=device_id
    )
    return {
        "device_id": device_id,
        "event_type": event_type or None,
        "from_date": from_date or None,
        "to_date": to_date or None,
        "source": source or None,
        "matching_events": count,
        "confirmation_required": f"BORRAR {count}",
        "deleted": False,
        "note": "Vista previa únicamente: no se borró ningún evento.",
    }


def delete_activity(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    confirmation: str,
    source: str | None = None,
) -> dict[str, Any]:
    """Borra solo el alcance explícito si la confirmación coincide con el recuento."""
    where_sql, params = _scope(device_id, event_type, from_date, to_date, source)
    if not isinstance(confirmation, str) or len(confirmation) > 40:
        raise PermissionError("La frase de confirmación no es válida.")

    deleted = activity_repository.delete_activity_scope(
        where_sql, params, device_id=device_id, confirmation=confirmation
    )
    return {
        "deleted_events": deleted,
        "device_id": device_id,
        "event_type": event_type or None,
        "from_date": from_date or None,
        "to_date": to_date or None,
        "source": source or None,
        "note": "Se borraron únicamente los eventos que coincidían con el alcance confirmado.",
    }
