"""Consultas de solo lectura para el inventario y el historial local."""
from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any

from .database_storage import connect
from .inventory_repository_support import _device_dict


def list_devices(path: Path | None = None, query: str = "") -> list[dict[str, Any]]:
    """Lista dispositivos con búsqueda sobre todas sus direcciones observadas.

    El JOIN carga el inventario y sus direcciones en una sola consulta, sin una
    consulta SQLite adicional por cada dispositivo.
    """
    select = """SELECT d.*,
                       a.ip_address AS _address_ip_address,
                       a.first_seen AS _address_first_seen,
                       a.last_seen AS _address_last_seen,
                       a.interface AS _address_interface,
                       a.source AS _address_source
                FROM devices d
                LEFT JOIN device_addresses a ON a.device_id = d.id"""
    order = """ ORDER BY d.trusted ASC, d.last_seen DESC, d.id ASC,
                        CASE WHEN instr(COALESCE(a.ip_address, ''), ':') = 0 THEN 0 ELSE 1 END,
                        a.ip_address"""
    with connect(path) as db:
        if query.strip():
            value = f"%{query.strip()}%"
            rows = db.execute(
                select + """ WHERE d.mac_address LIKE ? OR d.ip_address LIKE ?
                    OR d.display_name LIKE ? OR d.notes LIKE ?
                    OR COALESCE(d.manufacturer, '') LIKE ?
                    OR COALESCE(d.interface, '') LIKE ?
                    OR EXISTS (
                        SELECT 1 FROM device_addresses matched_address
                        WHERE matched_address.device_id = d.id
                          AND matched_address.ip_address LIKE ?
                    )""" + order,
                (value, value, value, value, value, value, value),
            ).fetchall()
        else:
            rows = db.execute(select + order).fetchall()

    devices_by_id: dict[int, dict[str, Any]] = {}
    for row in rows:
        values = dict(row)
        address_ip = values.pop("_address_ip_address")
        address = {
            "ip_address": address_ip,
            "first_seen": values.pop("_address_first_seen"),
            "last_seen": values.pop("_address_last_seen"),
            "interface": values.pop("_address_interface"),
            "source": values.pop("_address_source"),
        }
        device_id = int(values["id"])
        device = devices_by_id.get(device_id)
        if device is None:
            device = _device_dict(values)
            device["addresses"] = []
            devices_by_id[device_id] = device
        if address_ip is not None:
            device["addresses"].append(address)
    return list(devices_by_id.values())


