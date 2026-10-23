"""Consultas de actividad y formato de exportación, sin rutas HTTP.

La validación de filtros es pura; el repositorio ejecuta las consultas SQLite. Este
servicio compone el resultado que consume el panel y genera el CSV formula-seguro.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from . import activity_filters, activity_repository
from .activity_catalog import EVENT_SOURCES, EVENT_TYPES, SESSION_SOURCES
from .csv_safety import spreadsheet_safe_text as _csv_safe_text


_ACTIVITY_NOTE = (
    "La aplicación no captura tráfico por sí misma. El correo solo se incorpora como metadatos importados "
    "de registros autorizados, sin cuerpos ni adjuntos. Las sesiones habilitan una ventana para que un adaptador "
    "autorizado envíe metadatos; la importación CSV añade registros históricos. No se guardan credenciales, "
    "cookies ni cargas útiles. Las URLs de navegación se normalizan: se quitan fragmentos y parámetros "
    "conocidos sensibles, y se redactan algunos identificadores reconocibles en la ruta; otros segmentos o "
    "parámetros no reconocidos pueden persistir. DNS/SNI/conexiones son indicios de tráfico, no prueba de "
    "que una persona haya usado una cuenta o visto una página concreta."
)


def _normalized_device_id(device_id: int | None) -> int | None:
    """Valida el identificador antes de construir consultas para un dispositivo."""
    if device_id is None:
        return None
    normalized = int(device_id)
    if normalized < 1:
        raise ValueError("device_id debe ser un entero positivo.")
    return normalized


def _normalized_source_event_id(value: str | None) -> str | None:
    """Valida un ID de origen usado como foco de lectura, sin interpretarlo como SQL."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError("source_event_id debe ser texto.")
    normalized = value.strip()
    if (
        not normalized
        or len(normalized) > 180
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
    ):
        raise ValueError("source_event_id está vacío, supera el límite o contiene caracteres de control.")
    return normalized


def _build_event_filter(
    device_id: int | None,
    event_type: str | None,
    from_date: str | None,
    to_date: str | None,
    source: str | None,
    source_event_id: str | None = None,
) -> tuple[str, tuple[Any, ...]]:
    """Construye solo predicados conocidos; los valores siempre van como parámetros."""
    clauses, params = activity_filters.activity_filter_values(
        event_type, from_date, to_date, source
    )
    if device_id is not None:
        clauses.insert(0, "e.device_id = ?")
        params.insert(0, device_id)
    normalized_source_event_id = _normalized_source_event_id(source_event_id)
    if normalized_source_event_id is not None:
        clauses.append("e.source_event_id = ?")
        params.append(normalized_source_event_id)
    where_sql = "WHERE " + " AND ".join(clauses) if clauses else ""
    return where_sql, tuple(params)


def export_activity_csv(
    device_id: int | None = None,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 10000,
    source: str | None = None,
    source_event_id: str | None = None,
) -> str:
    """Exporta hasta 10.000 filas filtradas como CSV seguro para hojas de cálculo."""
    normalized_device = _normalized_device_id(device_id)
    where_sql, filter_params = _build_event_filter(
        normalized_device, event_type, from_date, to_date, source, source_event_id
    )
    events = activity_repository.get_activity_export_rows(
        where_sql=where_sql,
        params=filter_params,
        device_id=normalized_device,
        limit=max(1, min(int(limit), 10000)),
    )

    buffer = io.StringIO(newline="")
    fields = [
        "observed_at", "event_type", "device_id", "device_name", "ip_address", "source",
        "domain", "page_url", "search_engine", "search_terms", "source_ip",
        "source_port", "destination_ip", "destination_port", "protocol",
        "bytes_sent", "bytes_received", "packets_sent", "packets_received",
        "network_interface", "source_event_id", "app_name", "blocked", "email_provider",
        "email_from", "email_to", "email_subject",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for event in events:
        row = {
            "observed_at": event["observed_at"],
            "event_type": event["event_type"],
            "device_id": event["device_id"],
            "device_name": event["display_name"],
            "ip_address": event["ip_address"],
            "source": event["source"],
            "domain": event["domain"],
            "page_url": event["page_url"],
            "search_engine": event["search_engine"],
            "search_terms": event["search_terms"],
            "source_ip": event.get("source_ip"),
            "source_port": event.get("source_port"),
            "destination_ip": event["destination_ip"],
            "destination_port": event["destination_port"],
            "protocol": event["protocol"],
            "bytes_sent": event.get("bytes_sent"),
            "bytes_received": event.get("bytes_received"),
            "packets_sent": event.get("packets_sent"),
            "packets_received": event.get("packets_received"),
            "network_interface": event.get("network_interface"),
            "source_event_id": event.get("source_event_id"),
            "app_name": event["app_name"],
            "blocked": event["blocked"],
            "email_provider": event["email_provider"],
            "email_from": event["email_from"],
            "email_to": event["email_to"],
            "email_subject": event["email_subject"],
        }
        writer.writerow({key: _csv_safe_text(value) for key, value in row.items()})
    return "\ufeff" + buffer.getvalue()


def get_activity(
    device_id: int | None = None,
    limit: int = 100,
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str | None = None,
    source_event_id: str | None = None,
) -> dict[str, Any]:
    """Prepara el modelo de lectura; los filtros afectan a la lista de eventos."""
    normalized_device = _normalized_device_id(device_id)
    normalized_source_event_id = _normalized_source_event_id(source_event_id)
    event_filter, event_params = _build_event_filter(
        normalized_device, event_type, from_date, to_date, source, normalized_source_event_id
    )
    snapshot = activity_repository.get_activity_snapshot(
        device_id=normalized_device,
        event_filter=event_filter,
        event_params=event_params,
        limit=max(1, min(int(limit), 500)),
    )
    return {
        **snapshot,
        "sources": sorted(SESSION_SOURCES),
        "activity_sources": sorted(EVENT_SOURCES | {"manual_import"}),
        "event_types": sorted(EVENT_TYPES),
        "focus_event_id": normalized_source_event_id,
        "note": _ACTIVITY_NOTE,
    }
