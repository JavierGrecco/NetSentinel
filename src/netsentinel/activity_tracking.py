"""Seguimiento de actividad basado en metadatos explícitos y fuentes autorizadas.

Este módulo no captura paquetes por sí mismo ni lee contenido HTTPS, credenciales,
cookies o cuerpos HTTP. Las URLs de navegación se guardan normalizadas, no como
la URL original: se eliminan fragmentos y parámetros conocidos sensibles y se
redactan algunos identificadores reconocibles en la ruta. Otros segmentos o
parámetros desconocidos pueden persistir. Las fuentes compatibles envían metadatos
durante una sesión opt-in o mediante importación explícita.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from . import activity_deletion_service, activity_event_service, activity_filters, activity_import_service, activity_read_service, activity_retention_service, activity_session_service, activity_zeek_import_service
from .activity_catalog import EVENT_SOURCES, EVENT_TYPES, PROTOCOLS, SESSION_SOURCES
from .activity_session_service import InvalidCollectorToken
from .activity_privacy import _domain, _email_address_list, _safe_page_url



def _now() -> datetime:
    """Mantiene el helper histórico y delega el reloj UTC compartido."""
    return activity_retention_service.now()


def _iso(value: datetime) -> str:
    """Mantiene el helper histórico y delega la normalización UTC."""
    return activity_retention_service.iso(value)


def _parse_timestamp(value: str | None) -> str:
    """Mantiene el helper histórico y delega la validación de fechas."""
    return activity_event_service._parse_timestamp(value)


def normalize_event(
    payload: dict[str, Any], *, source_override: str | None = None
) -> dict[str, Any]:
    """Mantiene la firma pública y delega la normalización al servicio de eventos."""
    return activity_event_service.normalize_event(
        payload, source_override=source_override
    )

def _cleanup(db) -> int:
    """Mantiene el helper histórico y delega la política de retención."""
    return activity_retention_service.cleanup(db)


def start_session(
    device_id: int, duration_minutes: int, source_mode: str
) -> dict[str, Any]:
    """Mantiene la API histórica y delega la apertura de sesión."""
    return activity_session_service.start_session(
        device_id, duration_minutes, source_mode
    )


def stop_session(session_id: int) -> dict[str, Any] | None:
    """Mantiene la API histórica y delega el cierre de sesión."""
    return activity_session_service.stop_session(session_id)


def ingest_event(
    session_id: int, device_id: int, collector_token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Mantiene la API histórica y delega la ingesta validada."""
    return activity_session_service.ingest_event(
        session_id, device_id, collector_token, payload
    )

def import_csv(device_id: int, csv_data: str, *, preview: bool = False) -> dict[str, Any]:
    """Delega la validación CSV al servicio y conserva la firma pública actual."""
    return activity_import_service.import_csv(
        device_id,
        csv_data,
        preview=preview,
        normalize_event=normalize_event,
    )


def preview_csv(device_id: int, csv_data: str) -> dict[str, Any]:
    """Valida y muestra una vista previa de CSV sin almacenar los eventos."""
    return import_csv(device_id, csv_data, preview=True)


def import_zeek_log(
    device_id: int, log_data: str, *, preview: bool = False
) -> dict[str, Any]:
    """Delega la importación de Zeek JSON Lines o TSV al adaptador especializado."""
    return activity_zeek_import_service.import_log(
        device_id,
        log_data,
        normalize_event=normalize_event,
        preview=preview,
    )


def preview_zeek_log(device_id: int, log_data: str) -> dict[str, Any]:
    """Valida una exportación Zeek sin guardar datos."""
    return import_zeek_log(device_id, log_data, preview=True)


def update_retention(retention_days: int) -> dict[str, Any]:
    """Conserva la firma pública y delega la política de retención."""
    return activity_retention_service.update_retention(retention_days)


def _activity_filter_values(
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[list[str], list[Any]]:
    """Mantiene el punto de entrada histórico y delega la validación pura."""
    return activity_filters.activity_filter_values(event_type, from_date, to_date, source)

def _activity_delete_scope(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Mantiene el punto de entrada histórico para construir un alcance seguro."""
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
    """Conserva la API histórica y delega la vista previa al servicio de borrado."""
    return activity_deletion_service.preview_delete_activity(
        device_id=device_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        source=source,
    )


def delete_activity(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    confirmation: str,
    source: str | None = None,
) -> dict[str, Any]:
    """Conserva la firma pública y delega el borrado con confirmación exacta."""
    return activity_deletion_service.delete_activity(
        device_id=device_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        confirmation=confirmation,
        source=source,
    )


def export_activity_csv(
    device_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 10000,
    source: str | None = None,
) -> str:
    """Conserva la API pública y delega la consulta y el formato del CSV."""
    return activity_read_service.export_activity_csv(
        device_id=device_id,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        source=source,
    )

def get_activity(
    device_id: int | None = None,
    limit: int = 100,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
) -> dict[str, Any]:
    """Conserva el contrato que consume la API y delega el modelo de lectura."""
    return activity_read_service.get_activity(
        device_id=device_id,
        limit=limit,
        event_type=event_type,
        from_date=from_date,
        to_date=to_date,
        source=source,
    )
