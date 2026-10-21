"""Regresiones para el generador de escenarios manuales sintéticos."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "generate_manual_scenarios.py"


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
