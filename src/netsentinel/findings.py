"""Hallazgos normalizados a partir de evidencia local ya registrada.

Este módulo no descubre amenazas nuevas ni infiere identidades: presenta en un
contrato común los eventos del inventario y los incidentes de monitorización.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_ALLOWED_STATES = {"active", "acknowledged", "resolved", "all"}
_MAX_LIMIT = 200

_EVENT_TITLES = {
    "new_device": "Nuevo dispositivo observado",
    "ip_changed": "Cambio de dirección IP observado",
}

_EVENT_ACTIONS = {
    "new_device": (
        "Verificá si el dispositivo pertenece a un activo autorizado. "
        "El primer avistamiento por sí solo no demuestra una intrusión."
    ),
    "ip_changed": (
        "Comprobá DHCP, VPN, cambios de interfaz y reservas de direcciones. "
        "Un cambio de IP por sí solo no demuestra suplantación."
    ),
}

_EVENT_CONFIDENCE_NOTE = (
    "Evento registrado por el inventario local; no confirma la identidad del "
    "dispositivo ni la causa del cambio."
)
_INCIDENT_CONFIDENCE_NOTE = (
    "Una o más comprobaciones del monitor fallaron; esto no determina la causa "
    "raíz ni el impacto empresarial."
)


def _timestamp_key(value: Any) -> float:
    """Ordena marcas ISO-8601 y tolera datos históricos malformados."""
    if not isinstance(value, str) or not value:
        return 0.0
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (OverflowError, OSError, TypeError, ValueError):
        return 0.0


def _asset_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    device_id = event.get("device_id")
    if device_id is None:
        return None
    mac = event.get("mac_address")
    ip = event.get("ip_address")
    manufacturer = event.get("manufacturer")
    display_name = (event.get("display_name") or "").strip()
    label = display_name or manufacturer or mac or ip or f"Dispositivo {device_id}"
    return {
        "device_id": device_id,
        "label": label,
        "display_name": display_name or None,
        "manufacturer": manufacturer,
        "mac_address": mac,
        "ip_address": ip,
    }


def _event_finding(event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("event_type") or "unknown")
    acknowledged = bool(event.get("acknowledged"))
    created_at = event.get("created_at")
    severity = str(event.get("severity") or "unknown")
    message = str(event.get("message") or "El evento no contiene un detalle.")
    return {
        "id": f"event:{event.get('id', 'unknown')}",
        "category": "inventory",
        "title": _EVENT_TITLES.get(event_type, f"Evento de inventario: {event_type}"),
        "summary": message,
        "severity": severity,
        "severity_basis": "Clasificación del evento local; no equivale a impacto empresarial.",
        "status": "acknowledged" if acknowledged else "active",
        "first_seen_at": created_at,
        "updated_at": created_at,
        "source": {
            "system": "inventory",
            "record_type": "event",
            "record_id": event.get("id"),
        },
        "confidence": {
            "level": "observed",
            "explanation": _EVENT_CONFIDENCE_NOTE,
        },
        "asset": _asset_from_event(event),
        "evidence": {
            "event_type": event_type,
            "created_at": created_at,
            "event_severity": severity,
            "message": message,
            "acknowledged": acknowledged,
        },
        "recommended_action": _EVENT_ACTIONS.get(
            event_type,
            "Revisá el evento y contrastalo con una fuente independiente antes de actuar.",
        ),
        "limitations": [
            "El evento es una observación local, no una atribución de identidad.",
            "No se establece una causa raíz automáticamente.",
        ],
    }


def _incident_finding(incident: dict[str, Any]) -> dict[str, Any]:
    incident_id = incident.get("id", "unknown")
    status = "resolved" if incident.get("status") == "resolved" else "active"
    opened_at = incident.get("opened_at")
    updated_at = incident.get("updated_at") or opened_at
    monitor_name = str(incident.get("monitor_name") or "Monitor")
    target = incident.get("target")
    last_detail = str(incident.get("last_detail") or "Comprobación fallida.")
    return {
        "id": f"incident:{incident_id}",
        "category": "availability",
        "title": f"Incidente de disponibilidad: {monitor_name}",
        "summary": last_detail,
        "severity": "warning",
        "severity_basis": (
            "Prioridad orientativa de triaje por una comprobación fallida; "
            "no estima el impacto empresarial."
        ),
        "status": status,
        "first_seen_at": opened_at,
        "updated_at": updated_at,
        "source": {
            "system": "monitoring",
            "record_type": "incident",
            "record_id": incident.get("id"),
        },
        "confidence": {
            "level": "measured",
            "explanation": _INCIDENT_CONFIDENCE_NOTE,
        },
        "asset": {
            "monitor_id": incident.get("monitor_id"),
            "label": monitor_name,
            "kind": incident.get("kind"),
            "target": target,
        },
        "evidence": {
            "opened_at": opened_at,
            "updated_at": updated_at,
            "resolved_at": incident.get("resolved_at"),
            "failure_count": incident.get("failure_count"),
            "last_detail": last_detail,
            "monitor_kind": incident.get("kind"),
            "target": target,
        },
        "recommended_action": (
            "Confirmá la disponibilidad desde otro punto y revisá los registros "
            "del servicio. La comprobación no identifica por sí sola la causa raíz."
            if status == "active"
            else "La monitorización registró recuperación; validá que el servicio "
                 "funcione para sus usuarios antes de cerrar el seguimiento."
        ),
        "limitations": [
            "La evidencia corresponde al tipo de comprobación configurado.",
            "Una comprobación fallida no demuestra por sí sola una intrusión.",
        ],
    }


def build_findings(
    events: list[dict[str, Any]],
    incidents: list[dict[str, Any]],
    *,
    state: str = "active",
    limit: int = 100,
) -> dict[str, Any]:
    """Normaliza hallazgos de fuentes locales existentes, sin persistir ni correlacionar."""
    if state not in _ALLOWED_STATES:
        raise ValueError("El estado debe ser active, acknowledged, resolved o all.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= _MAX_LIMIT:
        raise ValueError(f"El límite debe estar entre 1 y {_MAX_LIMIT}.")

    findings: list[dict[str, Any]] = []
    for event in events:
        finding = _event_finding(event)
        if state == "all" or finding["status"] == state:
            findings.append(finding)
    for incident in incidents:
        finding = _incident_finding(incident)
        if state == "all" or finding["status"] == state:
            findings.append(finding)

    findings.sort(
        key=lambda item: (
            _timestamp_key(item.get("updated_at")),
            str(item.get("id") or ""),
        ),
        reverse=True,
    )
    findings = findings[:limit]

    returned_statuses = [item["status"] for item in findings]
    return {
        "format": "netsentinel-findings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "state": state,
        "limit": limit,
        "summary": {
            "returned": len(findings),
            "active": returned_statuses.count("active"),
            "acknowledged": returned_statuses.count("acknowledged"),
            "resolved": returned_statuses.count("resolved"),
        },
        "findings": findings,
        "notice": (
            "Vista compuesta de eventos del inventario e incidentes de monitorización "
            "que ya están almacenados localmente. No es un motor SIEM, no deduce "
            "identidades ni causas raíz y no incluye resultados puntuales DNS/TLS "
            "que no se hayan guardado. Las cantidades describen solo los registros "
            "devueltos por esta consulta."
        ),
    }