def get_device_addresses(device_id: int, path: Path | None = None) -> list[dict[str, Any]] | None:
    with connect(path) as db:
        exists = db.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone()
        if exists is None:
            return None
        rows = db.execute(
            """SELECT ip_address, first_seen, last_seen, interface, source
               FROM device_addresses WHERE device_id = ? ORDER BY last_seen DESC""",
            (device_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_address_owners(
    ip_addresses: list[str], path: Path | None = None
) -> dict[str, list[dict[str, Any]]]:
    """Devuelve los activos que tienen registrada cada IP y su intervalo observado.

    La consulta es de solo lectura y se limita a las direcciones solicitadas.
    Permite a las importaciones detectar reutilización o intervalos solapados de IP
    antes de asociar una conexión a una ficha del inventario.
    """
    addresses = sorted({str(value) for value in ip_addresses if value})
    owners: dict[str, list[dict[str, Any]]] = {address: [] for address in addresses}
    if not addresses:
        return owners

    # Mantener grupos moderados para no depender de un límite SQLite de parámetros alto.
    with connect(path) as db:
        for offset in range(0, len(addresses), 400):
            batch = addresses[offset : offset + 400]
            placeholders = ",".join("?" for _ in batch)
            rows = db.execute(
                "SELECT device_id, ip_address, first_seen, last_seen "
                "FROM device_addresses WHERE ip_address IN (" + placeholders + ") "
                "UNION ALL "
                "SELECT d.id AS device_id, d.ip_address, d.first_seen, d.last_seen "
                "FROM devices d WHERE d.ip_address IN (" + placeholders + ") "
                "AND NOT EXISTS (SELECT 1 FROM device_addresses a "
                "WHERE a.device_id = d.id AND a.ip_address = d.ip_address) "
                "ORDER BY 2, 3, 1",
                [*batch, *batch],
            ).fetchall()
            for row in rows:
                item = dict(row)
                owners.setdefault(str(item["ip_address"]), []).append(item)
    return owners


def get_device_history(device_id: int, limit: int = 100, path: Path | None = None) -> dict[str, Any] | None:
    """Devuelve observaciones históricas de un dispositivo, más recientes primero."""
    bounded_limit = max(1, min(int(limit), 500))
    with connect(path) as db:
        device = db.execute(
            "SELECT id, mac_address, ip_address, display_name, first_seen, last_seen FROM devices WHERE id = ?",
            (device_id,),
        ).fetchone()
        if device is None:
            return None
        rows = db.execute(
            """SELECT o.id, o.observed_at, o.ip_address, o.source, o.scan_id,
                      s.source AS scan_source
               FROM observations o
               LEFT JOIN scans s ON s.id = o.scan_id
               WHERE o.device_id = ?
               ORDER BY o.observed_at DESC, o.id DESC
               LIMIT ?""",
            (device_id, bounded_limit),
        ).fetchall()
    return {
        "device": dict(device),
        "observations": [dict(row) for row in rows],
        "count": len(rows),
        "limit": bounded_limit,
        "note": "Este historial refleja cuándo NetSentinel observó el dispositivo y sus direcciones; no registra páginas web ni todas las conexiones de red.",
    }


def get_scans(
    path: Path | None = None,
    limit: int = 30,
    before_started_at: str | None = None,
    before_id: int | None = None,
) -> list[dict[str, Any]]:
    """Devuelve capturas por páginas sin repetir las más recientes al cargar anteriores."""
    bounded_limit = max(1, min(limit, 100))
    if (before_started_at is None) != (before_id is None):
        raise ValueError("La fecha y el identificador de referencia deben enviarse juntos.")

    with connect(path) as db:
        if before_started_at is None:
            rows = db.execute(
                "SELECT * FROM scans ORDER BY started_at DESC, id DESC LIMIT ?",
                (bounded_limit,),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT * FROM scans
                   WHERE started_at < ? OR (started_at = ? AND id < ?)
                   ORDER BY started_at DESC, id DESC
                   LIMIT ?""",
                (before_started_at, before_started_at, max(1, int(before_id)), bounded_limit),
            ).fetchall()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        try:
            item["errors"] = json.loads(item.pop("errors_json"))
        except (TypeError, json.JSONDecodeError):
            item["errors"] = []
            item.pop("errors_json", None)
        try:
            report = json.loads(item.pop("discovery_json"))
            item["discovery"] = report if isinstance(report, dict) else {}
        except (TypeError, json.JSONDecodeError):
            item["discovery"] = {}
            item.pop("discovery_json", None)
        items.append(item)
    return items


def get_scan_by_id(scan_id: int, path: Path | None = None) -> dict[str, Any] | None:
    """Devuelve una lectura concreta sin depender del límite del listado reciente.

    Los indicadores de decodificación permiten distinguir un informe ausente o
    corrupto de una lectura válida sin subredes registradas.
    """
    if isinstance(scan_id, bool) or not isinstance(scan_id, int) or scan_id < 1:
        return None

    with connect(path) as db:
        row = db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if row is None:
        return None

    item = dict(row)
    try:
        errors = json.loads(item.pop("errors_json"))
        item["errors_available"] = isinstance(errors, list)
        item["errors"] = errors if isinstance(errors, list) else []
    except (TypeError, json.JSONDecodeError):
        item.pop("errors_json", None)
        item["errors_available"] = False
        item["errors"] = []

    try:
        discovery = json.loads(item.pop("discovery_json"))
        item["discovery_available"] = isinstance(discovery, dict)
        item["discovery"] = discovery if isinstance(discovery, dict) else {}
    except (TypeError, json.JSONDecodeError):
        item.pop("discovery_json", None)
        item["discovery_available"] = False
        item["discovery"] = {}

    return item


_PRIVATE_IPV4_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)
_COMPARISON_ABSENCE_NOTE = (
    "«No observado» solo significa que el descubrimiento no registró el dispositivo "
    "en esa captura. No demuestra que esté desconectado, apagado ni fuera de la red."
)


def _decode_scan_json(value: Any, expected_type: type) -> Any:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return expected_type()
    return decoded if isinstance(decoded, expected_type) else expected_type()


def _private_scan_networks(discovery: Any) -> set[str]:
    """Devuelve subredes RFC1918 IPv4 normalizadas, sin confiar en texto inválido."""
    if not isinstance(discovery, dict):
        return set()
    networks = discovery.get("networks")
    if not isinstance(networks, list):
        return set()

    result: set[str] = set()
    for item in networks:
        if not isinstance(item, dict):
            continue
        value = item.get("network")
        if not isinstance(value, str):
            continue
        try:
            network = ipaddress.ip_network(value.strip(), strict=False)
        except ValueError:
            continue
        if network.version != 4:
            continue
        if any(network.subnet_of(private) for private in _PRIVATE_IPV4_NETWORKS):
            result.add(network.with_prefixlen)
    return result


def _comparison_scan_info(row: Any) -> tuple[dict[str, Any], set[str]]:
    values = dict(row)
    errors = _decode_scan_json(values.get("errors_json"), list)
    discovery = _decode_scan_json(values.get("discovery_json"), dict)
    networks = _private_scan_networks(discovery)
    discovery_networks = discovery.get("networks", [])
    range_limited = any(
        isinstance(item, dict) and bool(item.get("range_limited"))
        for item in discovery_networks
    ) if isinstance(discovery_networks, list) else False
    info = {
        "id": int(values["id"]),
        "started_at": values.get("started_at"),
        "finished_at": values.get("finished_at"),
        "source": values.get("source") or "",
        "devices_found": int(values.get("devices_found") or 0),
        "errors_count": len(errors),
        "range_limited": range_limited,
        "networks": sorted(networks),
    }
    return info, networks


def compare_scans(
    first_scan_id: int,
    second_scan_id: int,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Compara dos capturas compatibles usando exclusivamente sus observaciones históricas.

    La comparación solo se presenta como válida si ambas capturas registraron al
    menos una misma subred IPv4 privada. La ausencia de observaciones nunca se
    interpreta como prueba de desconexión.
    """
    if int(first_scan_id) == int(second_scan_id):
        raise ValueError("Elegí dos lecturas diferentes para compararlas.")

    with connect(path) as db:
        scan_rows = db.execute(
            "SELECT * FROM scans WHERE id IN (?, ?)",
            (int(first_scan_id), int(second_scan_id)),
        ).fetchall()
        if len(scan_rows) != 2:
            return None

        scan_info_by_id: dict[int, dict[str, Any]] = {}
        networks_by_id: dict[int, set[str]] = {}
        for row in scan_rows:
            info, networks = _comparison_scan_info(row)
            scan_info_by_id[info["id"]] = info
            networks_by_id[info["id"]] = networks

        # Use the actual capture order, even when the caller selected them backwards.
        ordered = sorted(
            scan_info_by_id.values(),
            key=lambda item: (str(item.get("started_at") or ""), int(item["id"])),
        )
        baseline, comparison = ordered
        common_networks = sorted(
            networks_by_id[baseline["id"]] & networks_by_id[comparison["id"]]
        )

        warnings: list[str] = []
        for label, info in (("primera", baseline), ("segunda", comparison)):
            if info["errors_count"]:
                warnings.append(
                    f"La {label} lectura registró errores; sus resultados pueden ser incompletos."
                )
            if info["range_limited"]:
                warnings.append(
                    f"La {label} lectura informó un alcance limitado; puede haber equipos no detectados."
                )

        base_result: dict[str, Any] = {
            "comparable": bool(common_networks),
            "baseline_scan": baseline,
            "comparison_scan": comparison,
            "common_networks": common_networks,
            "warnings": warnings,
            "partial": bool(warnings),
            "absence_note": _COMPARISON_ABSENCE_NOTE,
        }
        if not common_networks:
            base_result.update({
                "reason": (
                    "Las capturas no comparten una subred IPv4 privada registrada. "
                    "Elegí dos lecturas que incluyan al menos una misma red para evitar "
                    "comparar alcances distintos."
                ),
                "summary": None,
                "changes": [],
            })
            return base_result

        common_network_objects = tuple(
            ipaddress.ip_network(network) for network in common_networks
        )
        observation_rows = db.execute(
            """SELECT o.scan_id, o.device_id, o.ip_address, o.observed_at, o.source,
                      d.mac_address, d.display_name
               FROM observations o
               LEFT JOIN devices d ON d.id = o.device_id
               WHERE o.scan_id IN (?, ?)
               ORDER BY o.scan_id, o.device_id, o.ip_address, o.id""",
            (baseline["id"], comparison["id"]),
        ).fetchall()

    # Only compare evidence observed inside a subnet shared by both captures.
    # Otherwise a device from an unrelated subnet could look newly absent/present.
    snapshots: dict[int, dict[int, dict[str, Any]]] = {
        baseline["id"]: {},
        comparison["id"]: {},
    }
    for row in observation_rows:
        scan_id = int(row["scan_id"])
        snapshot = snapshots.get(scan_id)
        if snapshot is None:
            continue
        address = str(row["ip_address"] or "").strip()
        if not address:
            continue
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError:
            continue
        if parsed_address.version != 4 or not any(
            parsed_address in network for network in common_network_objects
        ):
            continue

        device_id = int(row["device_id"])
        device = snapshot.setdefault(device_id, {
            "device_id": device_id,
            "mac_address": str(row["mac_address"] or ""),
            "display_name": str(row["display_name"] or ""),
            "address_sources": {},
            "evidence": [],
        })
        source = str(row["source"] or "").strip()
        sources = device["address_sources"].setdefault(address, set())
        if source:
            sources.add(source)
        device["evidence"].append({
            "scan_id": scan_id,
            "ip_address": address,
            "observed_at": str(row["observed_at"] or ""),
            "source": source,
        })

    baseline_devices = snapshots[baseline["id"]]
    comparison_devices = snapshots[comparison["id"]]
    all_device_ids = set(baseline_devices) | set(comparison_devices)
    counts = {
        "baseline_devices": len(baseline_devices),
        "comparison_devices": len(comparison_devices),
        "only_in_baseline": 0,
        "only_in_comparison": 0,
        "address_changed": 0,
        "unchanged": 0,
        "total_devices": len(all_device_ids),
    }
    changes: list[dict[str, Any]] = []

    for device_id in all_device_ids:
        previous = baseline_devices.get(device_id)
        current = comparison_devices.get(device_id)
        previous_addresses = sorted(previous["address_sources"]) if previous else []
        current_addresses = sorted(current["address_sources"]) if current else []

        if previous is None:
            status = "only_in_comparison"
            counts[status] += 1
        elif current is None:
            status = "only_in_baseline"
            counts[status] += 1
        elif previous_addresses != current_addresses:
            status = "address_changed"
            counts[status] += 1
        else:
            counts["unchanged"] += 1
            continue

        identity = current or previous or {}
        changes.append({
            "device_id": device_id,
            "display_name": identity.get("display_name") or "",
            "mac_address": identity.get("mac_address") or "",
            "status": status,
            "baseline_addresses": previous_addresses,
            "comparison_addresses": current_addresses,
            "baseline_evidence": sorted(
                (previous or {}).get("evidence", []),
                key=lambda item: (item["observed_at"], item["ip_address"], item["source"]),
            ),
            "comparison_evidence": sorted(
                (current or {}).get("evidence", []),
                key=lambda item: (item["observed_at"], item["ip_address"], item["source"]),
            ),
            "baseline_sources": sorted({
                source
                for values in (previous or {}).get("address_sources", {}).values()
                for source in values
            }),
            "comparison_sources": sorted({
                source
                for values in (current or {}).get("address_sources", {}).values()
                for source in values
            }),
        })

    changes.sort(
        key=lambda item: (
            str(item.get("display_name") or item.get("mac_address") or "").casefold(),
            int(item["device_id"]),
        )
    )
    base_result.update({
        "reason": "",
        "summary": counts,
        "changes": changes,
    })
    return base_result


def get_scan_observations(
    scan_id: int,
    path: Path | None = None,
) -> list[dict[str, Any]] | None:
    """Devuelve las direcciones observadas exactamente en una lectura concreta.

    No consulta `device_addresses.last_seen`: esa tabla conserva el último
    avistamiento por dirección y puede cambiar después de la lectura histórica.
    La tabla `observations`, en cambio, vincula cada IP y fuente con su scan_id.
    """
    with connect(path) as db:
        scan = db.execute("SELECT id FROM scans WHERE id = ?", (scan_id,)).fetchone()
        if scan is None:
            return None
        rows = db.execute(
            """SELECT o.scan_id, o.device_id, o.ip_address, o.observed_at, o.source,
                      d.mac_address, d.display_name, d.manufacturer, d.trusted,
                      d.ip_address AS primary_ip
               FROM observations o
               JOIN devices d ON d.id = o.device_id
               WHERE o.scan_id = ?
               ORDER BY o.device_id, o.observed_at, o.ip_address""",
            (scan_id,),
        ).fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["trusted"] = bool(item["trusted"])
        result.append(item)
    return result

