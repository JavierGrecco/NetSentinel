"""Conexiones, permisos del archivo y esquema SQLite de NetSentinel.

Este módulo es infraestructura compartida: no implementa consultas propias del
inventario ni de la monitorización. Las migraciones se mantienen aquí para que
cada actualización del esquema continúe siendo atómica y compatible con datos viejos.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from .config import database_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _elapsed_seconds(start: str | None, end: str | None = None) -> int | None:
    """Calcula segundos entre marcas ISO; si falta el final usa el instante actual."""
    if not start:
        return None
    try:
        start_at = datetime.fromisoformat(start)
        end_at = datetime.fromisoformat(end) if end else datetime.now(timezone.utc)
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=timezone.utc)
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        return max(0, int((end_at - start_at).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


def _ensure_private_directory(directory: Path, *, enforce_existing_final: bool = False) -> None:
    """Create missing paths privately; optionally harden a known app-owned final directory."""
    # NETSENTINEL_DATA_DIR may point to a shared/system directory. Change modes
    # only on components created here, never on a pre-existing parent such as /tmp.
    if os.name != "posix":
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        return

    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    for candidate in reversed(missing):
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            # A concurrent process may have created it. Don't chmod something
            # that this process did not create.
            if not candidate.is_dir():
                raise NotADirectoryError(f"El directorio de datos no es un directorio: {candidate}")
        else:
            try:
                os.chmod(candidate, 0o700)
            except OSError:
                # mkdir(mode=0o700) remains restrictive under a normal umask.
                pass

    if not directory.is_dir():
        raise NotADirectoryError(f"El directorio de datos no es un directorio: {directory}")

    # The default ~/.netsentinel directory is application-owned by convention.
    # It is safe to harden that known location even when it already exists;
    # custom NETSENTINEL_DATA_DIR paths are not assumed to be dedicated.
    if enforce_existing_final and not directory.is_symlink():
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass


def _harden_database_file(db_path: Path) -> None:
    """Restrict a regular SQLite file without changing a symlink target's mode."""
    if os.name != "posix":
        return

    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        # On POSIX systems without O_NOFOLLOW, prefer preserving a symlink target
        # to following it with chmod. Most supported macOS/Linux systems have it.
        if db_path.is_symlink():
            return
        try:
            os.chmod(db_path, 0o600)
        except OSError:
            pass
        return

    try:
        # Operate on an opened descriptor instead of chmod(path): O_NOFOLLOW
        # makes the final path component fail closed if it is a symlink.
        descriptor = os.open(db_path, os.O_RDONLY | nofollow)
    except OSError:
        # SQLite may intentionally use a symlink here. Do not silently change
        # permissions of its target; the operator must protect that target.
        return

    try:
        os.fchmod(descriptor, 0o600)
    except OSError:
        pass
    finally:
        os.close(descriptor)


@contextmanager


