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


def test_native_sqlite_codes_override_messages_and_cover_extended_codes():
    def code(name: str, fallback: int) -> int:
        return getattr(sqlite3, name, fallback)

    cases = [
        (
            sqlite3.OperationalError,
            "opaque busy detail",
            code("SQLITE_BUSY", 5) | (1 << 8),
            "NS-DB-002",
        ),
        (sqlite3.OperationalError, "opaque lock detail", code("SQLITE_LOCKED", 6), "NS-DB-002"),
        (sqlite3.OperationalError, "opaque storage detail", code("SQLITE_FULL", 13), "NS-DB-003"),
        (sqlite3.OperationalError, "opaque I/O detail", code("SQLITE_IOERR", 10), "NS-DB-007"),
        # Deliberately conflicting message: the native code must take precedence.
        (
            sqlite3.OperationalError,
            "database is locked: PRIVATE_TOKEN",
            code("SQLITE_READONLY", 8),
            "NS-DB-004",
        ),
        (sqlite3.OperationalError, "opaque open detail", code("SQLITE_CANTOPEN", 14), "NS-DB-004"),
        (sqlite3.DatabaseError, "opaque corruption detail", code("SQLITE_CORRUPT", 11), "NS-DB-005"),
        (sqlite3.DatabaseError, "opaque database detail", code("SQLITE_NOTADB", 26), "NS-DB-005"),
        (sqlite3.DatabaseError, "opaque schema detail", code("SQLITE_SCHEMA", 17), "NS-DB-005"),
    ]

    for error_type, raw_message, native_code, expected_code in cases:
        exception = error_type(raw_message)
        exception.sqlite_errorcode = native_code
        description = describe_unhandled_exception(exception)
        assert description.code == expected_code
        assert raw_message not in description.message
        assert raw_message not in description.log_reason
        assert "PRIVATE_TOKEN" not in description.message

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
