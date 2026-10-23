import csv
import io
from pathlib import Path

import pytest

from netsentinel import database
from netsentinel.discovery import Neighbor


def test_new_device_creates_single_event_and_persists_history(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    neighbor = Neighbor("192.168.10.10", "AA:BB:CC:DD:EE:FF", "eth0")

    first = database.record_scan([neighbor], path=db)
    assert first["devices_found"] == 1
    assert first["new_devices"] == 1
    assert database.get_summary(db)["devices_untrusted"] == 1
    assert len(database.get_events(db)) == 1

    second = database.record_scan([neighbor], path=db)
    assert second["new_devices"] == 0
    assert len(database.get_events(db)) == 1
    assert database.get_summary(db)["scans_total"] == 2


def test_trust_update_and_exports(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    database.record_scan([Neighbor("192.168.10.11", "11:22:33:44:55:66", "wlan0")], path=db)
    device = database.list_devices(db)[0]

    updated = database.update_device(device["id"], trusted=True, display_name="Mi portátil", path=db)
    assert updated is not None
    assert updated["trusted"] is True
    assert updated["display_name"] == "Mi portátil"
    assert database.get_summary(db)["devices_trusted"] == 1
    # CSV should contain the full observed address list, not just the primary IP.
    database.record_scan([
        Neighbor("192.168.10.11", "11:22:33:44:55:66", "wlan0"),
        Neighbor("fe80::1", "11:22:33:44:55:66", "wlan0", "ndp"),
    ], path=db)
    csv_text = database.export_csv(db)
    assert csv_text.startswith("\ufeff")
    csv_rows = list(__import__("csv").DictReader(__import__("io").StringIO(csv_text.lstrip("\ufeff"))))
    csv_device = next(item for item in csv_rows if item["mac_address"] == "11:22:33:44:55:66")
    assert "Mi portátil" in database.export_csv(db)
    assert csv_device["address_count"] == "2"
    assert "192.168.10.11" in csv_device["addresses"]
    assert "fe80::1" in csv_device["addresses"]
    export = __import__("json").loads(database.export_json(db))
    assert export["restorable_backup"] is False
    assert export["devices"][0]["display_name"] == "Mi portátil"
    assert len(export["scans"]) == 2
    assert len(export["observations"]) == 3


def test_inventory_csv_neutralizes_formula_cells_without_mutating_database(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    database.record_scan(
        [Neighbor("192.168.10.21", "AA:BB:CC:DD:EE:22", "eth0")],
        path=db,
    )
    device = database.list_devices(db)[0]
    formula_name = '=HYPERLINK("https://example.invalid","open")'
    formula_notes = "+SUM(1,1)"

    updated = database.update_device(
        device["id"],
        display_name=formula_name,
        notes=formula_notes,
        path=db,
    )
    assert updated is not None
    assert updated["display_name"] == formula_name
    assert updated["notes"] == formula_notes

    csv_text = database.export_csv(db)
    rows = list(csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff"))))
    exported = next(item for item in rows if item["id"] == str(device["id"]))
    assert exported["display_name"] == "'" + formula_name
    assert exported["notes"] == "'" + formula_notes

    # Protection belongs to the exported representation; stored values remain intact.
    stored = database.list_devices(db)[0]
    assert stored["display_name"] == formula_name
    assert stored["notes"] == formula_notes


def test_sqlite_backup_is_consistent_and_contains_history(tmp_path: Path):
    import sqlite3

    source = tmp_path / "netsentinel.sqlite3"
    database.initialize(source)
    database.record_scan(
        [Neighbor("192.168.22.4", "AA:BB:CC:DD:EE:11", "en0")],
        path=source,
    )
    monitor = database.create_monitor(
        "Respaldo de prueba", "tcp", "127.0.0.1:9", 60, 2, path=source
    )
    database.record_monitor_check(
        monitor["id"], "down", None, "Fallo de prueba", path=source
    )
    backup_path = tmp_path / "backup.sqlite3"
    backup_path.write_bytes(database.export_sqlite_backup(source))

    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT mac_address FROM devices").fetchone()[0] == "AA:BB:CC:DD:EE:11"
        assert backup.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 1
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    # Simulate restoring the downloaded backup without touching the source database.
    restored_path = tmp_path / "restored.sqlite3"
    restored_path.write_bytes(backup_path.read_bytes())

    # Starting NetSentinel initializes an existing database, so verify both
    # schema compatibility and the application reads after restoration.
    database.initialize(restored_path)
    restored_devices = database.list_devices(restored_path)
    assert len(restored_devices) == 1
    restored_device = restored_devices[0]
    assert restored_device["mac_address"] == "AA:BB:CC:DD:EE:11"
    assert "192.168.22.4" in {
        address["ip_address"] for address in restored_device["addresses"]
    }

    restored_history = database.get_device_history(restored_device["id"], path=restored_path)
    assert restored_history is not None
    assert restored_history["count"] == 1
    assert restored_history["observations"][0]["ip_address"] == "192.168.22.4"

    restored_scans = database.get_scans(path=restored_path)
    assert len(restored_scans) == 1
    assert restored_scans[0]["devices_found"] == 1

    # Monitoring state is related data too: checks, incidents and events must
    # remain consistent after a backup is restored and initialized.
    restored_monitors = database.list_monitors(path=restored_path)
    assert len(restored_monitors) == 1
    restored_monitor = restored_monitors[0]
    assert restored_monitor["name"] == "Respaldo de prueba"
    assert restored_monitor["last_status"] == "down"

    restored_checks = database.get_monitor_checks(
        restored_monitor["id"], path=restored_path
    )
    assert len(restored_checks) == 1
    assert restored_checks[0]["status"] == "down"
    assert restored_checks[0]["detail"] == "Fallo de prueba"

    restored_incidents = database.get_incidents(path=restored_path, limit=10)
    assert len(restored_incidents) == 1
    assert restored_incidents[0]["monitor_id"] == restored_monitor["id"]
    assert restored_incidents[0]["status"] == "open"
    assert restored_incidents[0]["failure_count"] == 1

    restored_event_types = {
        event["event_type"] for event in database.get_events(restored_path)
    }
    assert restored_event_types == {"new_device", "monitor_down"}


def test_sqlite_backup_closes_source_if_destination_cannot_open(tmp_path: Path, monkeypatch):
    import sqlite3

    from netsentinel import data_export_service

    source = tmp_path / "source.sqlite3"
    database.initialize(source)

    real_connect = sqlite3.connect
    opened_connections = []
    calls = 0

    def fail_destination(path, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            connection = real_connect(path, **kwargs)
            opened_connections.append(connection)
            return connection
        raise sqlite3.OperationalError("simulated temporary-destination failure")

    monkeypatch.setattr(data_export_service.sqlite3, "connect", fail_destination)

    with pytest.raises(sqlite3.OperationalError, match="simulated temporary-destination failure"):
        database.export_sqlite_backup(source)

    assert len(opened_connections) == 1
    # A leaked connection would still accept this query. A closed one raises.
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        opened_connections[0].execute("SELECT 1")


def test_scan_discovery_report_is_persisted(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    report = {
        "networks": [{"network": "192.168.10.0/24", "interface": "en0", "local_address": "192.168.10.8", "range_limited": False}],
        "addresses_checked": 254,
        "ping_responses": 4,
        "scope": "fixture",
    }
    database.record_scan(
        [Neighbor("192.168.10.1", "AA:BB:CC:DD:EE:FF", "en0", "automatic-local-network")],
        path=db,
        discovery=report,
    )
    assert database.get_scans(path=db)[0]["discovery"] == report
    exported = __import__("json").loads(database.export_json(path=db))
    assert exported["scans"][0]["discovery"] == report
    assert "discovery_json" not in exported["scans"][0]


def test_update_missing_device_returns_none(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    assert database.update_device(999, trusted=True, path=db) is None


def test_tracks_multiple_addresses_for_same_mac_without_duplicate_device(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    mac = "00:11:22:33:44:55"
    first = database.record_scan(
        [Neighbor("192.168.10.10", mac, "eth0"), Neighbor("fe80::10", mac, "eth0")], path=db
    )
    assert first["devices_found"] == 1
    assert first["addresses_found"] == 2
    devices = database.list_devices(db)
    assert len(devices) == 1
    assert {address["ip_address"] for address in devices[0]["addresses"]} == {"192.168.10.10", "fe80::10"}
    matching = database.list_devices(path=db, query="fe80::10")
    assert len(matching) == 1
    assert matching[0]["mac_address"] == mac
    assert len(database.get_events(db)) == 1


def test_records_ipv4_change_as_a_reviewable_event(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    mac = "00:11:22:33:44:55"
    database.record_scan([Neighbor("192.168.10.10", mac, "eth0")], path=db)
    database.record_scan([Neighbor("192.168.10.21", mac, "eth0")], path=db)
    events = database.get_events(db)
    assert {event["event_type"] for event in events} == {"new_device", "ip_changed"}
    assert "192.168.10.10" in next(event["message"] for event in events if event["event_type"] == "ip_changed")


def test_same_scan_with_two_ipv4_addresses_does_not_claim_ip_change(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    mac = "00:11:22:33:44:55"
    database.record_scan([Neighbor("192.168.10.10", mac)], path=db)
    database.record_scan(
        [Neighbor("192.168.10.10", mac), Neighbor("192.168.10.21", mac)], path=db
    )
    assert not any(event["event_type"] == "ip_changed" for event in database.get_events(db))


def test_migrates_v01_device_schema(tmp_path: Path):
    import sqlite3

    db = tmp_path / "legacy.sqlite3"
    connection = sqlite3.connect(db)
    connection.executescript(
        """CREATE TABLE devices (
             id INTEGER PRIMARY KEY AUTOINCREMENT, mac_address TEXT NOT NULL UNIQUE,
             ip_address TEXT NOT NULL, interface TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
             trusted INTEGER NOT NULL DEFAULT 0, display_name TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''
           );
           CREATE TABLE scans (
             id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL,
             finished_at TEXT NOT NULL, source TEXT NOT NULL,
             devices_found INTEGER NOT NULL DEFAULT 0, errors_json TEXT NOT NULL DEFAULT '[]'
           );
           INSERT INTO devices(mac_address, ip_address, first_seen, last_seen)
           VALUES ('00:11:22:33:44:55', '192.168.1.2', '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');"""
    )
    connection.commit()
    connection.close()
    database.initialize(db)
    device = database.list_devices(db)[0]
    assert device["manufacturer"] is None
    assert device["mac_locally_administered"] is False
    assert device["addresses"][0]["ip_address"] == "192.168.1.2"
    with database.connect(db) as migrated:
        columns = {row[1] for row in migrated.execute("PRAGMA table_info(scans)")}
    assert "discovery_json" in columns
    assert database.get_scans(path=db) == []


def test_migrates_legacy_activity_events_without_losing_rows(tmp_path: Path):
    """La ampliación del esquema debe conservar metadatos ya guardados."""
    import sqlite3

    db = tmp_path / "legacy-activity.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.executescript(
            """CREATE TABLE devices (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   mac_address TEXT NOT NULL UNIQUE,
                   ip_address TEXT NOT NULL,
                   interface TEXT,
                   first_seen TEXT NOT NULL,
                   last_seen TEXT NOT NULL,
                   trusted INTEGER NOT NULL DEFAULT 0,
                   display_name TEXT NOT NULL DEFAULT '',
                   notes TEXT NOT NULL DEFAULT ''
               );
               CREATE TABLE activity_sessions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                   source_mode TEXT NOT NULL,
                   started_at TEXT NOT NULL,
                   ends_at TEXT NOT NULL,
                   stopped_at TEXT,
                   status TEXT NOT NULL DEFAULT 'active'
               );
               CREATE TABLE activity_events (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   session_id INTEGER REFERENCES activity_sessions(id) ON DELETE SET NULL,
                   device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                   observed_at TEXT NOT NULL,
                   received_at TEXT NOT NULL,
                   event_type TEXT NOT NULL CHECK (
                       event_type IN ('dns_query', 'connection', 'tls_sni', 'app_usage', 'blocked')
                   ),
                   source TEXT NOT NULL CHECK (
                       source IN ('router_dns', 'router_flow', 'device_agent', 'manual_import')
                   ),
                   domain TEXT,
                   destination_ip TEXT,
                   destination_port INTEGER,
                   protocol TEXT,
                   app_name TEXT,
                   blocked INTEGER NOT NULL DEFAULT 0
               );
               INSERT INTO devices
                   (id, mac_address, ip_address, first_seen, last_seen)
               VALUES
                   (7, 'AA:BB:CC:DD:EE:77', '192.168.7.7',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00');
               INSERT INTO activity_events
                   (id, device_id, observed_at, received_at, event_type, source, domain, blocked)
               VALUES
                   (19, 7, '2026-01-01T00:01:00+00:00', '2026-01-01T00:01:01+00:00',
                    'dns_query', 'router_dns', 'legacy.example', 0);"""
        )

    database.initialize(db)

    with database.connect(db) as connection:
        event = connection.execute(
            """SELECT id, device_id, event_type, source, domain, page_url, email_subject,
                      source_ip, source_port, bytes_sent, bytes_received,
                      packets_sent, packets_received, network_interface, source_event_id
               FROM activity_events WHERE id = 19"""
        ).fetchone()
        assert event is not None
        assert dict(event) == {
            "id": 19,
            "device_id": 7,
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "legacy.example",
            "page_url": None,
            "email_subject": None,
            "source_ip": None, "source_port": None, "bytes_sent": None, "bytes_received": None,
            "packets_sent": None, "packets_received": None, "network_interface": None, "source_event_id": None,
        }

        # La base migrada acepta campos adicionales y conserva los desconocidos como NULL.
        connection.execute(
            """INSERT INTO activity_events
               (device_id, observed_at, received_at, event_type, source, page_url,
                source_ip, source_port, bytes_sent, packets_received, network_interface, source_event_id)
               VALUES (7, '2026-01-02T00:00:00+00:00', '2026-01-02T00:00:01+00:00',
                       'page_visit', 'manual_import', 'https://example.com/',
                       '192.0.2.7', 51514, 1200, 3, 'wan0', 'row-77')"""
        )
        inserted = connection.execute(
            """SELECT source_ip, source_port, bytes_sent, packets_received, network_interface, source_event_id
               FROM activity_events WHERE event_type = 'page_visit'"""
        ).fetchone()
        assert dict(inserted) == {
            "source_ip": "192.0.2.7", "source_port": 51514, "bytes_sent": 1200,
            "packets_received": 3, "network_interface": "wan0", "source_event_id": "row-77",
        }


def test_schema_initialization_rolls_back_when_the_initial_script_fails(tmp_path: Path):
    """Un error de migración no debe dejar tablas nuevas a medio crear."""
    import sqlite3

    db = tmp_path / "failed-schema.sqlite3"
    with sqlite3.connect(db) as connection:
        connection.execute(
            """CREATE TABLE activity_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                retention_days INTEGER NOT NULL DEFAULT 7 CHECK (retention_days BETWEEN 1 AND 90)
            )"""
        )
        connection.execute(
            """CREATE TRIGGER reject_activity_settings_seed
               BEFORE INSERT ON activity_settings
               BEGIN
                   SELECT RAISE(ABORT, 'simulated schema initialization failure');
               END"""
        )

    with pytest.raises(sqlite3.IntegrityError, match="simulated schema initialization failure"):
        database.initialize(db)

    with sqlite3.connect(db) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

    # La tabla preexistente se conserva, pero no quedan tablas nuevas a medio crear.
    assert "activity_settings" in tables
    assert "devices" not in tables
    assert "scans" not in tables


def test_uses_local_oui_file_and_records_lookup_provenance(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    (tmp_path / "oui.csv").write_text("prefix,vendor\nAABBCC,Proveedor de ejemplo\n", encoding="utf-8")
    db = tmp_path / "test.sqlite3"
    database.initialize(db)
    database.record_scan([Neighbor("192.168.10.8", "AA:BB:CC:DD:EE:FF", "eth0")], path=db)
    device = database.list_devices(db)[0]
    assert device["manufacturer"] == "Proveedor de ejemplo"
    assert device["manufacturer_source"] == "oui.csv (base local)"
    assert device["manufacturer_checked_at"]


def test_monitor_history_retention_prunes_only_old_check_rows(tmp_path: Path):
    from datetime import datetime, timedelta, timezone

    db = tmp_path / "retention.sqlite3"
    database.initialize(db)
    monitor = database.create_monitor("Retención", "tcp", "127.0.0.1:80", 60, 3, path=db)
    current = datetime.now(timezone.utc).replace(microsecond=0)
    recent = current.isoformat(timespec="seconds")
    old = (current - timedelta(days=91)).isoformat(timespec="seconds")

    # Create an open incident and a current monitor status; the cleanup must not
    # remove either because only detailed samples are subject to this policy.
    database.record_monitor_check(monitor["id"], "down", None, "Fallo simulado", path=db)
    with database.connect(db) as connection:
        connection.execute(
            "INSERT INTO monitor_checks(monitor_id, checked_at, status, latency_ms, detail) VALUES (?, ?, ?, ?, ?)",
            (monitor["id"], old, "down", None, "Comprobación antigua"),
        )
        connection.execute(
            "INSERT INTO monitor_checks(monitor_id, checked_at, status, latency_ms, detail) VALUES (?, ?, ?, ?, ?)",
            (monitor["id"], recent, "up", 12.5, "Comprobación reciente"),
        )

    assert database.cleanup_monitor_history(90, path=db) == 1
    with database.connect(db) as connection:
        checks = connection.execute(
            "SELECT checked_at, detail FROM monitor_checks WHERE monitor_id = ? ORDER BY checked_at",
            (monitor["id"],),
        ).fetchall()
        incidents = connection.execute(
            "SELECT status, failure_count FROM incidents WHERE monitor_id = ?",
            (monitor["id"],),
        ).fetchall()

    assert len(checks) == 2  # The generated current failure and the explicit recent row.
    assert all(row["detail"] != "Comprobación antigua" for row in checks)
    assert any(row["detail"] == "Comprobación reciente" for row in checks)
    assert len(incidents) == 1
    assert incidents[0]["status"] == "open"
    assert incidents[0]["failure_count"] == 1


def test_monitor_history_retention_rejects_unsafe_days(tmp_path: Path):
    db = tmp_path / "retention-validation.sqlite3"
    database.initialize(db)
    for value in (0, -1, 3651, True, "90"):
        try:
            database.cleanup_monitor_history(value, path=db)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid retention value should be rejected: {value!r}")



def test_connect_never_changes_permissions_of_an_existing_parent(tmp_path, monkeypatch):
    import os

    shared_parent = tmp_path / "shared"
    shared_parent.mkdir()
    db_path = shared_parent / "netsentinel.sqlite3"
    real_chmod = os.chmod
    chmod_calls = []

    def tracked_chmod(path, mode):
        chmod_calls.append((Path(path), mode))
        return real_chmod(path, mode)

    monkeypatch.setattr(database.os, "chmod", tracked_chmod)
    with database.connect(db_path):
        pass

    assert (shared_parent, 0o700) not in chmod_calls
    # The file mode is applied through a no-follow file descriptor, not chmod(path).
    if os.name == "posix":
        import stat
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600
        assert chmod_calls == []
    else:
        assert chmod_calls == []



def test_connect_hardens_existing_database_file_permissions(tmp_path):
    import os
    import sqlite3
    import stat

    if os.name != "posix":
        pytest.skip("Los permisos POSIX no se aplican en Windows.")

    db_path = tmp_path / "existing.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE fixture (value TEXT)")
    os.chmod(db_path, 0o644)

    with database.connect(db_path):
        pass

    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600


def test_connect_hardens_existing_database_file_without_following_symlinks(tmp_path):
    import os
    import stat

    if os.name != "posix":
        pytest.skip("Los permisos POSIX y los enlaces simbólicos no son uniformes en Windows.")

    target = tmp_path / "existing-shared.sqlite3"
    with database.connect(target):
        pass
    os.chmod(target, 0o644)
    link = tmp_path / "netsentinel.sqlite3"
    link.symlink_to(target)

    with database.connect(link):
        pass

    assert link.is_symlink()
    assert stat.S_IMODE(target.stat().st_mode) == 0o644

def test_connect_creates_new_nested_directories_with_private_permissions(tmp_path):
    import os
    import stat

    shared_parent = tmp_path / "shared"
    shared_parent.mkdir()
    destination = shared_parent / "nested" / "netsentinel-data"
    db_path = destination / "netsentinel.sqlite3"

    with database.connect(db_path):
        pass

    assert db_path.is_file()
    if os.name == "posix":
        assert stat.S_IMODE((shared_parent / "nested").stat().st_mode) == 0o700
        assert stat.S_IMODE(destination.stat().st_mode) == 0o700
        assert stat.S_IMODE(db_path.stat().st_mode) == 0o600



def test_connect_hardens_existing_default_application_directory(tmp_path, monkeypatch):
    import os
    import stat

    if os.name != "posix":
        pytest.skip("Los modos POSIX no se aplican en Windows.")

    app_data = tmp_path / ".netsentinel"
    app_data.mkdir()
    os.chmod(app_data, 0o755)
    db_path = app_data / "netsentinel.sqlite3"
    monkeypatch.delenv("NETSENTINEL_DATA_DIR", raising=False)
    monkeypatch.setattr(database, "database_path", lambda: db_path)

    with database.connect():
        pass

    assert stat.S_IMODE(app_data.stat().st_mode) == 0o700
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600



def test_connect_does_not_chmod_target_of_database_file_symlink(tmp_path):
    import os
    import stat

    if os.name != "posix":
        pytest.skip("Los modos POSIX y los enlaces simbólicos no son uniformes en Windows.")

    target = tmp_path / "shared-database.sqlite3"
    with database.connect(target):
        pass
    os.chmod(target, 0o644)

    link = tmp_path / "netsentinel.sqlite3"
    link.symlink_to(target)

    with database.connect(link):
        pass

    assert link.is_symlink()
    assert stat.S_IMODE(target.stat().st_mode) == 0o644


def test_connect_does_not_chmod_target_of_default_directory_symlink(tmp_path, monkeypatch):
    import os
    import stat

    from netsentinel import config

    if os.name != "posix":
        pytest.skip("Los enlaces simbólicos POSIX no son uniformes en Windows.")

    target = tmp_path / "shared-target"
    target.mkdir()
    os.chmod(target, 0o755)
    link = tmp_path / ".netsentinel"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.delenv("NETSENTINEL_DATA_DIR", raising=False)
    monkeypatch.setattr(config.Path, "home", classmethod(lambda _cls: tmp_path))

    # Exercise the real config -> database_path -> connect path: resolving the
    # default path here would hide the symlink from the private-directory guard.
    assert config.data_dir() == link
    db_path = config.database_path()
    assert db_path == link / "netsentinel.sqlite3"

    with database.connect():
        pass

    assert link.is_symlink()
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600

def test_scan_observations_preserve_exact_historical_source_and_address(tmp_path: Path):
    """Una lectura anterior debe mantener su evidencia tras una nueva observación."""
    db = tmp_path / "scan-observations.sqlite3"
    database.initialize(db)
    mac = "AA:BB:CC:DD:EE:91"

    first = database.record_scan(
        [Neighbor("192.168.10.20", mac, "en0", "automatic-local-network")],
        path=db,
        discovery={"networks": [{"network": "192.168.10.0/24", "interface": "en0"}]},
    )
    second = database.record_scan(
        [Neighbor("192.168.10.20", mac, "en0", "system-neighbor-table")],
        path=db,
        discovery={"networks": [{"network": "192.168.10.0/24", "interface": "en0"}]},
    )

    historical = database.get_scan_observations(first["scan_id"], path=db)
    latest = database.get_scan_observations(second["scan_id"], path=db)

    assert historical is not None and latest is not None
    assert len(historical) == len(latest) == 1
    assert historical[0]["scan_id"] == first["scan_id"]
    assert historical[0]["ip_address"] == "192.168.10.20"
    assert historical[0]["source"] == "automatic-local-network"
    assert latest[0]["source"] == "system-neighbor-table"
    assert historical[0]["device_id"] == latest[0]["device_id"]
    assert database.get_scan_observations(99999, path=db) is None



def test_scan_comparison_uses_historical_observations_and_does_not_claim_disconnection(tmp_path: Path):
    db = tmp_path / "comparison.sqlite3"
    database.initialize(db)
    network = {
        "networks": [{
            "network": "192.168.5.0/24",
            "interface": "en0",
            "local_address": "192.168.5.2",
            "range_limited": False,
        }]
    }
    baseline = database.record_scan([
        Neighbor("192.168.5.10", "AA:BB:CC:DD:EE:01", "en0", "automatic-local-network"),
        Neighbor("192.168.5.20", "AA:BB:CC:DD:EE:02", "en0", "automatic-local-network"),
        Neighbor("192.168.5.30", "AA:BB:CC:DD:EE:03", "en0", "automatic-local-network"),
    ], path=db, discovery=network)
    comparison = database.record_scan([
        Neighbor("192.168.5.11", "AA:BB:CC:DD:EE:01", "en0", "automatic-local-network"),
        Neighbor("192.168.5.20", "AA:BB:CC:DD:EE:02", "en0", "automatic-local-network"),
        Neighbor("192.168.5.40", "AA:BB:CC:DD:EE:04", "en0", "automatic-local-network"),
    ], path=db, discovery=network)

    result = database.compare_scans(baseline["scan_id"], comparison["scan_id"], path=db)

    assert result is not None
    assert result["comparable"] is True
    assert result["common_networks"] == ["192.168.5.0/24"]
    assert result["summary"] == {
        "baseline_devices": 3,
        "comparison_devices": 3,
        "only_in_baseline": 1,
        "only_in_comparison": 1,
        "address_changed": 1,
        "unchanged": 1,
        "total_devices": 4,
    }
    changes = {item["mac_address"]: item for item in result["changes"]}
    moved = changes["AA:BB:CC:DD:EE:01"]
    assert moved["status"] == "address_changed"
    assert moved["baseline_addresses"] == ["192.168.5.10"]
    assert moved["comparison_addresses"] == ["192.168.5.11"]
    assert moved["baseline_evidence"] == [{
        "scan_id": baseline["scan_id"],
        "ip_address": "192.168.5.10",
        "observed_at": moved["baseline_evidence"][0]["observed_at"],
        "source": "automatic-local-network",
    }]
    assert moved["baseline_evidence"][0]["observed_at"]
    assert moved["comparison_evidence"] == [{
        "scan_id": comparison["scan_id"],
        "ip_address": "192.168.5.11",
        "observed_at": moved["comparison_evidence"][0]["observed_at"],
        "source": "automatic-local-network",
    }]
    assert moved["comparison_evidence"][0]["observed_at"]
    not_seen_later = changes["AA:BB:CC:DD:EE:03"]
    assert not_seen_later["status"] == "only_in_baseline"
    assert not_seen_later["comparison_addresses"] == []
    assert not_seen_later["baseline_evidence"]
    assert not_seen_later["comparison_evidence"] == []
    assert "No demuestra" in result["absence_note"]
    assert "desconectado" not in not_seen_later["status"]


def test_scan_comparison_rejects_unrelated_private_network_scopes(tmp_path: Path):
    db = tmp_path / "comparison-scope.sqlite3"
    database.initialize(db)
    first = database.record_scan(
        [Neighbor("192.168.5.10", "AA:BB:CC:DD:EE:10", "en0", "automatic-local-network")],
        path=db,
        discovery={"networks": [{"network": "192.168.5.0/24", "interface": "en0"}]},
    )
    second = database.record_scan(
        [Neighbor("10.20.0.10", "AA:BB:CC:DD:EE:20", "en1", "automatic-local-network")],
        path=db,
        discovery={"networks": [{"network": "10.20.0.0/24", "interface": "en1"}]},
    )

    result = database.compare_scans(first["scan_id"], second["scan_id"], path=db)

    assert result is not None
    assert result["comparable"] is False
    assert result["common_networks"] == []
    assert result["changes"] == []
    assert result["summary"] is None
    assert "no comparten una subred" in result["reason"]


def test_scan_comparison_ignores_devices_outside_shared_subnets(tmp_path: Path):
    db = tmp_path / "comparison-multiple-networks.sqlite3"
    database.initialize(db)
    first = database.record_scan(
        [
            Neighbor("192.168.5.10", "AA:BB:CC:DD:EE:51", "en0", "automatic-local-network"),
            Neighbor("10.20.1.10", "AA:BB:CC:DD:EE:52", "en1", "automatic-local-network"),
        ],
        path=db,
        discovery={"networks": [
            {"network": "192.168.5.0/24", "interface": "en0"},
            {"network": "10.20.1.0/24", "interface": "en1"},
        ]},
    )
    second = database.record_scan(
        [
            Neighbor("192.168.5.10", "AA:BB:CC:DD:EE:51", "en0", "automatic-local-network"),
            Neighbor("10.20.2.10", "AA:BB:CC:DD:EE:53", "en2", "automatic-local-network"),
        ],
        path=db,
        discovery={"networks": [
            {"network": "192.168.5.0/24", "interface": "en0"},
            {"network": "10.20.2.0/24", "interface": "en2"},
        ]},
    )

    result = database.compare_scans(first["scan_id"], second["scan_id"], path=db)

    assert result is not None
    assert result["comparable"] is True
    assert result["common_networks"] == ["192.168.5.0/24"]
    assert result["summary"] == {
        "baseline_devices": 1,
        "comparison_devices": 1,
        "only_in_baseline": 0,
        "only_in_comparison": 0,
        "address_changed": 0,
        "unchanged": 1,
        "total_devices": 1,
    }
    assert result["changes"] == []
