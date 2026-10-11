"""Persistencia SQLite, inventario, direcciones por dispositivo e historial."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Iterator

from .config import database_path
from .discovery import Neighbor
from .vendor import is_locally_administered, manufacturer_for_mac, oui_database_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Abre una conexión transaccional y asegura que se cierre al terminar."""
    db_path = path or database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    connection = sqlite3.connect(db_path, timeout=10)
    if os.name == "posix":
        try:
            os.chmod(db_path.parent, 0o700)
            os.chmod(db_path, 0o600)
        except OSError:
            pass
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path: Path | None = None) -> None:
    """Crea el esquema y migra de forma aditiva bases de datos de v0.1."""
    with connect(path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mac_address TEXT NOT NULL UNIQUE,
                ip_address TEXT NOT NULL,
                interface TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                trusted INTEGER NOT NULL DEFAULT 0 CHECK (trusted IN (0, 1)),
                display_name TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                manufacturer TEXT,
                manufacturer_source TEXT,
                manufacturer_checked_at TEXT,
                mac_locally_administered INTEGER NOT NULL DEFAULT 0 CHECK (mac_locally_administered IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                source TEXT NOT NULL,
                devices_found INTEGER NOT NULL DEFAULT 0,
                errors_json TEXT NOT NULL DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                observed_at TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                source TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS device_addresses (
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                ip_address TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                interface TEXT,
                source TEXT NOT NULL,
                PRIMARY KEY (device_id, ip_address)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL,
                message TEXT NOT NULL,
                acknowledged INTEGER NOT NULL DEFAULT 0 CHECK (acknowledged IN (0, 1))
            );
            CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);
            CREATE INDEX IF NOT EXISTS idx_observations_device_time ON observations(device_id, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_addresses_ip ON device_addresses(ip_address);
            """
        )
        # Compatibility for existing v0.1 installations.
        existing_columns = {row[1] for row in db.execute("PRAGMA table_info(devices)")}
        if "manufacturer" not in existing_columns:
            db.execute("ALTER TABLE devices ADD COLUMN manufacturer TEXT")
        if "manufacturer_source" not in existing_columns:
            db.execute("ALTER TABLE devices ADD COLUMN manufacturer_source TEXT")
        if "manufacturer_checked_at" not in existing_columns:
            db.execute("ALTER TABLE devices ADD COLUMN manufacturer_checked_at TEXT")
        if "mac_locally_administered" not in existing_columns:
            db.execute(
                "ALTER TABLE devices ADD COLUMN mac_locally_administered INTEGER NOT NULL DEFAULT 0"
            )
        # Backfill known address history from existing observations. The current device IP
        # is also inserted because some older installations may have no observation row.
        db.execute(
            """INSERT OR IGNORE INTO device_addresses
               (device_id, ip_address, first_seen, last_seen, interface, source)
               SELECT id, ip_address, first_seen, last_seen, interface, 'migration-v0.1'
               FROM devices"""
        )
        db.execute(
            """INSERT OR IGNORE INTO device_addresses
               (device_id, ip_address, first_seen, last_seen, interface, source)
               SELECT device_id, ip_address, MIN(observed_at), MAX(observed_at), NULL,
                      COALESCE(MIN(source), 'migration-v0.1')
               FROM observations GROUP BY device_id, ip_address"""
        )


def _device_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["trusted"] = bool(item["trusted"])
    item["mac_locally_administered"] = bool(item.get("mac_locally_administered", 0))
    return item


def list_devices(path: Path | None = None, query: str = "") -> list[dict[str, Any]]:
    with connect(path) as db:
        if query.strip():
            value = f"%{query.strip()}%"
            rows = db.execute(
                """SELECT * FROM devices
                   WHERE mac_address LIKE ? OR ip_address LIKE ? OR display_name LIKE ?
                     OR notes LIKE ? OR COALESCE(manufacturer, '') LIKE ?
                   ORDER BY trusted ASC, last_seen DESC""",
                (value, value, value, value, value),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM devices ORDER BY trusted ASC, last_seen DESC").fetchall()
        devices = [_device_dict(row) for row in rows]
        for device in devices:
            address_rows = db.execute(
                """SELECT ip_address, first_seen, last_seen, interface, source
                   FROM device_addresses WHERE device_id = ?
                   ORDER BY CASE WHEN instr(ip_address, ':') = 0 THEN 0 ELSE 1 END, ip_address""",
                (device["id"],),
            ).fetchall()
            device["addresses"] = [dict(address) for address in address_rows]
    return devices


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


def get_events(path: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            """SELECT e.*, d.mac_address, d.ip_address, d.display_name, d.manufacturer
               FROM events e LEFT JOIN devices d ON d.id = e.device_id
               ORDER BY e.created_at DESC, e.id DESC LIMIT ?""",
            (max(1, min(limit, 200)),),
        ).fetchall()
    return [dict(row) for row in rows]


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
        items.append(item)
    return items


def get_summary(path: Path | None = None) -> dict[str, int | str | None]:
    with connect(path) as db:
        total = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
        trusted = db.execute("SELECT COUNT(*) FROM devices WHERE trusted = 1").fetchone()[0]
        scans = db.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        last_scan = db.execute("SELECT MAX(finished_at) FROM scans").fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM events WHERE acknowledged = 0").fetchone()[0]
        addresses = db.execute("SELECT COUNT(*) FROM device_addresses").fetchone()[0]
    return {
        "devices_total": total,
        "devices_trusted": trusted,
        "devices_untrusted": int(total - trusted),
        "addresses_total": addresses,
        "scans_total": scans,
        "events_pending": pending,
        "last_scan": last_scan,
    }


def _ip_sort_key(address: str) -> tuple[int, int]:
    parsed = ip_address(address)
    return (parsed.version, int(parsed))


def _insert_event(db: sqlite3.Connection, event_type: str, severity: str, device_id: int, message: str, now: str) -> None:
    db.execute(
        "INSERT INTO events(event_type, severity, device_id, created_at, message) VALUES (?, ?, ?, ?, ?)",
        (event_type, severity, device_id, now, message),
    )


def record_scan(
    neighbors: list[Neighbor],
    errors: list[str] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Registra una lectura, múltiples IP por MAC y cambios IPv4 confirmables."""
    started = utc_now()
    errors = errors or []
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
            "INSERT INTO scans(started_at, finished_at, source, devices_found, errors_json) VALUES (?, ?, ?, ?, ?)",
            (started, started, source, len(grouped), json.dumps(errors, ensure_ascii=False)),
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


def acknowledge_event(event_id: int, path: Path | None = None) -> bool:
    with connect(path) as db:
        cursor = db.execute("UPDATE events SET acknowledged = 1 WHERE id = ?", (event_id,))
        return cursor.rowcount > 0


def export_json(path: Path | None = None) -> str:
    """Exporta inventario, direcciones e historial (no es un backup restaurable)."""
    with connect(path) as db:
        devices = [_device_dict(row) for row in db.execute("SELECT * FROM devices ORDER BY id").fetchall()]
        events = [dict(row) for row in db.execute(
            """SELECT e.*, d.mac_address, d.ip_address, d.display_name, d.manufacturer
               FROM events e LEFT JOIN devices d ON d.id = e.device_id ORDER BY e.created_at, e.id"""
        ).fetchall()]
        scans = []
        for row in db.execute("SELECT * FROM scans ORDER BY id").fetchall():
            item = dict(row)
            try:
                item["errors"] = json.loads(item.pop("errors_json"))
            except (TypeError, json.JSONDecodeError):
                item["errors"] = []
                item.pop("errors_json", None)
            scans.append(item)
        observations = [dict(row) for row in db.execute("SELECT * FROM observations ORDER BY id").fetchall()]
        addresses = [dict(row) for row in db.execute("SELECT * FROM device_addresses ORDER BY device_id, ip_address").fetchall()]
    payload = {
        "generated_at": utc_now(),
        "format": "netsentinel-data-export-v2",
        "restorable_backup": False,
        "devices": devices,
        "addresses": addresses,
        "events": events,
        "scans": scans,
        "observations": observations,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_csv(path: Path | None = None) -> str:
    rows = list_devices(path)
    buffer = io.StringIO(newline="")
    fields = [
        "id", "display_name", "ip_address", "mac_address", "manufacturer", "mac_locally_administered",
        "interface", "trusted", "first_seen", "last_seen", "notes",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
