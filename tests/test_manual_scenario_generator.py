"""Regresiones para el generador de escenarios manuales sintéticos."""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from netsentinel import activity_event_service, activity_import_service

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_manual_scenarios.py"
SEED_SCRIPT = ROOT / "scripts" / "seed_manual_test_database.py"


def run_generator(output_dir: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta el script como lo haría una persona desde Terminal."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--output-dir", str(output_dir), *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_generator_creates_expected_valid_and_negative_scenarios(tmp_path: Path) -> None:
    result = run_generator(tmp_path, "--device-ip", "192.168.1.25")
    assert result.returncode == 0, result.stderr
    expected = {
        "activity.csv",
        "activity-invalid-sensitive.csv",
        "activity-invalid-duplicate-header.csv",
        "zeek-conn.jsonl",
        "zeek-conn.tsv",
        "zeek-invalid.jsonl",
        "README.txt",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected

    with (tmp_path / "activity.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    assert {row["event_type"] for row in rows} == {
        "dns_query", "connection", "tls_sni", "blocked", "app_usage", "search_query"
    }
    assert all(datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00")).tzinfo for row in rows)
    assert rows[0]["destination_ip"] == "1.1.1.1"

    records = [
        json.loads(line)
        for line in (tmp_path / "zeek-conn.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 3
    assert len({record["uid"] for record in records}) == 3
    assert records[0]["id.orig_h"] == "192.168.1.25"
    assert records[1]["orig_ip_bytes"] == 0
    assert "orig_ip_bytes" not in records[2]
    assert records[2]["id.resp_h"] == "192.168.1.25"

    tsv = (tmp_path / "zeek-conn.tsv").read_text(encoding="utf-8")
    assert "#path conn\n" in tsv
    assert "#fields " + "\t".join([
        "ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p",
        "proto", "orig_ip_bytes", "resp_ip_bytes", "orig_pkts", "resp_pkts",
    ]) in tsv
    assert "\t-\t0\t-\t0\n" in tsv
    assert "SYNTHETIC_BODY_MUST_BE_REJECTED" in (
        tmp_path / "activity-invalid-sensitive.csv"
    ).read_text(encoding="utf-8")
    assert "{this is not valid JSON}" in (
        tmp_path / "zeek-invalid.jsonl"
    ).read_text(encoding="utf-8")


def test_generator_refuses_to_overwrite_without_explicit_force(tmp_path: Path) -> None:
    first = run_generator(tmp_path)
    assert first.returncode == 0, first.stderr
    target = tmp_path / "activity.csv"
    target.write_text("KEEP THIS FILE\n", encoding="utf-8")

    second = run_generator(tmp_path)
    assert second.returncode != 0
    assert "no se modificaron" in second.stderr
    assert target.read_text(encoding="utf-8") == "KEEP THIS FILE\n"

    third = run_generator(tmp_path, "--force")
    assert third.returncode == 0, third.stderr
    assert target.read_text(encoding="utf-8").startswith("observed_at,event_type,")


def test_generator_rejects_hostnames_and_invalid_ip_literals(tmp_path: Path) -> None:
    result = run_generator(tmp_path, "--device-ip", "device.local")
    assert result.returncode != 0
    assert not list(tmp_path.iterdir())


def test_generated_activity_csv_passes_real_validator_without_database_writes(
    tmp_path: Path, monkeypatch
) -> None:
    """El CSV de ejemplo se valida con la lógica real, pero la escritura se intercepta."""
    generated = run_generator(tmp_path)
    assert generated.returncode == 0, generated.stderr
    csv_data = (tmp_path / "activity.csv").read_text(encoding="utf-8")
    captured = {}

    def capture_events(device_id, events, line_numbers, *, now, preview):
        captured["device_id"] = device_id
        captured["events"] = events
        captured["line_numbers"] = line_numbers
        captured["preview"] = preview
        return {
            "imported": len(events),
            "skipped_duplicates": 0,
            "preview_dispositions": ["new"] * len(events),
        }

    monkeypatch.setattr(
        activity_import_service.activity_repository,
        "require_device_exists",
        lambda _device_id: None,
    )
    monkeypatch.setattr(
        activity_import_service.activity_repository,
        "import_manual_events",
        capture_events,
    )

    result = activity_import_service.import_csv(
        77,
        csv_data,
        normalize_event=activity_event_service.normalize_event,
        preview=False,
    )
    assert result["imported"] == 6
    assert captured["device_id"] == 77
    assert captured["preview"] is False
    assert captured["line_numbers"] == [2, 3, 4, 5, 6, 7]
    assert [item["event_type"] for item in captured["events"]] == [
        "dns_query", "connection", "tls_sni", "blocked", "app_usage", "search_query"
    ]
    assert captured["events"][0]["destination_ip"] == "1.1.1.1"
    assert captured["events"][3]["blocked"] == 1


def run_seed(directory: Path | None, *extra_args: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta el creador de activo sintético con un entorno de datos explícito."""
    env = os.environ.copy()
    env.pop("NETSENTINEL_DATA_DIR", None)
    if directory is not None:
        env["NETSENTINEL_DATA_DIR"] = str(directory)
    return subprocess.run(
        [sys.executable, str(SEED_SCRIPT), *extra_args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_seed_requires_explicit_isolated_directory(tmp_path: Path) -> None:
    result = run_seed(None)
    assert result.returncode != 0
    assert "NETSENTINEL_DATA_DIR" in result.stderr
    assert not (Path.home() / ".netsentinel" / "netsentinel.sqlite3").exists() or (
        "no se modificó" in result.stderr
    )


def test_seed_creates_only_synthetic_inventory_in_new_database(tmp_path: Path) -> None:
    result = run_seed(tmp_path, "--device-ip", "192.168.56.20")
    assert result.returncode == 0, result.stderr
    db_path = tmp_path / "netsentinel.sqlite3"
    assert db_path.is_file()

    with sqlite3.connect(db_path) as db:
        devices = db.execute(
            "SELECT mac_address, ip_address, display_name, notes FROM devices"
        ).fetchall()
        addresses = db.execute(
            "SELECT ip_address, first_seen, last_seen, source FROM device_addresses"
        ).fetchall()
        scans = db.execute(
            "SELECT source, devices_found, discovery_json FROM scans"
        ).fetchall()

    assert len(devices) == 1
    assert devices[0][0:3] == (
        "02:00:00:00:00:20", "192.168.56.20", "Dispositivo sintético de prueba"
    )
    assert "No representa un equipo real" in devices[0][3]
    assert len(addresses) == 1
    assert addresses[0][0] == "192.168.56.20"
    assert addresses[0][1] < addresses[0][2]
    assert addresses[0][3] == "synthetic-test-fixture"
    assert scans[0][0] == "synthetic-test-fixture"
    assert scans[0][1] == 1
    assert '"network_scan_performed": false' in scans[0][2]


def test_seed_refuses_existing_database_without_modifying_it(tmp_path: Path) -> None:
    db_path = tmp_path / "netsentinel.sqlite3"
    db_path.write_bytes(b"preserve this file")
    result = run_seed(tmp_path)
    assert result.returncode != 0
    assert "Ya existe una base SQLite" in result.stderr
    assert db_path.read_bytes() == b"preserve this file"


def test_seed_rejects_public_or_invalid_device_ip_without_creating_database(tmp_path: Path) -> None:
    result = run_seed(tmp_path, "--device-ip", "8.8.8.8")
    assert result.returncode != 0
    assert not (tmp_path / "netsentinel.sqlite3").exists()
