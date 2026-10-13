"""Casos de uso para reunir y preparar hallazgos a partir de evidencia local.

El servicio coordina consultas del inventario y de los incidentes y delega la
presentación al módulo puro findings. No conoce FastAPI ni respuestas HTTP.
"""
from __future__ import annotations

from . import database
from .findings import build_findings

DUPLICATE_MONITOR_EVENT_TYPES = ("monitor_down", "monitor_recovered")
ALLOWED_STATES = {"active", "acknowledged", "resolved", "all"}


def collect_findings_report(state: str, limit: int) -> dict:
    """Crea un informe desde la evidencia ya almacenada para el estado solicitado."""
    if state not in ALLOWED_STATES:
        raise ValueError("El estado debe ser active, acknowledged, resolved o all.")

    if state == "active":
        source_events = database.get_events(
            limit=limit,
            acknowledged=False,
            exclude_event_types=DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = database.get_incidents(limit=limit, status="open")
    elif state == "acknowledged":
        source_events = database.get_events(
            limit=limit,
            acknowledged=True,
            exclude_event_types=DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = []
    elif state == "resolved":
        source_events = []
        source_incidents = database.get_incidents(limit=limit, status="resolved")
    else:
        source_events = database.get_events(
            limit=limit,
            exclude_event_types=DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = database.get_incidents(limit=limit)

    return build_findings(source_events, source_incidents, state=state, limit=limit)
