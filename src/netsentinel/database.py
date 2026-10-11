"""Persistencia SQLite, inventario, direcciones por dispositivo e historial."""

from __future__ import annotations

import csv
import io
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
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
                errors_json TEXT NOT NULL DEFAULT '[]',
                discovery_json TEXT NOT NULL DEFAULT '{}'
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
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('ping', 'tcp', 'http')),
                target TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL CHECK (interval_seconds BETWEEN 15 AND 86400),
                timeout_seconds INTEGER NOT NULL CHECK (timeout_seconds BETWEEN 1 AND 10),
                enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_checked_at TEXT,
                last_status TEXT CHECK (last_status IN ('up', 'down') OR last_status IS NULL)
            );
            CREATE TABLE IF NOT EXISTS monitor_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                checked_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('up', 'down')),
                latency_ms REAL,
                detail TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
                opened_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                failure_count INTEGER NOT NULL DEFAULT 1,
                last_detail TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_one_open_per_monitor
                ON incidents(monitor_id) WHERE status = 'open';
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monitor_id INTEGER NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
                incident_id INTEGER REFERENCES incidents(id) ON DELETE SET NULL,
                event_type TEXT NOT NULL,
                attempted_at TEXT NOT NULL,
                success INTEGER NOT NULL CHECK (success IN (0, 1)),
                detail TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_monitor_checks_time ON monitor_checks(monitor_id, checked_at DESC);
            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notification_time ON notification_log(attempted_at DESC);
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
        scan_columns = {row[1] for row in db.execute("PRAGMA table_info(scans)")}
        if "discovery_json" not in scan_columns:
            db.execute("ALTER TABLE scans ADD COLUMN discovery_json TEXT NOT NULL DEFAULT '{}'")
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
        try:
            report = json.loads(item.pop("discovery_json"))
            item["discovery"] = report if isinstance(report, dict) else {}
        except (TypeError, json.JSONDecodeError):
            item["discovery"] = {}
            item.pop("discovery_json", None)
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
        monitors_total = db.execute("SELECT COUNT(*) FROM monitors").fetchone()[0]
        monitors_enabled = db.execute("SELECT COUNT(*) FROM monitors WHERE enabled = 1").fetchone()[0]
        incidents_open = db.execute("SELECT COUNT(*) FROM incidents WHERE status = 'open'").fetchone()[0]
    return {
        "devices_total": total,
        "devices_trusted": trusted,
        "devices_untrusted": int(total - trusted),
        "addresses_total": addresses,
        "scans_total": scans,
        "events_pending": pending,
        "last_scan": last_scan,
        "monitors_total": monitors_total,
        "monitors_enabled": monitors_enabled,
        "incidents_open": incidents_open,
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


def acknowledge_event(event_id: int, path: Path | None = None) -> bool:
    with connect(path) as db:
        cursor = db.execute("UPDATE events SET acknowledged = 1 WHERE id = ?", (event_id,))
        return cursor.rowcount > 0


def export_json(path: Path | None = None) -> str:
    """Exporta inventario e historial, incluida la monitorización (no es backup restaurable)."""
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
            try:
                report = json.loads(item.pop("discovery_json"))
                item["discovery"] = report if isinstance(report, dict) else {}
            except (TypeError, json.JSONDecodeError):
                item["discovery"] = {}
                item.pop("discovery_json", None)
            scans.append(item)
        observations = [dict(row) for row in db.execute("SELECT * FROM observations ORDER BY id").fetchall()]
        addresses = [dict(row) for row in db.execute("SELECT * FROM device_addresses ORDER BY device_id, ip_address").fetchall()]
        monitors = [dict(row) for row in db.execute("SELECT * FROM monitors ORDER BY id").fetchall()]
        monitor_checks = [dict(row) for row in db.execute("SELECT * FROM monitor_checks ORDER BY id").fetchall()]
        incidents = [dict(row) for row in db.execute("SELECT * FROM incidents ORDER BY id").fetchall()]
        notifications = [dict(row) for row in db.execute("SELECT * FROM notification_log ORDER BY id").fetchall()]
    payload = {
        "generated_at": utc_now(),
        "format": "netsentinel-data-export-v3",
        "restorable_backup": False,
        "devices": devices,
        "addresses": addresses,
        "events": events,
        "scans": scans,
        "observations": observations,
        "monitors": monitors,
        "monitor_checks": monitor_checks,
        "incidents": incidents,
        "notification_log": notifications,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_sqlite_backup(path: Path | None = None) -> bytes:
    """Crea una copia SQLite consistente mientras la aplicación sigue en uso.

    Usa la API de backup de SQLite para incluir transacciones confirmadas aunque
    la base de datos use WAL; el archivo temporal se elimina al retornar.
    """
    source_path = path or database_path()
    if not source_path.is_file():
        raise FileNotFoundError("No existe la base de datos de NetSentinel para respaldar.")

    with tempfile.TemporaryDirectory(prefix="netsentinel-backup-") as temporary_directory:
        backup_path = Path(temporary_directory) / "netsentinel-backup.sqlite3"
        source = sqlite3.connect(source_path, timeout=10)
        destination = sqlite3.connect(backup_path, timeout=10)
        try:
            source.backup(destination)
            destination.commit()
        finally:
            destination.close()
            source.close()
        return backup_path.read_bytes()


def export_csv(path: Path | None = None) -> str:
    """Exporta el inventario y todas las direcciones conocidas en un CSV legible."""
    rows = list_devices(path)
    buffer = io.StringIO(newline="")
    fields = [
        "id", "display_name", "ip_address", "addresses", "address_count",
        "mac_address", "manufacturer", "mac_locally_administered",
        "interface", "trusted", "first_seen", "last_seen", "notes",
    ]
    for device in rows:
        addresses = device.get("addresses") or []
        device["address_count"] = len(addresses)
        device["addresses"] = "; ".join(
            f"{item['ip_address']} [interfaz: {item.get('interface') or '—'}; origen: {item.get('source') or '—'}]"
            for item in addresses
        )
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    # Excel on Windows recognizes UTF-8 reliably when the CSV has a BOM.
    return "\ufeff" + buffer.getvalue()



# --- Monitorización periódica e incidentes (v0.3) ---------------------------

def create_monitor(
    name: str, kind: str, target: str, interval_seconds: int = 60,
    timeout_seconds: int = 3, path: Path | None = None,
) -> dict[str, Any]:
    now = utc_now()
    name = name.strip()[:120]
    if not name:
        raise ValueError("El nombre del monitor no puede estar vacío.")
    if kind not in {"ping", "tcp", "http"}:
        raise ValueError("Tipo de monitor no admitido.")
    if not 15 <= int(interval_seconds) <= 86400:
        raise ValueError("El intervalo debe estar entre 15 y 86400 segundos.")
    if not 1 <= int(timeout_seconds) <= 10:
        raise ValueError("El tiempo límite debe estar entre 1 y 10 segundos.")
    with connect(path) as db:
        cursor = db.execute(
            """INSERT INTO monitors(name, kind, target, interval_seconds, timeout_seconds, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
            (name, kind, target.strip(), int(interval_seconds), int(timeout_seconds), now, now),
        )
        monitor_id = int(cursor.lastrowid)
    result = next((item for item in list_monitors(path) if item["id"] == monitor_id), None)
    if result is None:
        raise RuntimeError("No se pudo recuperar el monitor recién creado.")
    return result


def list_monitors(path: Path | None = None) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            """SELECT m.*,
                      (SELECT c.latency_ms FROM monitor_checks c WHERE c.monitor_id = m.id ORDER BY c.id DESC LIMIT 1) AS last_latency_ms,
                      (SELECT c.detail FROM monitor_checks c WHERE c.monitor_id = m.id ORDER BY c.id DESC LIMIT 1) AS last_detail,
                      (SELECT i.id FROM incidents i WHERE i.monitor_id = m.id AND i.status = 'open' ORDER BY i.id DESC LIMIT 1) AS open_incident_id,
                      (SELECT COUNT(*) FROM monitor_checks c WHERE c.monitor_id = m.id) AS checks_count
               FROM monitors m ORDER BY m.enabled DESC, m.name COLLATE NOCASE"""
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["enabled"] = bool(item["enabled"])
        item["incident_open"] = item["open_incident_id"] is not None
    return items


def get_monitor_checks(monitor_id: int, limit: int = 30, path: Path | None = None) -> list[dict[str, Any]] | None:
    with connect(path) as db:
        if db.execute("SELECT 1 FROM monitors WHERE id = ?", (monitor_id,)).fetchone() is None:
            return None
        rows = db.execute(
            "SELECT * FROM monitor_checks WHERE monitor_id = ? ORDER BY id DESC LIMIT ?",
            (monitor_id, max(1, min(int(limit), 200))),
        ).fetchall()
    return [dict(row) for row in rows]


def get_monitor_analytics(window_hours: int = 24, path: Path | None = None) -> dict[str, Any]:
    """Resume comprobaciones por monitor en una ventana reciente sin alterar el historial."""
    hours = max(1, min(int(window_hours), 168))
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")
    with connect(path) as db:
        totals = db.execute(
            """SELECT COUNT(*) AS checks_total,
                      COALESCE(SUM(CASE WHEN status = 'up' THEN 1 ELSE 0 END), 0) AS checks_up,
                      COALESCE(SUM(CASE WHEN status = 'down' THEN 1 ELSE 0 END), 0) AS checks_down,
                      AVG(CASE WHEN status = 'up' THEN latency_ms END) AS average_latency_ms
               FROM monitor_checks WHERE checked_at >= ?""",
            (since,),
        ).fetchone()
        monitor_rows = db.execute(
            """SELECT m.id AS monitor_id, m.name, m.enabled,
                      COUNT(c.id) AS checks_total,
                      COALESCE(SUM(CASE WHEN c.status = 'up' THEN 1 ELSE 0 END), 0) AS checks_up,
                      COALESCE(SUM(CASE WHEN c.status = 'down' THEN 1 ELSE 0 END), 0) AS checks_down,
                      AVG(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS average_latency_ms,
                      MIN(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS min_latency_ms,
                      MAX(CASE WHEN c.status = 'up' THEN c.latency_ms END) AS max_latency_ms
               FROM monitors m
               LEFT JOIN monitor_checks c
                 ON c.monitor_id = m.id AND c.checked_at >= ?
               GROUP BY m.id
               ORDER BY m.enabled DESC, m.name COLLATE NOCASE""",
            (since,),
        ).fetchall()
        monitors_total = db.execute("SELECT COUNT(*) FROM monitors").fetchone()[0]
        monitors_enabled = db.execute("SELECT COUNT(*) FROM monitors WHERE enabled = 1").fetchone()[0]
        incidents_open = db.execute("SELECT COUNT(*) FROM incidents WHERE status = 'open'").fetchone()[0]

    checks_total = int(totals["checks_total"] or 0)
    checks_up = int(totals["checks_up"] or 0)
    checks_down = int(totals["checks_down"] or 0)
    summary = {
        "checks_total": checks_total,
        "checks_up": checks_up,
        "checks_down": checks_down,
        "success_rate_percent": round(checks_up / checks_total * 100, 2) if checks_total else None,
        "average_latency_ms": round(float(totals["average_latency_ms"]), 2)
        if totals["average_latency_ms"] is not None else None,
        "monitors_total": int(monitors_total),
        "monitors_enabled": int(monitors_enabled),
        "incidents_open": int(incidents_open),
    }
    monitor_stats = []
    for row in monitor_rows:
        item = dict(row)
        total = int(item["checks_total"] or 0)
        up = int(item["checks_up"] or 0)
        item["enabled"] = bool(item["enabled"])
        item["success_rate_percent"] = round(up / total * 100, 2) if total else None
        for field in ("average_latency_ms", "min_latency_ms", "max_latency_ms"):
            item[field] = round(float(item[field]), 2) if item[field] is not None else None
        monitor_stats.append(item)

    return {
        "window_hours": hours,
        "since": since,
        "summary": summary,
        "monitors": monitor_stats,
    }


def update_monitor(monitor_id: int, *, enabled: bool | None = None, name: str | None = None,
                   interval_seconds: int | None = None, timeout_seconds: int | None = None,
                   path: Path | None = None) -> dict[str, Any] | None:
    with connect(path) as db:
        row = db.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        if row is None:
            return None
        new_enabled = int(enabled) if enabled is not None else row["enabled"]
        new_name = name.strip()[:120] if name is not None else row["name"]
        new_interval = int(interval_seconds) if interval_seconds is not None else row["interval_seconds"]
        new_timeout = int(timeout_seconds) if timeout_seconds is not None else row["timeout_seconds"]
        if not new_name:
            raise ValueError("El nombre del monitor no puede estar vacío.")
        if not 15 <= new_interval <= 86400:
            raise ValueError("El intervalo debe estar entre 15 y 86400 segundos.")
        if not 1 <= new_timeout <= 10:
            raise ValueError("El tiempo límite debe estar entre 1 y 10 segundos.")
        db.execute(
            "UPDATE monitors SET name = ?, enabled = ?, interval_seconds = ?, timeout_seconds = ?, updated_at = ? WHERE id = ?",
            (new_name, new_enabled, new_interval, new_timeout, utc_now(), monitor_id),
        )
    return next((item for item in list_monitors(path) if item["id"] == monitor_id), None)


def delete_monitor(monitor_id: int, path: Path | None = None) -> bool:
    with connect(path) as db:
        cursor = db.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
        return cursor.rowcount > 0


def get_incidents(path: Path | None = None, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = ""
    if status in {"open", "resolved"}:
        where = "WHERE i.status = ?"
        params.append(status)
    params.append(max(1, min(int(limit), 200)))
    with connect(path) as db:
        rows = db.execute(
            f"""SELECT i.*, m.name AS monitor_name, m.kind, m.target
                FROM incidents i JOIN monitors m ON m.id = i.monitor_id
                {where} ORDER BY CASE WHEN i.status = 'open' THEN 0 ELSE 1 END, i.updated_at DESC, i.id DESC LIMIT ?""",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def record_monitor_check(monitor_id: int, status: str, latency_ms: float | None,
                         detail: str, path: Path | None = None) -> dict[str, Any]:
    if status not in {"up", "down"}:
        raise ValueError("El estado del control debe ser up o down.")
    now = utc_now()
    transition: dict[str, Any] | None = None
    with connect(path) as db:
        monitor = db.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,)).fetchone()
        if monitor is None:
            raise ValueError("El monitor ya no existe.")
        db.execute(
            "INSERT INTO monitor_checks(monitor_id, checked_at, status, latency_ms, detail) VALUES (?, ?, ?, ?, ?)",
            (monitor_id, now, status, latency_ms, detail[:1000]),
        )
        db.execute(
            "UPDATE monitors SET last_checked_at = ?, last_status = ?, updated_at = ? WHERE id = ?",
            (now, status, now, monitor_id),
        )
        open_incident = db.execute(
            "SELECT * FROM incidents WHERE monitor_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
            (monitor_id,),
        ).fetchone()
        if status == "down":
            if open_incident is None:
                cursor = db.execute(
                    """INSERT INTO incidents(monitor_id, status, opened_at, updated_at, failure_count, last_detail)
                       VALUES (?, 'open', ?, ?, 1, ?)""",
                    (monitor_id, now, now, detail[:1000]),
                )
                incident_id = int(cursor.lastrowid)
                message = f"El monitor '{monitor['name']}' no responde: {detail[:500]}"
                _insert_event(db, "monitor_down", "warning", None, message, now)
                transition = {"transition": "down", "incident_id": incident_id, "monitor_name": monitor["name"],
                              "target": monitor["target"], "message": message, "at": now}
            else:
                incident_id = int(open_incident["id"])
                db.execute(
                    "UPDATE incidents SET updated_at = ?, failure_count = failure_count + 1, last_detail = ? WHERE id = ?",
                    (now, detail[:1000], incident_id),
                )
        elif open_incident is not None:
            incident_id = int(open_incident["id"])
            db.execute(
                "UPDATE incidents SET status = 'resolved', updated_at = ?, resolved_at = ?, last_detail = ? WHERE id = ?",
                (now, now, detail[:1000], incident_id),
            )
            message = f"El monitor '{monitor['name']}' se recuperó. {detail[:500]}"
            _insert_event(db, "monitor_recovered", "info", None, message, now)
            transition = {"transition": "recovered", "incident_id": incident_id, "monitor_name": monitor["name"],
                          "target": monitor["target"], "message": message, "at": now}
        check = db.execute("SELECT * FROM monitor_checks WHERE monitor_id = ? ORDER BY id DESC LIMIT 1", (monitor_id,)).fetchone()
    return {"check": dict(check), "transition": transition}


def record_notification(monitor_id: int, incident_id: int | None, event_type: str,
                        success: bool, detail: str, path: Path | None = None) -> None:
    with connect(path) as db:
        db.execute(
            """INSERT INTO notification_log(monitor_id, incident_id, event_type, attempted_at, success, detail)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (monitor_id, incident_id, event_type, utc_now(), int(success), detail[:500]),
        )


def get_notification_log(path: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with connect(path) as db:
        rows = db.execute(
            """SELECT n.*, m.name AS monitor_name FROM notification_log n
               JOIN monitors m ON m.id = n.monitor_id ORDER BY n.id DESC LIMIT ?""",
            (max(1, min(int(limit), 200)),),
        ).fetchall()
    return [dict(row) for row in rows]
