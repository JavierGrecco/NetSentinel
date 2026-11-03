"""Casos de uso para reunir y contextualizar evidencia local.

El servicio coordina eventos, incidentes y actividad Zeek importada expresamente.
Las coincidencias se limitan por activo/IP y tiempo; no se interpretan como causalidad.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from . import database, findings_activity_repository
from .findings import build_findings

_DUPLICATE_MONITOR_EVENT_TYPES = ("monitor_down", "monitor_recovered")
_ALLOWED_STATES = frozenset({"active", "acknowledged", "resolved", "all"})
_CORRELATION_WINDOW_SECONDS = 300
_MAX_ACTIVITY_RECORDS_PER_CONTEXT = 5


def _utc_datetime(value: Any) -> datetime | None:
    """Interpreta una marca ISO-8601; los valores sin zona se tratan como UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (OverflowError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _utc_text(value: datetime) -> str:
    """Serializa una marca de tiempo UTC para consultas SQLite acotadas."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _monitor_target_ip(value: Any) -> str | None:
    """Devuelve solo una IP literal, sin resolver nombres ni adivinar direcciones."""
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    candidate: str | None = None
    if "://" in raw:
        try:
            candidate = urlsplit(raw).hostname
        except ValueError:
            return None
    else:
        candidate = raw
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            pass
        if raw.startswith("[") and "]" in raw:
            candidate = raw[1:raw.index("]")]
        elif raw.count(":") == 1:
            host, port = raw.rsplit(":", 1)
            candidate = host if port.isdigit() else raw
        else:
            candidate = raw
    try:
        return str(ipaddress.ip_address(candidate))
    except (TypeError, ValueError):
        return None


def _add_context(
    contexts: list[dict[str, Any]],
    *,
    finding_id: str,
    context_name: str,
    anchor_value: Any,
    device_id: Any = None,
    target_ip: str | None = None,
    relation: str,
) -> None:
    """Agrega una ventana temporal pequeña solo cuando la identidad es usable."""
    anchor = _utc_datetime(anchor_value)
    normalized_device_id = (
        device_id
        if isinstance(device_id, int) and not isinstance(device_id, bool) and device_id > 0
        else None
    )
    if anchor is None or (normalized_device_id is None and target_ip is None):
        return
    window = timedelta(seconds=_CORRELATION_WINDOW_SECONDS)
    contexts.append({
        "context_id": f"{finding_id}:{context_name}",
        "finding_id": finding_id,
        "device_id": normalized_device_id,
        "target_ip": target_ip,
        "anchor_at": _utc_text(anchor),
        "start_at": _utc_text(anchor - window),
        "end_at": _utc_text(anchor + window),
        "relation": relation,
    })


def _attach_related_activity(
    report: dict[str, Any],
    source_events: list[dict[str, Any]],
    source_incidents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Añade contexto Zeek opcional sin alterar el registro de origen."""
    findings = report.get("findings")
    # Mantiene compatibilidad con implementaciones de prueba de este coordinador
    # que sustituyen build_findings por un objeto simplificado.
    if not isinstance(findings, list):
        return report

    events_by_id = {str(event.get("id")): event for event in source_events}
    incidents_by_id = {str(incident.get("id")): incident for incident in source_incidents}
    contexts: list[dict[str, Any]] = []
    contexts_by_finding: dict[str, list[dict[str, Any]]] = {}

    for finding in findings:
        finding_id = str(finding.get("id") or "")
        source = finding.get("source") or {}
        record_id = source.get("record_id")
        candidates: list[dict[str, Any]] = []
        if source.get("system") == "inventory":
            event = events_by_id.get(str(record_id))
            if event:
                before_count = len(contexts)
                _add_context(
                    contexts,
                    finding_id=finding_id,
                    context_name="asset",
                    anchor_value=event.get("created_at"),
                    device_id=event.get("device_id"),
                    relation="same_device_near_inventory_event",
                )
                candidates = contexts[before_count:]
        elif source.get("system") == "monitoring":
            incident = incidents_by_id.get(str(record_id))
            target_ip = _monitor_target_ip(incident.get("target")) if incident else None
            if incident and target_ip:
                before_count = len(contexts)
                _add_context(
                    contexts,
                    finding_id=finding_id,
                    context_name="opened",
                    anchor_value=incident.get("opened_at"),
                    target_ip=target_ip,
                    relation="exact_monitor_target_ip_near_opened_at",
                )
                _add_context(
                    contexts,
                    finding_id=finding_id,
                    context_name="updated",
                    anchor_value=incident.get("updated_at") or incident.get("resolved_at"),
                    target_ip=target_ip,
                    relation="exact_monitor_target_ip_near_updated_at",
                )
                candidates = contexts[before_count:]
        contexts_by_finding[finding_id] = candidates

    rows = findings_activity_repository.get_zeek_activity_contexts(
        contexts,
        per_context_limit=_MAX_ACTIVITY_RECORDS_PER_CONTEXT,
    )
    rows_by_context: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_context.setdefault(str(row.get("context_id")), []).append(row)

    note = (
        "Una coincidencia temporal/contextual no demuestra una intrusión, una causa raíz "
        "ni que el evento de inventario haya generado esa conexión. Solo se consultan "
        "registros Zeek conn.log importados explícitamente que siguen dentro de la retención."
    )
    for finding in findings:
        finding_id = str(finding.get("id") or "")
        item_contexts = contexts_by_finding.get(finding_id, [])
        best_by_activity_id: dict[int, dict[str, Any]] = {}
        for context in item_contexts:
            for match in rows_by_context.get(context["context_id"], []):
                activity_id = match.get("activity_id")
                if not isinstance(activity_id, int):
                    continue
                candidate = dict(match)
                existing = best_by_activity_id.get(activity_id)
                if existing is None or float(candidate.get("time_delta_seconds") or 0) < float(
                    existing.get("time_delta_seconds") or 0
                ):
                    candidate["correlation_reason"] = (
                        "Mismo activo del inventario y una hora de observación dentro de "
                        "cinco minutos del evento."
                        if context["relation"] == "same_device_near_inventory_event"
                        else "La IP literal del objetivo del monitor aparece como origen o "
                             "destino dentro de cinco minutos de una marca del incidente."
                    )
                    best_by_activity_id[activity_id] = candidate

        matched = sorted(
            best_by_activity_id.values(),
            key=lambda item: (
                float(item.get("time_delta_seconds") or 0),
                str(item.get("observed_at") or ""),
                int(item.get("activity_id") or 0),
            ),
        )[:_MAX_ACTIVITY_RECORDS_PER_CONTEXT]
        records = []
        for match in matched:
            records.append({
                "activity_id": match.get("activity_id"),
                "source_event_id": match.get("source_event_id"),
                "device_id": match.get("device_id"),
                "device_name": match.get("device_name"),
                "device_ip": match.get("device_ip"),
                "observed_at": match.get("observed_at"),
                "received_at": match.get("received_at"),
                "source_ip": match.get("source_ip"),
                "source_port": match.get("source_port"),
                "destination_ip": match.get("destination_ip"),
                "destination_port": match.get("destination_port"),
                "protocol": match.get("protocol"),
                "bytes_sent": match.get("bytes_sent"),
                "bytes_received": match.get("bytes_received"),
                "packets_sent": match.get("packets_sent"),
                "packets_received": match.get("packets_received"),
                "time_delta_seconds": int(round(float(match.get("time_delta_seconds") or 0))),
                "correlation_reason": match.get("correlation_reason"),
            })

        if records:
            status = "matched"
            message = f"Se encontraron {len(records)} conexión(es) importada(s) cerca del momento investigado."
        elif item_contexts:
            status = "no_match_in_window"
            message = (
                "No se encontraron registros Zeek importados para este activo/objetivo dentro "
                "de la ventana temporal de cinco minutos. Esto no demuestra que no hubiera actividad."
            )
        else:
            status = "not_available"
            source = finding.get("source") or {}
            if source.get("system") == "monitoring":
                message = (
                    "No se buscó actividad por nombre de host: para evitar resolver o atribuir "
                    "direcciones sin evidencia, esta primera versión solo correlaciona objetivos "
                    "configurados como IP literal."
                )
            else:
                message = (
                    "No hay un activo ni una marca de tiempo válidos para construir una búsqueda "
                    "temporal segura."
                )
        finding["related_activity"] = {
            "status": status,
            "source": "Zeek conn.log importado manualmente",
            "window_seconds": _CORRELATION_WINDOW_SECONDS,
            "records": records,
            "message": message,
            "notice": note,
        }

    report["correlation"] = {
        "method": "Zeek conn.log importado manualmente",
        "window_seconds": _CORRELATION_WINDOW_SECONDS,
        "max_records_per_finding": _MAX_ACTIVITY_RECORDS_PER_CONTEXT,
        "notice": note,
    }
    return report


def collect_findings_report(state: str, limit: int) -> dict:
    """Crea un informe de evidencia local y adjunta coincidencias temporales acotadas."""
    if state not in _ALLOWED_STATES:
        raise ValueError("El estado debe ser active, acknowledged, resolved o all.")

    if state == "active":
        source_events = database.get_events(
            limit=limit,
            acknowledged=False,
            exclude_event_types=_DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = database.get_incidents(limit=limit, status="open")
    elif state == "acknowledged":
        source_events = database.get_events(
            limit=limit,
            acknowledged=True,
            exclude_event_types=_DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = []
    elif state == "resolved":
        source_events = []
        source_incidents = database.get_incidents(limit=limit, status="resolved")
    else:
        source_events = database.get_events(
            limit=limit,
            exclude_event_types=_DUPLICATE_MONITOR_EVENT_TYPES,
        )
        source_incidents = database.get_incidents(limit=limit)

    report = build_findings(source_events, source_incidents, state=state, limit=limit)
    return _attach_related_activity(report, source_events, source_incidents)
