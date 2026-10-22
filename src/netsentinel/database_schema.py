"""Esquema y migraciones aditivas de SQLite de NetSentinel.

Todas las migraciones se ejecutan en una única transacción a través de la fábrica de
conexión compartida. No contiene consultas de inventario ni reglas de monitorización.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .database_storage import connect
from .forensics_audit_integrity import audit_event_hash


def initialize(path: Path | None = None, *, default_path_provider: Callable[[], Path] | None = None) -> None:
    """Crea el esquema y migra de forma aditiva bases de datos de v0.1."""
    with connect(path, default_path_provider=default_path_provider) as db:
        db.executescript(
            """
            BEGIN IMMEDIATE;
            -- Incluye el esquema inicial y las migraciones siguientes en la misma transacción.
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
                source_event_id TEXT,
                domain TEXT,
                source_ip TEXT,
                source_port INTEGER CHECK (source_port BETWEEN 1 AND 65535 OR source_port IS NULL),
                destination_ip TEXT,
                destination_port INTEGER CHECK (destination_port BETWEEN 1 AND 65535 OR destination_port IS NULL),
                protocol TEXT CHECK (protocol IN ('tcp', 'udp', 'quic', 'icmp', 'other') OR protocol IS NULL),
                bytes_sent INTEGER CHECK (bytes_sent BETWEEN 0 AND 9223372036854775807 OR bytes_sent IS NULL),
                bytes_received INTEGER CHECK (bytes_received BETWEEN 0 AND 9223372036854775807 OR bytes_received IS NULL),
                packets_sent INTEGER CHECK (packets_sent BETWEEN 0 AND 9223372036854775807 OR packets_sent IS NULL),
                packets_received INTEGER CHECK (packets_received BETWEEN 0 AND 9223372036854775807 OR packets_received IS NULL),
                network_interface TEXT,
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
                    source_event_id TEXT,
                    domain TEXT,
                    source_ip TEXT,
                    source_port INTEGER CHECK (source_port BETWEEN 1 AND 65535 OR source_port IS NULL),
                    destination_ip TEXT,
                    destination_port INTEGER CHECK (destination_port BETWEEN 1 AND 65535 OR destination_port IS NULL),
                    protocol TEXT CHECK (protocol IN ('tcp', 'udp', 'quic', 'icmp', 'other') OR protocol IS NULL),
                    bytes_sent INTEGER CHECK (bytes_sent BETWEEN 0 AND 9223372036854775807 OR bytes_sent IS NULL),
                    bytes_received INTEGER CHECK (bytes_received BETWEEN 0 AND 9223372036854775807 OR bytes_received IS NULL),
                    packets_sent INTEGER CHECK (packets_sent BETWEEN 0 AND 9223372036854775807 OR packets_sent IS NULL),
                    packets_received INTEGER CHECK (packets_received BETWEEN 0 AND 9223372036854775807 OR packets_received IS NULL),
                    network_interface TEXT,
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
                "source", "source_event_id", "domain", "source_ip", "source_port",
                "destination_ip", "destination_port", "protocol", "bytes_sent", "bytes_received",
                "packets_sent", "packets_received", "network_interface", "app_name",
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
            column_definitions = {
                "page_url": "TEXT",
                "search_engine": "TEXT",
                "search_terms": "TEXT",
                "email_provider": "TEXT",
                "email_from": "TEXT",
                "email_to": "TEXT",
                "email_subject": "TEXT",
                "source_event_id": "TEXT",
                "source_ip": "TEXT",
                "source_port": "INTEGER CHECK (source_port BETWEEN 1 AND 65535 OR source_port IS NULL)",
                "bytes_sent": "INTEGER CHECK (bytes_sent BETWEEN 0 AND 9223372036854775807 OR bytes_sent IS NULL)",
                "bytes_received": "INTEGER CHECK (bytes_received BETWEEN 0 AND 9223372036854775807 OR bytes_received IS NULL)",
                "packets_sent": "INTEGER CHECK (packets_sent BETWEEN 0 AND 9223372036854775807 OR packets_sent IS NULL)",
                "packets_received": "INTEGER CHECK (packets_received BETWEEN 0 AND 9223372036854775807 OR packets_received IS NULL)",
                "network_interface": "TEXT",
            }
            for column, definition in column_definitions.items():
                if column not in activity_columns:
                    db.execute(f"ALTER TABLE activity_events ADD COLUMN {column} {definition}")
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

        # Tablas forenses aditivas: no modifican las tablas ni los datos de Red.
        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_cases (
                id TEXT PRIMARY KEY,
                case_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                authority_reference TEXT NOT NULL,
                objective TEXT NOT NULL,
                scope TEXT NOT NULL,
                examiner TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES forensic_cases(id) ON DELETE RESTRICT,
                evidence_number TEXT NOT NULL,
                label TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK (
                    source_type IN ('disk_image', 'file_copy', 'browser_export', 'email_export', 'network_log', 'other')
                ),
                original_name TEXT,
                source_description TEXT NOT NULL,
                received_from TEXT NOT NULL,
                received_by TEXT NOT NULL,
                received_at_original TEXT NOT NULL,
                received_timezone TEXT NOT NULL,
                size_bytes INTEGER CHECK (size_bytes >= 0 OR size_bytes IS NULL),
                reported_sha256 TEXT,
                hash_source TEXT,
                created_at TEXT NOT NULL,
                UNIQUE (case_id, evidence_number),
                CHECK (reported_sha256 IS NULL OR length(reported_sha256) = 64)
            )
        """)
        # Migración aditiva: las recepciones antiguas no identificaban a la
        # persona que quedó a cargo. Un valor vacío significa "no registrado"; no
        # inferimos esa identidad a partir del operador ni de la fuente que entrega.
        evidence_columns = {
            str(row["name"]) for row in db.execute("PRAGMA table_info(forensic_evidence)")
        }
        if "received_by" not in evidence_columns:
            db.execute(
                "ALTER TABLE forensic_evidence ADD COLUMN received_by TEXT NOT NULL DEFAULT ''"
            )

        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_integrity_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES forensic_cases(id) ON DELETE RESTRICT,
                evidence_id TEXT NOT NULL REFERENCES forensic_evidence(id) ON DELETE RESTRICT,
                checked_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                copy_confirmed INTEGER NOT NULL DEFAULT 1 CHECK (copy_confirmed = 1),
                algorithm TEXT NOT NULL CHECK (algorithm = 'SHA-256'),
                source_name TEXT NOT NULL,
                expected_sha256 TEXT,
                calculated_sha256 TEXT,
                size_bytes INTEGER CHECK (size_bytes >= 0 OR size_bytes IS NULL),
                status TEXT NOT NULL CHECK (status IN ('match', 'mismatch', 'failed')),
                tool_version TEXT NOT NULL,
                error_code TEXT,
                error_message TEXT,
                CHECK (expected_sha256 IS NULL OR length(expected_sha256) = 64),
                CHECK (calculated_sha256 IS NULL OR length(calculated_sha256) = 64)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES forensic_cases(id) ON DELETE RESTRICT,
                evidence_id TEXT REFERENCES forensic_evidence(id) ON DELETE RESTRICT,
                occurred_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # Crear y rellenar la cadena solo durante la migración inicial. Si en una base
        # ya migrada faltan filas de cadena, no las reconstruimos en cada arranque:
        # la consulta debe poder señalar ese faltante como una posible alteración.
        audit_chain_exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'forensic_audit_chain'"
        ).fetchone() is not None
        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_audit_chain (
                audit_id INTEGER PRIMARY KEY REFERENCES forensic_audit(id) ON DELETE RESTRICT,
                case_id TEXT NOT NULL REFERENCES forensic_cases(id) ON DELETE RESTRICT,
                previous_hash TEXT CHECK (previous_hash IS NULL OR length(previous_hash) = 64),
                event_hash TEXT NOT NULL CHECK (length(event_hash) = 64)
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_forensic_audit_chain_case ON forensic_audit_chain(case_id, audit_id)"
        )
        if not audit_chain_exists:
            legacy_case_ids = db.execute(
                "SELECT DISTINCT case_id FROM forensic_audit ORDER BY case_id"
            ).fetchall()
            for legacy_case in legacy_case_ids:
                previous_hash = None
                legacy_events = db.execute(
                    """SELECT id, case_id, evidence_id, occurred_at, actor, action, result, details_json
                       FROM forensic_audit WHERE case_id = ? ORDER BY id ASC""",
                    (legacy_case["case_id"],),
                ).fetchall()
                for event in legacy_events:
                    event_hash = audit_event_hash(
                        case_id=event["case_id"],
                        evidence_id=event["evidence_id"],
                        occurred_at=event["occurred_at"],
                        actor=event["actor"],
                        action=event["action"],
                        result=event["result"],
                        details_json=event["details_json"],
                        previous_hash=previous_hash,
                    )
                    db.execute(
                        """INSERT INTO forensic_audit_chain
                           (audit_id, case_id, previous_hash, event_hash)
                           VALUES (?, ?, ?, ?)""",
                        (event["id"], event["case_id"], previous_hash, event_hash),
                    )
                    previous_hash = event_hash
        db.execute("CREATE INDEX IF NOT EXISTS idx_forensic_cases_updated ON forensic_cases(updated_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_forensic_evidence_case ON forensic_evidence(case_id, created_at)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_forensic_integrity_evidence_time ON forensic_integrity_checks(evidence_id, checked_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_forensic_audit_case_time ON forensic_audit(case_id, occurred_at DESC)")
        # Las verificaciones de integridad también conservan su historial original.
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_integrity_no_update
            BEFORE UPDATE ON forensic_integrity_checks
            BEGIN SELECT RAISE(ABORT, 'forensic integrity history is append-only'); END
        """)
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_integrity_no_delete
            BEFORE DELETE ON forensic_integrity_checks
            BEGIN SELECT RAISE(ABORT, 'forensic integrity history is append-only'); END
        """)
        # El historial de auditoría es de solo anexado desde la app y la propia base.
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_audit_no_update
            BEFORE UPDATE ON forensic_audit
            BEGIN SELECT RAISE(ABORT, 'forensic audit is append-only'); END
        """)
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_audit_no_delete
            BEFORE DELETE ON forensic_audit
            BEGIN SELECT RAISE(ABORT, 'forensic audit is append-only'); END
        """)
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_audit_chain_no_update
            BEFORE UPDATE ON forensic_audit_chain
            BEGIN SELECT RAISE(ABORT, 'forensic audit chain is append-only'); END
        """)
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_audit_chain_no_delete
            BEFORE DELETE ON forensic_audit_chain
            BEGIN SELECT RAISE(ABORT, 'forensic audit chain is append-only'); END
        """)

        # Los informes se versionan como documentos inmutables. Una corrección crea
        # una fila nueva que referencia la versión anterior; no se reemplaza el informe.
        db.execute("""
            CREATE TABLE IF NOT EXISTS forensic_reports (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES forensic_cases(id) ON DELETE RESTRICT,
                report_version INTEGER NOT NULL CHECK (report_version >= 1),
                amends_report_id TEXT REFERENCES forensic_reports(id) ON DELETE RESTRICT,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status = 'draft_unsigned'),
                report_sha256 TEXT NOT NULL CHECK (length(report_sha256) = 64),
                report_json TEXT NOT NULL,
                UNIQUE (case_id, report_version)
            )
        """)
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_forensic_reports_case_version "
            "ON forensic_reports(case_id, report_version DESC)"
        )
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_reports_no_update
            BEFORE UPDATE ON forensic_reports
            BEGIN SELECT RAISE(ABORT, 'forensic reports are append-only'); END
        """)
        db.execute("""
            CREATE TRIGGER IF NOT EXISTS forensic_reports_no_delete
            BEFORE DELETE ON forensic_reports
            BEGIN SELECT RAISE(ABORT, 'forensic reports are append-only'); END
        """)
