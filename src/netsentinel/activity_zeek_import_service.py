"""Importación explícita de registros Zeek conn.log en JSON Lines.

El servicio no ejecuta Zeek ni abre interfaces de red. Valida un archivo que la
persona selecciona, adapta solo metadatos de conexión al contrato compartido y
delega la persistencia transaccional y la deduplicación al repositorio existente.
"""
from __future__ import annotations

import ipaddress
import json
import math
from datetime import datetime, timezone
from typing import Any, Callable

from . import activity_event_service, activity_repository, activity_retention_service, inventory_read_repository

EventNormalizer = Callable[..., dict[str, Any]]

MAX_IMPORT_BYTES = 1_000_000
MAX_IMPORT_ROWS = 1_000
PREVIEW_FIELDS = (
    "observed_at",
    "event_type",
    "source_ip",
    "source_port",
    "destination_ip",
    "destination_port",
    "protocol",
    "bytes_sent",
    "bytes_received",
    "packets_sent",
    "packets_received",
    "source_event_id",
)

MAX_COUNTER = 9_223_372_036_854_775_807


def _now() -> datetime:
    """Devuelve la hora UTC usada por el repositorio de importación."""
    return activity_retention_service.now()


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Rechaza claves repetidas para no aceptar un registro ambiguo."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("El registro JSON repite una clave.")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    """Rechaza NaN e Infinity, que no son números JSON válidos para este contrato."""
    raise ValueError("El registro JSON contiene un número no válido.")


def _parse_json_line(raw_line: str, line_number: int) -> dict[str, Any] | None:
    """Lee una línea JSON; una línea vacía se ignora y los errores indican su número."""
    if not raw_line.strip():
        return None
    try:
        record = json.loads(
            raw_line,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError(f"Fila {line_number}: el registro no es JSON válido.") from exc
    if not isinstance(record, dict):
        raise ValueError(f"Fila {line_number}: cada registro debe ser un objeto JSON.")
    return record


def _required_text(record: dict[str, Any], field: str, line_number: int, *, maximum: int = 160) -> str:
    """Valida los identificadores y etiquetas que Zeek debe aportar."""
    value = record.get(field)
    if not isinstance(value, str):
        raise ValueError(f"Fila {line_number}: falta el campo obligatorio {field}.")
    value = value.strip()
    if not value or value == "-" or len(value) > maximum:
        raise ValueError(f"Fila {line_number}: el campo {field} está vacío o fuera de límite.")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"Fila {line_number}: el campo {field} contiene caracteres de control.")
    return value


def _timestamp_from_zeek(value: Any, line_number: int) -> str:
    """Convierte el tiempo Unix de Zeek a UTC, conservando la precisión del esquema."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Fila {line_number}: ts debe ser un número de tiempo Unix válido.")
    try:
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError("ts debe ser finito.")
        parsed = datetime.fromtimestamp(numeric_value, tz=timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError) as exc:
        raise ValueError(f"Fila {line_number}: ts está fuera del rango admitido o no es finito.") from exc
    return parsed.replace(microsecond=0).isoformat(timespec="seconds")


