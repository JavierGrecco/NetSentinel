"""Exportaciones de datos y copia consistente de SQLite.

Los formatos de exportación son una capacidad transversal del producto. Este módulo
reúne datos de varios dominios sin cambiar quién es responsable de su escritura.
La copia restaurable se genera con la API de backup de SQLite, no copiando el archivo
en bruto mientras puede haber transacciones activas.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Callable

from .config import database_path
from .csv_safety import spreadsheet_safe_text
from .database_storage import connect, utc_now
from .inventory_repository import _device_dict, list_devices


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
        activity_sessions = [dict(row) for row in db.execute(
            "SELECT id, device_id, source_mode, started_at, ends_at, stopped_at, status FROM activity_sessions ORDER BY id"
        ).fetchall()]
        activity_events = [dict(row) for row in db.execute("SELECT * FROM activity_events ORDER BY id").fetchall()]
        activity_settings = [dict(row) for row in db.execute("SELECT * FROM activity_settings ORDER BY id").fetchall()]
    payload = {
        "generated_at": utc_now(),
        "format": "netsentinel-data-export-v4",
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
        "activity_sessions": activity_sessions,
        "activity_events": activity_events,
        "activity_settings": activity_settings,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def export_sqlite_backup(path: Path | None = None, *, default_path_provider: Callable[[], Path] | None = None) -> bytes:
    """Crea una copia SQLite consistente mientras la aplicación sigue en uso.

    Usa la API de backup de SQLite para incluir transacciones confirmadas aunque
    la base de datos use WAL; el archivo temporal se elimina al retornar.
    """
    source_path = path or (default_path_provider or database_path)()
    if not source_path.is_file():
        raise FileNotFoundError("No existe la base de datos de NetSentinel para respaldar.")

    with tempfile.TemporaryDirectory(prefix="netsentinel-backup-") as temporary_directory:
        backup_path = Path(temporary_directory) / "netsentinel-backup.sqlite3"
        source = sqlite3.connect(source_path, timeout=10)
        try:
            # Si no se puede abrir el destino temporal, cerrar igualmente el origen.
            # El try exterior protege también los errores al crear el destino.
            destination = sqlite3.connect(backup_path, timeout=10)
            try:
                source.backup(destination)
                destination.commit()
            finally:
                destination.close()
        finally:
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
    writer.writerows(
        {key: spreadsheet_safe_text(value) for key, value in row.items()}
        for row in rows
    )
    # Excel on Windows recognizes UTF-8 reliably when the CSV has a BOM.
    return "\ufeff" + buffer.getvalue()



# --- Monitorización periódica e incidentes (v0.3) ---------------------------
