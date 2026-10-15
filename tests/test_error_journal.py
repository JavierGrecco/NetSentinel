"""Pruebas del diario local de errores y sus límites de privacidad."""
from __future__ import annotations

import json
import os
import stat

import pytest

from netsentinel import error_journal, error_reporting


def test_error_journal_writes_allowlisted_fields_and_rotates(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(error_journal, "_ERROR_LOG_MAX_BYTES", 300)
    for index in range(8):
        assert error_reporting.record_error_event({
            "error_code": "NS-500-001",
            "request_id": f"{index:012X}",
            "category": "unexpected",
            "severity": "error",
            "reason": "Safe catalog reason",
            "message": "PRIVATE_TOKEN=do-not-save",
            "raw_body": "secret body",
            "frames": "main.py:123:handler",
        })

    path = tmp_path / "netsentinel-errors.jsonl"
    assert path.exists()
    current_lines = path.read_text(encoding="utf-8").splitlines()
    assert current_lines
    parsed = [json.loads(line) for line in current_lines]
    assert all(record["error_code"] == "NS-500-001" for record in parsed)
    assert all("message" not in record and "raw_body" not in record for record in parsed)
    all_logs = "\n".join(
        candidate.read_text(encoding="utf-8")
        for candidate in tmp_path.glob("netsentinel-errors.jsonl*")
        if candidate.is_file()
    )
    assert "PRIVATE_TOKEN" not in all_logs
    assert "secret body" not in all_logs
    assert (tmp_path / "netsentinel-errors.jsonl.1").exists()
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600



@pytest.mark.skipif(os.name != "posix", reason="Los modos de archivo POSIX no se aplican en Windows.")
def test_error_journal_hardens_existing_log_before_archiving(monkeypatch, tmp_path):
    """Un log antiguo con permisos abiertos no debe seguir así tras la rotación."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(error_journal, "_ERROR_LOG_MAX_BYTES", 1)
    path = tmp_path / "netsentinel-errors.jsonl"
    path.write_text(
        '{"error_code":"NS-500-001","reason":"safe legacy diagnostic"}\n',
        encoding="utf-8",
    )
    os.chmod(path, 0o644)

    assert error_reporting.record_error_event({
        "error_code": "NS-DB-001",
        "category": "database",
        "severity": "error",
        "reason": "Safe new diagnostic",
    })

    archived = tmp_path / "netsentinel-errors.jsonl.1"
    assert archived.is_file()
    assert stat.S_IMODE(archived.stat().st_mode) == 0o600
    assert stat.S_IMODE(path.stat().st_mode) == 0o600



def test_error_journal_returns_false_when_persistence_is_unavailable(monkeypatch, tmp_path):
    blocked_dir = tmp_path / "not-a-file"
    blocked_dir.mkdir()
    monkeypatch.setattr(error_journal, "data_dir", lambda: blocked_dir)
    (blocked_dir / "netsentinel-errors.jsonl").mkdir()

    assert error_reporting.record_error_event({
        "error_code": "NS-500-001",
        "category": "unexpected",
        "severity": "error",
        "reason": "Safe catalog reason",
    }) is False


def test_error_journal_rejects_records_without_an_error_code(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))

    assert error_reporting.record_error_event({"category": "unexpected"}) is False
    assert not (tmp_path / "netsentinel-errors.jsonl").exists()


@pytest.mark.skipif(os.name != "posix", reason="La prueba requiere enlaces simbólicos POSIX.")
def test_error_journal_does_not_follow_a_symlink(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    target = tmp_path / "keep.txt"
    target.write_text("no modificar", encoding="utf-8")
    log_path = tmp_path / "netsentinel-errors.jsonl"
    log_path.symlink_to(target)

    assert error_reporting.record_error_event({
        "error_code": "NS-500-001",
        "category": "unexpected",
        "severity": "error",
        "reason": "Safe catalog reason",
    }) is False
    assert target.read_text(encoding="utf-8") == "no modificar"
