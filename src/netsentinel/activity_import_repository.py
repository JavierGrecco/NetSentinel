"""Persistencia transaccional de eventos importados manualmente.

La validación del archivo y sus mensajes se resuelven en el servicio de importación.
Aquí se aplican retención, deduplicación y escritura atómica; la vista previa no escribe.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from . import database
from .activity_repository_support import _require_device
from .activity_retention_repository import _utc_iso, cleanup, get_retention_days


_MANUAL_IMPORT_DEDUP_FIELDS = (
    "observed_at", "event_type", "domain", "source_ip", "source_port",
    "destination_ip", "destination_port", "protocol", "bytes_sent", "bytes_received",
    "packets_sent", "packets_received", "network_interface", "source_event_id",
    "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)


def import_manual_events(
    device_id: int,
    events: list[Mapping[str, Any]],
    source_line_numbers: list[int],
    *,
    now: datetime,
    preview: bool,
) -> dict[str, Any]:
    """Valida retención y deduplica/guarda eventos manuales de forma atómica.

    La vista previa es de solo lectura. La importación toma el bloqueo de escritura
    antes de comprobar la retención y los duplicados para evitar carreras con otra
    importación o un cambio de política de retención.
    """
    if len(events) != len(source_line_numbers):
        raise ValueError("La importación recibió filas y números de línea incompatibles.")

    imported_count = 0
    skipped_duplicates = 0
    preview_dispositions: list[str] = []
    seen_in_batch: set[tuple[Any, ...]] = set()

    with database.connect() as db:
        if not preview:
            db.execute("BEGIN IMMEDIATE")
        _require_device(db, device_id)

        retention_days = get_retention_days(db)
        cutoff = _utc_iso(now - timedelta(days=retention_days))

        # Rechazar el lote completo antes de limpiar o escribir evita importaciones
        # parciales cuando alguna fila queda fuera del período conservado.
        for line, item in zip(source_line_numbers, events):
            if item["observed_at"] < cutoff:
                raise ValueError(
                    f"Fila {line}: la fecha queda fuera de la retención configurada "
                    f"de {retention_days} día(s). Aumentá la retención antes de importar "
                    "ese período y volvé a previsualizar la importación."
                )

        duplicate_sql = (
            "SELECT 1 FROM activity_events "
            "WHERE device_id = ? AND source = 'manual_import' AND "
            + " AND ".join(f"{field} IS ?" for field in _MANUAL_IMPORT_DEDUP_FIELDS)
            + " LIMIT 1"
        )
        if preview:
            # La vista previa solo compara con eventos que seguirían en retención.
            duplicate_sql = duplicate_sql.replace(
                "source = 'manual_import' AND",
                "source = 'manual_import' AND observed_at >= ? AND",
            )
        duplicate_source_id_sql = (
            "SELECT 1 FROM activity_events "
            "WHERE device_id = ? AND source = 'manual_import' AND source_event_id = ?"
            + (" AND observed_at >= ?" if preview else "")
            + " LIMIT 1"
        )
        if not preview:
            cleanup(db, now=now)

        now_text = _utc_iso(now)
        for item in events:
            values = tuple(item.get(field) for field in _MANUAL_IMPORT_DEDUP_FIELDS)
            source_event_id = item.get("source_event_id")
            # Una fuente puede exportar el mismo registro con metadatos añadidos
            # después. Si trae un ID estable, ese ID es la identidad principal.
            # Sin ID de origen conservamos la deduplicación por todos los campos.
            identity = ("source_event_id", source_event_id) if source_event_id else ("fields", *values)
            disposition = "new"
            if identity in seen_in_batch:
                skipped_duplicates += 1
                disposition = "duplicate"
            else:
                seen_in_batch.add(identity)
                if source_event_id:
                    params = (
                        (device_id, source_event_id, cutoff)
                        if preview
                        else (device_id, source_event_id)
                    )
                    duplicate = db.execute(duplicate_source_id_sql, params).fetchone()
                else:
                    params = (device_id, cutoff, *values) if preview else (device_id, *values)
                    duplicate = db.execute(duplicate_sql, params).fetchone()
                if duplicate:
                    skipped_duplicates += 1
                    disposition = "duplicate"
                else:
                    if not preview:
                        db.execute(
                            """INSERT INTO activity_events
                               (session_id, device_id, observed_at, received_at, event_type, source, domain,
                                source_ip, source_port, destination_ip, destination_port, protocol,
                                bytes_sent, bytes_received, packets_sent, packets_received, network_interface, source_event_id,
                                app_name, page_url, search_engine, search_terms,
                                email_provider, email_from, email_to, email_subject, blocked)
                               VALUES (NULL, ?, ?, ?, ?, 'manual_import', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                device_id, item["observed_at"], now_text, item["event_type"], item["domain"],
                                item.get("source_ip"), item.get("source_port"), item["destination_ip"],
                                item["destination_port"], item["protocol"], item.get("bytes_sent"),
                                item.get("bytes_received"), item.get("packets_sent"), item.get("packets_received"),
                                item.get("network_interface"), item.get("source_event_id"),
                                item["app_name"], item["page_url"], item["search_engine"], item["search_terms"],
                                item["email_provider"], item["email_from"], item["email_to"], item["email_subject"], item["blocked"],
                            ),
                        )
                    imported_count += 1

            if preview and len(preview_dispositions) < 10:
                preview_dispositions.append(disposition)

    return {
        "imported": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "preview_dispositions": preview_dispositions,
    }
