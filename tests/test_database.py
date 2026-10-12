from pathlib import Path

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


def test_sqlite_backup_is_consistent_and_contains_history(tmp_path: Path):
    import sqlite3

    source = tmp_path / "netsentinel.sqlite3"
    database.initialize(source)
    database.record_scan(
        [Neighbor("192.168.22.4", "AA:BB:CC:DD:EE:11", "en0")],
        path=source,
    )
    backup_path = tmp_path / "backup.sqlite3"
    backup_path.write_bytes(database.export_sqlite_backup(source))

    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT mac_address FROM devices").fetchone()[0] == "AA:BB:CC:DD:EE:11"
        assert backup.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 1
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


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
    if os.name == "posix":
        assert (db_path, 0o600) in chmod_calls
    else:
        assert chmod_calls == []


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