@contextmanager
def connect(path: Path | None = None, *, default_path_provider: Callable[[], Path] | None = None) -> Iterator[sqlite3.Connection]:
    """Abre una conexión transaccional y asegura que se cierre al terminar."""
    db_path = path or (default_path_provider or database_path)()
    use_default_data_directory = path is None and not os.environ.get("NETSENTINEL_DATA_DIR")
    _ensure_private_directory(db_path.parent, enforce_existing_final=use_default_data_directory)
    connection = sqlite3.connect(db_path, timeout=10)
    _harden_database_file(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize(path: Path | None = None, *, default_path_provider: Callable[[], Path] | None = None) -> None:
    """Crea el esquema y migra de forma aditiva bases de datos de v0.1."""
    with connect(path, default_path_provider=default_path_provider) as db:
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
            CREATE TABLE IF NOT EXISTS activity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                source_mode TEXT NOT NULL CHECK (source_mode IN ('router_dns', 'router_flow', 'device_agent')),
                started_at TEXT NOT NULL,
                ends_at TEXT NOT NULL,
                stopped_at TEXT,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'stopped', 'expired')),
                collector_token_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS activity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES activity_sessions(id) ON DELETE SET NULL,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                observed_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN ('dns_query', 'connection', 'tls_sni', 'app_usage', 'blocked', 'page_visit', 'search_query', 'email_metadata')),
                source TEXT NOT NULL CHECK (source IN ('router_dns', 'router_flow', 'device_agent', 'manual_import')),
                domain TEXT,
                destination_ip TEXT,
                destination_port INTEGER CHECK (destination_port BETWEEN 1 AND 65535 OR destination_port IS NULL),
                protocol TEXT CHECK (protocol IN ('tcp', 'udp', 'quic', 'icmp', 'other') OR protocol IS NULL),
                app_name TEXT,
                page_url TEXT,
                search_engine TEXT,
                search_terms TEXT,
                email_provider TEXT,
                email_from TEXT,
                email_to TEXT,
                email_subject TEXT,
                blocked INTEGER NOT NULL DEFAULT 0 CHECK (blocked IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS activity_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                retention_days INTEGER NOT NULL DEFAULT 7 CHECK (retention_days BETWEEN 1 AND 90)
            );
            INSERT OR IGNORE INTO activity_settings(id, retention_days) VALUES (1, 7);
            CREATE INDEX IF NOT EXISTS idx_monitor_checks_time ON monitor_checks(monitor_id, checked_at DESC);
            CREATE INDEX IF NOT EXISTS idx_monitor_checks_checked_at ON monitor_checks(checked_at DESC);
            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_notification_time ON notification_log(attempted_at DESC);
            CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen DESC);
            CREATE INDEX IF NOT EXISTS idx_observations_device_time ON observations(device_id, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_addresses_ip ON device_addresses(ip_address);
            CREATE INDEX IF NOT EXISTS idx_activity_sessions_device_status ON activity_sessions(device_id, status, started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_events_device_time ON activity_events(device_id, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_events_observed_at ON activity_events(observed_at DESC);
            """
        )
        # Adicionar el hash del token sin romper bases creadas en iteraciones previas de la rama.
        activity_session_columns = {row[1] for row in db.execute("PRAGMA table_info(activity_sessions)")}
        if "collector_token_hash" not in activity_session_columns:
            db.execute("ALTER TABLE activity_sessions ADD COLUMN collector_token_hash TEXT NOT NULL DEFAULT ''")
            db.execute("UPDATE activity_sessions SET status = 'expired' WHERE status = 'active'")
        # Expand the early-branch activity schema while preserving already-imported rows.
        activity_event_sql_row = db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='activity_events'"
        ).fetchone()
        activity_event_sql = (activity_event_sql_row["sql"] or "") if activity_event_sql_row else ""
        if any(event_type not in activity_event_sql for event_type in ("page_visit", "search_query", "email_metadata")):
            db.execute("DROP TABLE IF EXISTS activity_events_migrated")
            old_columns = {row[1] for row in db.execute("PRAGMA table_info(activity_events)")}
            db.execute("""
                CREATE TABLE activity_events_migrated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER REFERENCES activity_sessions(id) ON DELETE SET NULL,
                    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                    observed_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    event_type TEXT NOT NULL CHECK (event_type IN ('dns_query', 'connection', 'tls_sni', 'app_usage', 'blocked', 'page_visit', 'search_query', 'email_metadata')),
                    source TEXT NOT NULL CHECK (source IN ('router_dns', 'router_flow', 'device_agent', 'manual_import')),
                    domain TEXT,
                    destination_ip TEXT,
                    destination_port INTEGER CHECK (destination_port BETWEEN 1 AND 65535 OR destination_port IS NULL),
                    protocol TEXT CHECK (protocol IN ('tcp', 'udp', 'quic', 'icmp', 'other') OR protocol IS NULL),
                    app_name TEXT,
                    page_url TEXT,
                    search_engine TEXT,
                    search_terms TEXT,
                    email_provider TEXT,
                    email_from TEXT,
                    email_to TEXT,
                    email_subject TEXT,
                    blocked INTEGER NOT NULL DEFAULT 0 CHECK (blocked IN (0, 1))
                )
            """)
            core_columns = [
                "id", "session_id", "device_id", "observed_at", "received_at", "event_type",
                "source", "domain", "destination_ip", "destination_port", "protocol", "app_name",
            ]
            select_columns = [name if name in old_columns else "NULL" for name in core_columns]
            extra_columns = ("page_url", "search_engine", "search_terms", "email_provider", "email_from", "email_to", "email_subject")
            select_columns.extend(name if name in old_columns else "NULL" for name in extra_columns)
            select_columns.append("blocked" if "blocked" in old_columns else "0")
            target_columns = core_columns + list(extra_columns) + ["blocked"]
            db.execute(
                "INSERT INTO activity_events_migrated (" + ", ".join(target_columns) + ") "
                "SELECT " + ", ".join(select_columns) + " FROM activity_events"
            )
            db.execute("DROP TABLE activity_events")
            db.execute("ALTER TABLE activity_events_migrated RENAME TO activity_events")
        else:
            activity_columns = {row[1] for row in db.execute("PRAGMA table_info(activity_events)")}
            for column in ("page_url", "search_engine", "search_terms", "email_provider", "email_from", "email_to", "email_subject"):
                if column not in activity_columns:
                    db.execute(f"ALTER TABLE activity_events ADD COLUMN {column} TEXT")
        db.execute("CREATE INDEX IF NOT EXISTS idx_activity_events_device_time ON activity_events(device_id, observed_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_activity_events_observed_at ON activity_events(observed_at DESC)")
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
