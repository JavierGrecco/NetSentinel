"""Validación pura de filtros para consultar y borrar metadatos de actividad."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .activity_catalog import EVENT_SOURCES, EVENT_TYPES


def activity_filter_values(
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[list[str], list[Any]]:
    """Valida filtros y devuelve cláusulas SQL fijas con valores separados."""
    clauses: list[str] = []
    params: list[Any] = []
    if event_type not in (None, ""):
        normalized_type = str(event_type).strip().lower()
        if normalized_type not in EVENT_TYPES:
            raise ValueError("El tipo de evento no es válido.")
        clauses.append("event_type = ?")
        params.append(normalized_type)

    if source not in (None, ""):
        normalized_source = str(source).strip().lower()
        if normalized_source not in EVENT_SOURCES and normalized_source != "manual_import":
            raise ValueError("La fuente de actividad no es válida.")
        clauses.append("source = ?")
        params.append(normalized_source)

    parsed_from: datetime | None = None
    parsed_to: datetime | None = None
    for raw, name in ((from_date, "from_date"), (to_date, "to_date")):
        if raw in (None, ""):
            continue
        try:
            parsed = datetime.strptime(str(raw), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} debe tener formato AAAA-MM-DD.") from exc
        if name == "from_date":
            parsed_from = parsed
        else:
            parsed_to = parsed

    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")
    if parsed_from:
        clauses.append("observed_at >= ?")
        params.append(parsed_from.isoformat(timespec="seconds"))
    if parsed_to:
        clauses.append("observed_at < ?")
        params.append((parsed_to + timedelta(days=1)).isoformat(timespec="seconds"))
    return clauses, params


def activity_delete_scope(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Construye un alcance de borrado acotado; nunca permite una operación global vacía."""
    if (
        device_id is None
        and event_type in (None, "")
        and from_date in (None, "")
        and to_date in (None, "")
        and source in (None, "")
    ):
        raise ValueError("Elegí al menos un alcance: dispositivo, tipo de evento, fuente o fechas.")
    clauses, params = activity_filter_values(event_type, from_date, to_date, source)
    if device_id is not None:
        if int(device_id) < 1:
            raise ValueError("device_id debe ser un entero positivo.")
        clauses.insert(0, "device_id = ?")
        params.insert(0, int(device_id))
    return " WHERE " + " AND ".join(clauses), tuple(params)
