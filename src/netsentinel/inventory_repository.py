"""Fachada de compatibilidad y escrituras transaccionales del inventario.

Las consultas sin efectos viven en inventory_read_repository.py. Esta capa
conserva las escrituras: cada exploración, las direcciones y observaciones que
genera y los eventos asociados se confirman o revierten como una sola unidad.
"""
from __future__ import annotations

import json
from ipaddress import ip_address
from pathlib import Path
from typing import Any

from .database_storage import connect, utc_now
from .events_repository import _insert_event
from .inventory_read_repository import (
    get_device_addresses,
    get_device_history,
    get_scan_observations,
    get_scans,
    list_devices,
)
from .inventory_repository_support import _device_dict, _ip_sort_key
from .network_models import Neighbor
from .vendor import is_locally_administered, manufacturer_for_mac, oui_database_path


def record_scan(
    neighbors: list[Neighbor],
    errors: list[str] | None = None,
    path: Path | None = None,
    discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Registra una lectura, múltiples IP por MAC y cambios IPv4 confirmables."""
    started = utc_now()
    errors = errors or []
    discovery = discovery or {}
    # Duplicate source output is common when fallback commands overlap.
    deduplicated: dict[tuple[str, str], Neighbor] = {}
    for neighbor in neighbors:
        key = (neighbor.ip_address, neighbor.mac_address)
        current = deduplicated.get(key)
        if current is None or (not current.interface and neighbor.interface):
            deduplicated[key] = neighbor
    neighbors = list(deduplicated.values())
    grouped: dict[str, list[Neighbor]] = {}
    for neighbor in neighbors:
        grouped.setdefault(neighbor.mac_address, []).append(neighbor)
    source_names = sorted({n.source for n in neighbors})
    source = ", ".join(source_names) if source_names else "system-neighbor-table"
    new_devices = 0

    with connect(path) as db:
        cursor = db.execute(
            "INSERT INTO scans(started_at, finished_at, source, devices_found, errors_json, discovery_json) VALUES (?, ?, ?, ?, ?, ?)",
            (started, started, source, len(grouped), json.dumps(errors, ensure_ascii=False), json.dumps(discovery, ensure_ascii=False)),
        )
        scan_id = int(cursor.lastrowid)

        for mac, observed in grouped.items():
            now = utc_now()
            observed_by_ip = {item.ip_address: item for item in observed}
            sorted_ips = sorted(observed_by_ip, key=_ip_sort_key)
            preferred_neighbor = next((n for n in observed if n.ip_address == sorted_ips[0]), observed[0])
            manufacturer = manufacturer_for_mac(mac)
            oui_source = "oui.csv (base local)" if oui_database_path().is_file() else None
            oui_checked_at = now if oui_source else None
            locally_administered = int(is_locally_administered(mac))
            row = db.execute(
                "SELECT id, ip_address, trusted, manufacturer FROM devices WHERE mac_address = ?", (mac,)
            ).fetchone()

            if row is None:
                primary_ip = sorted_ips[0]
                cur = db.execute(
                    """INSERT INTO devices
                       (mac_address, ip_address, interface, first_seen, last_seen, manufacturer,
                        manufacturer_source, manufacturer_checked_at, mac_locally_administered)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (mac, primary_ip, preferred_neighbor.interface, now, now, manufacturer,
                     oui_source, oui_checked_at, locally_administered),
                )
                device_id = int(cur.lastrowid)
                new_devices += 1
                _insert_event(
                    db, "new_device", "warning", device_id,
                    f"Dispositivo no registrado detectado: {primary_ip} ({mac}). Revisá si es conocido.", now,
                )
            else:
                device_id = int(row["id"])
                old_primary_ip = row["ip_address"]
                # Preserve the current primary IP if it is still observed; otherwise prefer IPv4.
                primary_ip = old_primary_ip if old_primary_ip in observed_by_ip else sorted_ips[0]
                try:
                    old_ip_obj = ip_address(old_primary_ip)
                    new_ip_obj = ip_address(primary_ip)
                except ValueError:
                    old_ip_obj = new_ip_obj = None
                if (
                    old_primary_ip != primary_ip
                    and old_ip_obj is not None and new_ip_obj is not None
                    and old_ip_obj.version == new_ip_obj.version == 4
                    and old_primary_ip not in observed_by_ip
                ):
                    _insert_event(
                        db, "ip_changed", "warning", device_id,
                        f"Se observó un cambio de IPv4 para {mac}: {old_primary_ip} → {primary_ip}. "
                        "Es una observación nueva; verificá si corresponde al mismo equipo.", now,
                    )
                db.execute(
                    """UPDATE devices SET ip_address = ?, interface = COALESCE(?, interface), last_seen = ?,
                       manufacturer = COALESCE(?, manufacturer),
                       manufacturer_source = COALESCE(?, manufacturer_source),
                       manufacturer_checked_at = COALESCE(?, manufacturer_checked_at),
                       mac_locally_administered = ? WHERE id = ?""",
                    (primary_ip, observed_by_ip[primary_ip].interface, now, manufacturer,
                     oui_source, oui_checked_at, locally_administered, device_id),
                )

            for item in observed:
                address_row = db.execute(
                    "SELECT first_seen FROM device_addresses WHERE device_id = ? AND ip_address = ?",
                    (device_id, item.ip_address),
                ).fetchone()
                if address_row is None:
                    db.execute(
                        """INSERT INTO device_addresses
                           (device_id, ip_address, first_seen, last_seen, interface, source)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (device_id, item.ip_address, now, now, item.interface, item.source),
                    )
                else:
                    db.execute(
                        """UPDATE device_addresses SET last_seen = ?, interface = COALESCE(?, interface), source = ?
                           WHERE device_id = ? AND ip_address = ?""",
                        (now, item.interface, item.source, device_id, item.ip_address),
                    )
                db.execute(
                    """INSERT INTO observations(scan_id, device_id, observed_at, ip_address, source)
                       VALUES (?, ?, ?, ?, ?)""",
                    (scan_id, device_id, now, item.ip_address, item.source),
                )

        finished = utc_now()
        db.execute(
            "UPDATE scans SET finished_at = ?, devices_found = ? WHERE id = ?",
            (finished, len(grouped), scan_id),
        )

    return {
        "scan_id": scan_id,
        "started_at": started,
        "finished_at": finished,
        "devices_found": len(grouped),
        "addresses_found": len(neighbors),
        "new_devices": new_devices,
        "errors": errors,
        "source": source,
    }


def update_device(
    device_id: int,
    *,
    trusted: bool | None = None,
    display_name: str | None = None,
    notes: str | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    with connect(path) as db:
        row = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        if row is None:
            return None
        new_trusted = int(trusted) if trusted is not None else row["trusted"]
        new_name = display_name.strip()[:120] if display_name is not None else row["display_name"]
        new_notes = notes.strip()[:2000] if notes is not None else row["notes"]
        changed_trust = trusted is not None and int(trusted) != int(row["trusted"])
        db.execute(
            "UPDATE devices SET trusted = ?, display_name = ?, notes = ? WHERE id = ?",
            (new_trusted, new_name, new_notes, device_id),
        )
        if changed_trust:
            _insert_event(
                db, "trust_changed", "info", device_id,
                f"Dispositivo marcado como {'de confianza' if trusted else 'no verificado'}", utc_now(),
            )
        updated = db.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
    return _device_dict(updated)
