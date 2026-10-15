"""Formato de las exportaciones de monitorización.

Las consultas y las reglas de estado siguen en monitoring_repository.py. Este módulo
solo presenta esos resultados en CSV y neutraliza celdas peligrosas para hojas de cálculo.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from .csv_safety import spreadsheet_safe_text
from .monitoring_repository import (
    get_incidents,
    get_monitor_analytics,
    get_monitor_latency_trend,
)


def export_incidents_csv(status: str | None = None, path: Path | None = None, limit: int = 5000) -> str:
    """Exporta incidentes con duración estimada y protección contra fórmulas CSV."""
    if status not in {None, "open", "resolved"}:
        raise ValueError("El estado debe ser open o resolved.")
    incidents = get_incidents(path=path, limit=limit, status=status)
    buffer = io.StringIO(newline="")
    fields = [
        "id_incidente", "monitor", "tipo", "objetivo", "estado", "detectado_utc",
        "recuperado_utc", "duracion_estimada_segundos", "tiempo_recuperacion_segundos",
        "cantidad_fallos", "detalle_final", "base_duracion",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for incident in incidents:
        row = {
            "id_incidente": incident["id"],
            "monitor": incident["monitor_name"],
            "tipo": incident["kind"],
            "objetivo": incident["target"],
            "estado": "abierto" if incident["status"] == "open" else "resuelto",
            "detectado_utc": incident["opened_at"],
            "recuperado_utc": incident.get("resolved_at") or "",
            "duracion_estimada_segundos": incident.get("duration_seconds"),
            "tiempo_recuperacion_segundos": incident.get("time_to_recovery_seconds")
                if incident.get("time_to_recovery_seconds") is not None else "",
            "cantidad_fallos": incident["failure_count"],
            "detalle_final": incident["last_detail"],
            "base_duracion": incident.get("duration_basis", ""),
        }
        writer.writerow({key: spreadsheet_safe_text(value) for key, value in row.items()})
    return "\ufeff" + buffer.getvalue()


def export_monitor_latency_csv(monitor_id: int, window_hours: int = 24,
                               path: Path | None = None) -> str | None:
    """Exporta métricas de latencia agrupadas por hora o por bloques de seis horas."""
    report = get_monitor_latency_trend(monitor_id, window_hours=window_hours, path=path)
    if report is None:
        return None
    buffer = io.StringIO(newline="")
    fields = [
        "monitor_id", "monitor", "tipo", "objetivo", "periodo_horas", "bucket_minutos",
        "inicio_bucket_utc", "comprobaciones", "correctas", "fallidas",
        "latencia_media_ms", "latencia_minima_ms", "latencia_maxima_ms",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    for point in report["points"]:
        row = {
            "monitor_id": report["monitor"]["id"],
            "monitor": report["monitor"]["name"], "tipo": report["monitor"]["kind"],
            "objetivo": report["monitor"]["target"], "periodo_horas": report["window_hours"],
            "bucket_minutos": report["bucket_minutes"], "inicio_bucket_utc": point["bucket_start"],
            "comprobaciones": point["checks_total"], "correctas": point["checks_up"],
            "fallidas": point["checks_down"],
            "latencia_media_ms": point["average_latency_ms"] if point["average_latency_ms"] is not None else "",
            "latencia_minima_ms": point["min_latency_ms"] if point["min_latency_ms"] is not None else "",
            "latencia_maxima_ms": point["max_latency_ms"] if point["max_latency_ms"] is not None else "",
        }
        writer.writerow({key: spreadsheet_safe_text(value) for key, value in row.items()})
    return "\ufeff" + buffer.getvalue()


def export_monitoring_csv(window_hours: int = 24, path: Path | None = None) -> str:
    """Exporta el resumen de monitorización por período en CSV seguro para hojas de cálculo."""
    report = get_monitor_analytics(window_hours=window_hours, path=path)
    buffer = io.StringIO(newline="")
    fields = [
        "periodo_horas", "desde_utc", "id_monitor", "nombre", "tipo", "objetivo",
        "habilitado", "ultimo_estado", "ultima_comprobacion_utc", "incidente_abierto",
        "comprobaciones", "correctas", "fallidas", "tasa_exito_pct",
        "latencia_media_ms", "latencia_minima_ms", "latencia_maxima_ms",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for monitor in report["monitors"]:
        row = {
            "periodo_horas": report["window_hours"],
            "desde_utc": report["since"],
            "id_monitor": monitor["monitor_id"],
            "nombre": monitor["name"],
            "tipo": monitor["kind"],
            "objetivo": monitor["target"],
            "habilitado": "sí" if monitor["enabled"] else "no",
            "ultimo_estado": monitor["last_status"] or "sin_comprobar",
            "ultima_comprobacion_utc": monitor["last_checked_at"] or "",
            "incidente_abierto": "sí" if monitor["incident_open"] else "no",
            "comprobaciones": monitor["checks_total"],
            "correctas": monitor["checks_up"],
            "fallidas": monitor["checks_down"],
            "tasa_exito_pct": monitor["success_rate_percent"] if monitor["success_rate_percent"] is not None else "",
            "latencia_media_ms": monitor["average_latency_ms"] if monitor["average_latency_ms"] is not None else "",
            "latencia_minima_ms": monitor["min_latency_ms"] if monitor["min_latency_ms"] is not None else "",
            "latencia_maxima_ms": monitor["max_latency_ms"] if monitor["max_latency_ms"] is not None else "",
        }
        writer.writerow({key: spreadsheet_safe_text(value) for key, value in row.items()})
    return "\ufeff" + buffer.getvalue()
