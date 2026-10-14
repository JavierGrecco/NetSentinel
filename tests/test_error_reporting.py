from __future__ import annotations

import sqlite3
from pathlib import Path

from netsentinel import error_journal, error_reporting
from netsentinel.error_reporting import describe_http_error, describe_unhandled_exception


def test_sqlite_locked_error_has_actionable_code_without_raw_detail():
    error = describe_unhandled_exception(sqlite3.OperationalError("database is locked: PRIVATE_TOKEN"))

    assert error.code == "NS-DB-002"
    assert "ocupada" in error.message
    assert "cerrá otras instancias" in error.next_action
    assert "PRIVATE_TOKEN" not in error.message
    assert "PRIVATE_TOKEN" not in error.log_reason


def test_sqlite_storage_and_access_failures_have_distinct_codes():
    full = describe_unhandled_exception(sqlite3.OperationalError("database or disk is full"))
    readonly = describe_unhandled_exception(sqlite3.OperationalError("attempt to write a readonly database"))
    malformed = describe_unhandled_exception(sqlite3.OperationalError("database disk image is malformed"))

    assert full.code == "NS-DB-003"
    assert readonly.code == "NS-DB-004"
    io_error = describe_unhandled_exception(sqlite3.OperationalError("disk I/O error"))
    assert malformed.code == "NS-DB-005"
    assert io_error.code == "NS-DB-007"
    assert full.code != readonly.code != malformed.code


def test_generic_exception_is_safe_and_requests_followup_reference():
    error = describe_unhandled_exception(RuntimeError("email=person@example.com token=secret"))

    assert error.code == "NS-500-001"
    assert "código de error" in error.next_action
    assert "person@example.com" not in error.message
    assert "secret" not in error.log_reason
    assert error.log_level == "error"


def test_expected_permission_and_timeout_errors_are_classified():
    import subprocess

    permission = describe_unhandled_exception(PermissionError("/private/user/data.sqlite"))
    timeout = describe_unhandled_exception(subprocess.TimeoutExpired(["ping", "private-host"], 3))

    assert permission.code == "NS-FS-001"
    assert "/private/user" not in permission.message
    assert timeout.code == "NS-SYS-002"


def test_http_errors_have_stable_codes_and_next_steps():
    assert describe_http_error(404) == (
        "NS-HTTP-404",
        "Actualizá la vista y comprobá que el recurso todavía exista.",
    )
    assert describe_http_error(503)[0] == "NS-HTTP-503"
    assert describe_http_error(418)[0] == "NS-HTTP-418"


def test_error_journal_keeps_its_legacy_import_path():
    """Los manejadores existentes siguen usando el contrato histórico."""
    assert error_reporting.record_error_event is error_journal.record_error_event

def test_panel_formats_validation_errors_and_reports_backend_request_reference():
    root = Path(__file__).resolve().parents[1] / "src/netsentinel/static"
    source = (root / "index.html").read_text(encoding="utf-8") + (root / "index.js").read_text(encoding="utf-8")

    assert "item.loc.filter" in source
    assert "Código: ${code}" in source
    assert "Referencia: ${requestId}" in source
    assert "NS-CONN-001" in source
    assert "no queda registrada en el log del backend" in source
