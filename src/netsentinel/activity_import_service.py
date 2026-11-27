"""Importación CSV de actividad, separada de la API y de las consultas SQL.

Este servicio convierte archivos autorizados en eventos validados. La lectura de
cabeceras, los alias de proveedores, los límites y la vista previa viven aquí;
las transacciones, la retención y la deduplicación se delegan al repositorio.
No importa FastAPI ni administra conexiones SQLite directamente.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Callable

from . import activity_repository
from .semantics.catalog import FIELD_DEFINITIONS
from .semantics.models import HeaderStatus
from .semantics.resolver import missing_required_fields, normalize_header, resolve_headers

EventNormalizer = Callable[..., dict[str, Any]]

CSV_FIELDS = set(FIELD_DEFINITIONS)
CSV_PREVIEW_FIELDS = (
    "observed_at", "event_type", "domain", "source_ip", "source_port",
    "destination_ip", "destination_port", "protocol", "bytes_sent", "bytes_received",
    "packets_sent", "packets_received", "network_interface", "source_event_id",
    "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)
def _normalized_csv_header(value: str | None) -> str:
    """Conserva el helper histórico usando la normalización semántica compartida."""
    normalized, reason = normalize_header(value)
    return normalized or ""


def _is_sensitive_csv_header(value: str | None) -> bool:
    """Identifica encabezados sensibles mediante el perfil CSV central."""
    result = resolve_headers(
        [value],
        "activity_csv",
        suggest_typos=False,
    ).headers[0]
    return result.status is HeaderStatus.BLOCKED


def _canonical_csv_header(value: str | None) -> str | None:
    """Compatibilidad para llamadas existentes; los typos nunca se asignan."""
    result = resolve_headers(
        [value],
        "activity_csv",
        suggest_typos=False,
    ).headers[0]
    if result.usable:
        return result.field_name
    if result.status in {HeaderStatus.IGNORED, HeaderStatus.BLOCKED}:
        return None
    return result.normalized_header


def _now() -> datetime:
    """Devuelve la hora UTC usada para fijar la transacción de importación."""
    return datetime.now(timezone.utc)

def import_csv(
    device_id: int,
    csv_data: str,
    *,
    normalize_event: EventNormalizer,
    preview: bool = False,
) -> dict[str, Any]:
    """Valida un CSV y, salvo en vista previa, importa hasta 1000 filas normalizadas."""
    if len(csv_data.encode("utf-8")) > 1_000_000:
        raise ValueError("El archivo CSV supera el máximo de 1 MB.")
    reader = csv.DictReader(io.StringIO(csv_data))
    try:
        # Leer fieldnames también puede generar csv.Error si una cabecera supera
        # el límite de tamaño definido por el analizador de la biblioteca estándar.
        raw_headers = list(reader.fieldnames or [])
    except csv.Error as exc:
        raise ValueError("El CSV contiene una cabecera inválida o demasiado grande.") from exc
    if not raw_headers:
        raise ValueError("El CSV está vacío o no contiene cabeceras.")
    header_plan = resolve_headers(raw_headers, "activity_csv")
    blocked = [
        result.source_header
        for result in header_plan.headers
        if result.status is HeaderStatus.BLOCKED
    ]
    if blocked:
        raise ValueError(
            "El CSV incluye campos que no se importan por privacidad: "
            + ", ".join(sorted(str(name) for name in blocked)) + "."
        )

    unsafe = [
        result for result in header_plan.headers
        if result.status is HeaderStatus.UNSAFE_NAME
    ]
    if unsafe:
        details = "; ".join(
            f"{result.source_header!r}: {result.reason}"
            for result in unsafe
        )
        raise ValueError("El CSV contiene nombres de columna no seguros: " + details)

    if header_plan.collisions:
        raise ValueError("El CSV repite una cabecera tras normalizar los nombres de columna.")

    unresolved = [
        result for result in header_plan.headers
        if result.status in {
            HeaderStatus.UNKNOWN, HeaderStatus.SUGGESTION, HeaderStatus.AMBIGUOUS,
        }
    ]
    if unresolved:
        descriptions = []
        for result in unresolved:
            if result.suggestions:
                candidates = ", ".join(
                    f"{suggestion.field_name} (alias {suggestion.matched_alias})"
                    for suggestion in result.suggestions
                )
                descriptions.append(
                    f"{result.source_header!r} → posible {candidates}; no se asignó automáticamente"
                )
            else:
                descriptions.append(f"{result.source_header!r} (sin correspondencia conocida)")
        raise ValueError(
            "Cabeceras CSV no admitidas: " + "; ".join(descriptions) + "."
        )

    normalized_headers = [
        result.normalized_header or ""
        for result in header_plan.headers
    ]
    field_by_header = {
        result.source_header: result.field_name
        for result in header_plan.headers
        if result.usable and result.source_header is not None and result.field_name is not None
    }
    present_fields = {
        result.field_name
        for result in header_plan.headers
        if result.usable and result.field_name is not None
    }
    email_audit_csv = {"email_from", "email_to"}.issubset(present_fields)
    required_headers = {"observed_at"}
    if not email_audit_csv:
        required_headers.add("event_type")
    missing_headers = missing_required_fields(header_plan, required_headers)
    if missing_headers:
        if email_audit_csv:
            message = (
                "El CSV requiere fecha y tipo de evento, o fecha más emisor/destinatario "
                "para una exportación de auditoría de correo."
            )
        else:
            message = "El CSV requiere fecha y tipo de evento."
        raise ValueError(message)
    # Detener la lectura al llegar a la fila 1001 para no cargar en memoria un
    # número de filas no confiable antes de aplicar el límite de importación.
    raw_rows: list[dict[str, Any]] = []
    try:
        for row in reader:
            if len(raw_rows) >= 1000:
                raise ValueError("Se permiten hasta 1000 eventos por importación.")
            raw_rows.append(row)
    except csv.Error as exc:
        raise ValueError("El CSV contiene una columna demasiado grande o tiene un formato inválido.") from exc
    activity_repository.require_device_exists(device_id)
    normalized: list[dict[str, Any]] = []
    normalized_line_numbers: list[int] = []
    for line, row in enumerate(raw_rows, start=2):
        if row.get(None):
            raise ValueError(f"Fila {line}: contiene más columnas que las cabeceras del CSV.")
        mapped: dict[str, Any] = {}
        for raw_name, value in row.items():
            if raw_name is None:
                continue
            canonical = field_by_header.get(raw_name)
            if canonical is None:
                continue
            if canonical in mapped:
                raise ValueError(f"Fila {line}: hay varias columnas que representan {canonical}.")
            mapped[canonical] = value
        if not mapped.get("observed_at"):
            raise ValueError(f"Fila {line}: falta una fecha/hora.")
        if not mapped.get("event_type") and email_audit_csv:
            mapped["event_type"] = "email_metadata"
            raw_header_set = set(normalized_headers)
            if not mapped.get("email_provider"):
                if {"received_datetime", "received_date_time", "sender_address", "recipient_address"}.issubset(raw_header_set) or {"received_date_time", "sender_address", "recipient_address"}.issubset(raw_header_set):
                    mapped["email_provider"] = "Microsoft 365"
                elif "subject_or_message_id" in raw_header_set:
                    mapped["email_provider"] = "Google Workspace"
        if not mapped.get("event_type"):
            raise ValueError(f"Fila {line}: event_type es obligatorio para eventos no relacionados con correo.")
        try:
            normalized.append(normalize_event(mapped, source_override="manual_import"))
            normalized_line_numbers.append(line)
        except ValueError as exc:
            raise ValueError(f"Fila {line}: {exc}") from exc
    if not normalized:
        if preview:
            return {
                "device_id": device_id,
                "valid_rows": 0,
                "would_import": 0,
                "skipped_duplicates": 0,
                "preview_rows": [],
                "note": "El CSV no contiene eventos. No se guardó ningún dato.",
            }
        return {
            "device_id": device_id,
            "imported": 0,
            "skipped_duplicates": 0,
            "note": "El CSV no contiene eventos.",
        }

    result = activity_repository.import_manual_events(
        device_id,
        normalized,
        normalized_line_numbers,
        now=_now(),
        preview=preview,
    )

    if preview:
        preview_rows = []
        for item, disposition in zip(normalized[:10], result["preview_dispositions"]):
            row = {field: item.get(field) for field in CSV_PREVIEW_FIELDS}
            row["disposition"] = disposition
            preview_rows.append(row)
        return {
            "device_id": device_id,
            "valid_rows": len(normalized),
            "would_import": result["imported"],
            "skipped_duplicates": result["skipped_duplicates"],
            "preview_rows": preview_rows,
            "note": "Vista previa únicamente: no se guardó ningún evento. Se muestran hasta 10 filas de ejemplo.",
        }

    return {
        "device_id": device_id,
        "imported": result["imported"],
        "skipped_duplicates": result["skipped_duplicates"],
        "note": (
            "Importado como metadatos históricos. Las filas no prueban que una persona haya "
            "interactuado con el servicio. Las filas idénticas ya importadas para este dispositivo "
            "se omitieron."
        ),
    }
