"""Importación CSV de actividad, separada de la API y de las consultas SQL.

Este servicio convierte archivos autorizados en eventos validados. La lectura de
cabeceras, los alias de proveedores, los límites y la vista previa viven aquí;
las transacciones, la retención y la deduplicación se delegan al repositorio.
No importa FastAPI ni administra conexiones SQLite directamente.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Any, Callable

from . import activity_repository

EventNormalizer = Callable[..., dict[str, Any]]

CSV_FIELDS = {
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "blocked", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject",
}
CSV_PREVIEW_FIELDS = (
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)
SENSITIVE_HEADERS = {
    "url", "full_url", "path", "query_string", "username", "user",
    "password", "passwd", "token", "cookie", "authorization", "payload",
    "body", "message", "email_body", "message_body", "body_text", "body_html",
    "content", "email_message", "request_body", "response_body", "attachment",
    "attachments", "attachment_content", "message_content",
}

CSV_IGNORED_METADATA_HEADERS = {
    "id", "message_id", "messageid", "message_trace_id", "messagetraceid",
    "status", "delivery_status", "direction", "size", "message_size",
    "from_ip", "fromip", "to_ip", "toip", "sender_ip", "senderip",
    "recipient_ip", "recipientip", "delivery_step", "event", "route",
    "internet_message_id", "internetmessageid", "network_message_id",
    "networkmessageid", "trace_id", "traceid",
}
CSV_HEADER_ALIASES = {
    "observed_at": {
        "date", "datetime", "timestamp", "date_time", "date_and_time",
        "received_datetime", "received_date_time", "sent_datetime", "sent_date_time",
        "received_time", "sent_time", "time",
    },
    "event_type": {"eventtype"},
    "email_provider": {"provider", "mail_provider", "email_service", "service"},
    "email_from": {
        "from", "from_address", "from_email", "sender", "sender_address",
        "senderaddress", "sender_email", "sender_email_address",
    },
    "email_to": {
        "to", "to_address", "to_email", "recipient", "recipient_address",
        "recipientaddress", "recipient_email", "recipients",
    },
    "email_subject": {
        "subject", "subject_line", "message_subject", "subject_or_message_id",
    },
}


def _normalized_csv_header(value: str | None) -> str:
    raw = str(value or "").strip().lstrip(chr(0xFEFF))
    # Provider exports commonly use camelCase fields such as receivedDateTime.
    raw = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", raw)
    return re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")

def _is_sensitive_csv_header(value: str | None) -> bool:
    normalized = _normalized_csv_header(value)
    if normalized in SENSITIVE_HEADERS:
        return True
    parts = set(normalized.split("_"))
    if parts.intersection({"body", "content", "payload", "attachment", "attachments"}):
        return True
    # A message identifier is harmless metadata; a message/body/content column is not.
    return "message" in parts and "id" not in parts and "subject" not in parts


def _canonical_csv_header(value: str | None) -> str | None:
    normalized = _normalized_csv_header(value)
    if normalized in CSV_IGNORED_METADATA_HEADERS:
        return None
    if normalized in CSV_FIELDS:
        return normalized
    for canonical, aliases in CSV_HEADER_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized

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
        # Accessing fieldnames reads the CSV header and can itself raise csv.Error
        # when an input field exceeds the standard library's parser limit.
        raw_headers = list(reader.fieldnames or [])
    except csv.Error as exc:
        raise ValueError("El CSV contiene una cabecera inválida o demasiado grande.") from exc
    if not raw_headers:
        raise ValueError("El CSV está vacío o no contiene cabeceras.")
    forbidden = [name for name in raw_headers if _is_sensitive_csv_header(name)]
    if forbidden:
        raise ValueError(
            "El CSV incluye campos que no se importan por privacidad: "
            + ", ".join(sorted(str(name) for name in forbidden)) + "."
        )
    normalized_headers = [_normalized_csv_header(name) for name in raw_headers]
    headers = [_canonical_csv_header(name) for name in raw_headers]
    effective_headers = [name for name in headers if name is not None]
    if len(set(effective_headers)) != len(effective_headers):
        raise ValueError("El CSV repite una cabecera tras normalizar los nombres de columna.")
    email_audit_csv = {"email_from", "email_to"}.issubset(set(effective_headers))
    if "observed_at" not in effective_headers or (
        "event_type" not in effective_headers and not email_audit_csv
    ):
        raise ValueError(
            "El CSV requiere fecha y tipo de evento, o fecha más emisor/destinatario "
            "para una exportación de auditoría de correo."
        )
    unknown = set(effective_headers) - CSV_FIELDS
    if unknown:
        raise ValueError("Cabeceras CSV no admitidas: " + ", ".join(sorted(unknown)) + ".")
    # Stop parsing as soon as row 1001 is reached instead of materializing an
    # attacker-controlled number of dictionaries before applying the import cap.
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
            canonical = _canonical_csv_header(raw_name)
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