def _zeek_port(record: dict[str, Any], field: str, line_number: int) -> int | None:
    """Normaliza puertos; el 0 usado por Zeek para protocolos sin puerto queda desconocido."""
    if field not in record:
        raise ValueError(f"Fila {line_number}: falta el campo obligatorio {field}.")
    value = record[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Fila {line_number}: {field} debe ser un entero.")
    if value < 0 or value > 65535:
        raise ValueError(f"Fila {line_number}: {field} está fuera del rango de puerto.")
    return value or None


def _optional_counter(record: dict[str, Any], field: str, line_number: int) -> int | None:
    """Mantiene ausente como desconocido y distingue un contador observado en cero."""
    if field not in record or record[field] is None or record[field] == "-":
        return None
    value = record[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Fila {line_number}: {field} debe ser un entero o un campo no disponible.")
    if not 0 <= value <= MAX_COUNTER:
        raise ValueError(f"Fila {line_number}: {field} está fuera del rango admitido.")
    return value


def _protocol(value: str) -> str:
    """Reduce los protocolos de Zeek al conjunto común sin inventar un protocolo."""
    normalized = value.strip().lower()
    if normalized in {"tcp", "udp", "icmp", "quic"}:
        return normalized
    return "other"


def _to_event(record: dict[str, Any], line_number: int) -> dict[str, Any]:
    """Mapea únicamente campos de conexión documentados por Zeek."""
    timestamp = _timestamp_from_zeek(record.get("ts"), line_number)
    uid = _required_text(record, "uid", line_number, maximum=155)
    source_ip = _required_text(record, "id.orig_h", line_number, maximum=64)
    destination_ip = _required_text(record, "id.resp_h", line_number, maximum=64)
    source_port = _zeek_port(record, "id.orig_p", line_number)
    destination_port = _zeek_port(record, "id.resp_p", line_number)
    protocol = _required_text(record, "proto", line_number, maximum=64)
    return {
        "observed_at": timestamp,
        "event_type": "connection",
        "source_ip": source_ip,
        "source_port": source_port,
        "destination_ip": destination_ip,
        "destination_port": destination_port,
        "protocol": _protocol(protocol),
        # Use IP-layer bytes consistently. orig_bytes/resp_bytes measure payload
        # bytes and are intentionally not mixed into these generic counters.
        # Missing values remain None; a reported zero remains zero.
        "bytes_sent": _optional_counter(record, "orig_ip_bytes", line_number),
        "bytes_received": _optional_counter(record, "resp_ip_bytes", line_number),
        "packets_sent": _optional_counter(record, "orig_pkts", line_number),
        "packets_received": _optional_counter(record, "resp_pkts", line_number),
        # Prefix IDs so they remain identifiable and do not collide with other
        # import formats that also use a field called source_event_id.
        "source_event_id": f"zeek:{uid}",
    }


def _parse_utc_timestamp(value: Any) -> datetime | None:
    """Convierte una fecha ISO a UTC; los valores sin zona se tratan como UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _device_address_history(device_id: int) -> list[dict[str, Any]]:
    """Devuelve las IP del activo con el intervalo en que se observaron."""
    addresses = inventory_read_repository.get_device_addresses(device_id)
    if addresses is None:
        raise LookupError("No existe el dispositivo seleccionado.")

    history: list[dict[str, Any]] = []
    for address in addresses:
        try:
            ip_address = str(ipaddress.ip_address(str(address.get("ip_address", ""))))
        except ValueError:
            continue
        first_seen = _parse_utc_timestamp(address.get("first_seen"))
        last_seen = _parse_utc_timestamp(address.get("last_seen"))
        if first_seen is None or last_seen is None or first_seen > last_seen:
            continue
        history.append({
            "ip_address": ip_address,
            "first_seen": first_seen,
            "last_seen": last_seen,
        })

    if not history:
        # Compatibility with older inventories that predate device_addresses.
        # Only use the primary IP and device-level interval when no usable
        # per-address history exists; never extend a recorded address interval.
        legacy = inventory_read_repository.get_device_history(device_id, limit=1)
        device = legacy.get("device", {}) if legacy else {}
        try:
            ip_value = str(ipaddress.ip_address(str(device.get("ip_address", ""))))
        except ValueError:
            ip_value = ""
        first_seen = _parse_utc_timestamp(device.get("first_seen"))
        last_seen = _parse_utc_timestamp(device.get("last_seen"))
        if ip_value and first_seen is not None and last_seen is not None and first_seen <= last_seen:
            history.append({
                "ip_address": ip_value,
                "first_seen": first_seen,
                "last_seen": last_seen,
            })

    if not history:
        raise ValueError(
            "El dispositivo no tiene un historial de direcciones con fechas válidas. "
            "Actualizá el inventario antes de asociar conexiones."
        )
    return history


def import_jsonl(
    device_id: int,
    jsonl_data: str,
    *,
    normalize_event: EventNormalizer | None = None,
    preview: bool = False,
) -> dict[str, Any]:
    """Valida un archivo Zeek JSONL y lo previsualiza o importa de forma atómica.

    Solo se admite el formato JSON Lines, con un objeto por línea. No se leen
    paquetes ni se contacta con la fuente Zeek. La escritura reutiliza la política
    común de retención y deduplicación de las importaciones manuales.
    """
    if not isinstance(jsonl_data, str):
        raise ValueError("El archivo debe ser texto JSON Lines.")
    try:
        encoded_size = len(jsonl_data.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("El archivo debe contener texto UTF-8 válido.") from exc
    if encoded_size > MAX_IMPORT_BYTES:
        raise ValueError("El archivo supera el máximo de 1 MB.")
    # Tolerar el BOM de un archivo UTF-8, sin permitirlo en mitad de los registros.
    if jsonl_data.startswith("\ufeff"):
        jsonl_data = jsonl_data[1:]

    rows: list[tuple[int, dict[str, Any]]] = []
    for line_number, raw_line in enumerate(jsonl_data.split("\n"), start=1):
        record = _parse_json_line(raw_line, line_number)
        if record is None:
            continue
        if len(rows) >= MAX_IMPORT_ROWS:
            raise ValueError("Se permiten hasta 1000 registros por importación.")
        rows.append((line_number, record))

    activity_repository.require_device_exists(device_id)
    if not rows:
        if preview:
            return {
                "device_id": device_id,
                "valid_rows": 0,
                "matching_rows": 0,
                "would_import": 0,
                "skipped_duplicates": 0,
                "skipped_out_of_scope": 0,
                "skipped_ambiguous": 0,
                "preview_rows": [],
                "note": "El archivo no contiene registros. No se guardó ningún evento.",
            }
        return {
            "device_id": device_id,
            "valid_rows": 0,
            "matching_rows": 0,
            "imported": 0,
            "skipped_duplicates": 0,
            "skipped_out_of_scope": 0,
            "skipped_ambiguous": 0,
            "note": "El archivo no contiene registros.",
        }

    normalizer = normalize_event or activity_event_service.normalize_event
    normalized: list[dict[str, Any]] = []
    source_line_numbers: list[int] = []
    for line_number, record in rows:
        try:
            mapped = _to_event(record, line_number)
            normalized.append(normalizer(mapped, source_override="manual_import"))
            source_line_numbers.append(line_number)
        except ValueError as exc:
            if str(exc).startswith(f"Fila {line_number}:"):
                raise
            raise ValueError(f"Fila {line_number}: {exc}") from exc

    # A sensor log may contain traffic for many hosts, and DHCP can reuse an IP.
    # Attribute a row only when an address was observed on this asset at that
    # event time and no other asset has an overlapping recorded interval for it.
    selected_history = _device_address_history(device_id)
    candidate_ips = sorted({
        event[field]
        for event in normalized
        for field in ("source_ip", "destination_ip")
        if event.get(field)
    })
    owners = inventory_read_repository.get_address_owners(candidate_ips)
    matching: list[tuple[dict[str, Any], int]] = []
    skipped_out_of_scope = 0
    skipped_ambiguous = 0

    for event, line_number in zip(normalized, source_line_numbers):
        observed_at = _parse_utc_timestamp(event.get("observed_at"))
        if observed_at is None:
            # normalize_event normally guarantees this, but keep the source boundary defensive.
            raise ValueError(f"Fila {line_number}: la fecha normalizada no es válida.")

        has_unique_selected_owner = False
        has_ambiguous_selected_owner = False
        for field in ("source_ip", "destination_ip"):
            ip_value = event.get(field)
            if not ip_value:
                continue
            active_owner_ids: set[int] = set()
            for owner in owners.get(str(ip_value), []):
                first_seen = _parse_utc_timestamp(owner.get("first_seen"))
                last_seen = _parse_utc_timestamp(owner.get("last_seen"))
                if first_seen is None or last_seen is None or first_seen > last_seen:
                    continue
                if first_seen <= observed_at <= last_seen:
                    try:
                        active_owner_ids.add(int(owner["device_id"]))
                    except (KeyError, TypeError, ValueError):
                        continue

            if device_id in active_owner_ids:
                if len(active_owner_ids) == 1:
                    has_unique_selected_owner = True
                else:
                    has_ambiguous_selected_owner = True

        # Also ensure this row lies inside at least one of the selected asset's
        # recorded address windows, even if the global owner query was incomplete.
        in_selected_window = any(
            event.get(field) == address["ip_address"]
            and address["first_seen"] <= observed_at <= address["last_seen"]
            for field in ("source_ip", "destination_ip")
            for address in selected_history
        )
        if has_unique_selected_owner and in_selected_window:
            matching.append((event, line_number))
        elif has_ambiguous_selected_owner and in_selected_window:
            skipped_ambiguous += 1
        else:
            skipped_out_of_scope += 1

    matching_events = [event for event, _line in matching]
    matching_lines = [line_number for _event, line_number in matching]

    if not matching_events:
        notes = []
        if skipped_out_of_scope:
            notes.append(
                f"{skipped_out_of_scope} registro(s) quedan fuera del intervalo observado del dispositivo."
            )
        if skipped_ambiguous:
            notes.append(
                f"{skipped_ambiguous} registro(s) tienen una IP con propietarios históricos solapados."
            )
        detail = " ".join(notes) or "No se hallaron conexiones atribuibles al dispositivo."
        note = "No se guardaron eventos. " + detail
        result_base = {
            "device_id": device_id,
            "valid_rows": len(normalized),
            "matching_rows": 0,
            "skipped_out_of_scope": skipped_out_of_scope,
            "skipped_ambiguous": skipped_ambiguous,
        }
        if preview:
            return {
                **result_base,
                "would_import": 0,
                "skipped_duplicates": 0,
                "preview_rows": [],
                "note": "Vista previa solamente. " + note,
            }
        return {
            **result_base,
            "imported": 0,
            "skipped_duplicates": 0,
            "note": note,
        }

    result = activity_repository.import_manual_events(
        device_id,
        matching_events,
        matching_lines,
        now=_now(),
        preview=preview,
    )
    if not preview:
        if result["imported"]:
            note = "Se importaron las conexiones que incluyen una IP del dispositivo seleccionado."
        else:
            note = "No se añadieron registros nuevos; las conexiones asociadas ya existían."
        if skipped_out_of_scope:
            note += f" Se omitieron {skipped_out_of_scope} registro(s) de otros dispositivos."
        if skipped_out_of_scope:
            note += f" Se omitieron {skipped_out_of_scope} registro(s) fuera del intervalo observado."
        if skipped_ambiguous:
            note += f" Se omitieron {skipped_ambiguous} registro(s) con propiedad de IP ambigua."
        return {
            "device_id": device_id,
            "valid_rows": len(normalized),
            "matching_rows": len(matching_events),
            "imported": result["imported"],
            "skipped_duplicates": result["skipped_duplicates"],
            "skipped_out_of_scope": skipped_out_of_scope,
            "skipped_ambiguous": skipped_ambiguous,
            "note": note,
        }

    preview_rows = []
    for event, disposition in zip(matching_events[:10], result["preview_dispositions"]):
        row = {field: event.get(field) for field in PREVIEW_FIELDS}
        row["disposition"] = disposition
        preview_rows.append(row)
    note = "Vista previa solamente: no se guardó ningún evento."
    if skipped_out_of_scope:
        note += f" Se omitirían {skipped_out_of_scope} registro(s) fuera del intervalo observado."
    if skipped_ambiguous:
        note += f" Se omitirían {skipped_ambiguous} registro(s) con propiedad de IP ambigua."
    return {
        "device_id": device_id,
        "valid_rows": len(normalized),
        "matching_rows": len(matching_events),
        "would_import": result["imported"],
        "skipped_duplicates": result["skipped_duplicates"],
        "skipped_out_of_scope": skipped_out_of_scope,
        "skipped_ambiguous": skipped_ambiguous,
        "preview_rows": preview_rows,
        "note": note,
    }
