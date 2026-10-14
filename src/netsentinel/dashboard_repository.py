"""Consulta agregada del resumen del panel.

El resumen combina indicadores de inventario y monitorización en una sola lectura.
La mezcla es intencional: el panel necesita una vista transversal, no propiedad de
un único dominio.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .database_storage import connect


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
