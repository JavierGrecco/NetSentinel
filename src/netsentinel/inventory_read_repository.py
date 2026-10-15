"""Consultas de solo lectura para el inventario y el historial local."""
from __future__ import annotations

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


def get_scans(path: Path | None = None, limit: int = 30) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            "SELECT * FROM scans ORDER BY started_at DESC, id DESC LIMIT ?",
            (max(1, min(limit, 100)),),
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
