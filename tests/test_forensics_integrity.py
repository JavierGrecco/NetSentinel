"""Pruebas del cálculo inicial de integridad forense con archivos sintéticos."""
from __future__ import annotations

import hashlib
import pytest

from netsentinel.forensics_integrity import (
    ForensicIntegrityError,
    calculate_sha256,
)


def test_sha256_is_calculated_in_small_chunks_without_changing_file(tmp_path):
    source = tmp_path / "synthetic-evidence.bin"
    content = (b"synthetic forensic fixture\x00" * 37) + b"end"
    source.write_bytes(content)
    before = source.stat()

    result = calculate_sha256(source, chunk_size=11)

    assert result.algorithm == "SHA-256"
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.size_bytes == len(content)
    assert result.source_unchanged_during_read is True
    assert result.verified_at_utc.endswith("Z")
    assert source.read_bytes() == content
    after = source.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)


@pytest.mark.parametrize("chunk_size", [0, -1, True, 1.5, "1024"])
def test_invalid_chunk_size_returns_clear_error_code(tmp_path, chunk_size):
    source = tmp_path / "fixture.bin"
    source.write_bytes(b"fixture")

    with pytest.raises(ForensicIntegrityError) as error:
        calculate_sha256(source, chunk_size=chunk_size)

    assert error.value.code == "NS-FORENSIC-INT-001"
    assert "entero mayor que cero" in str(error.value)


def test_missing_file_returns_clear_error_without_echoing_path(tmp_path):
    source = tmp_path / "does-not-exist-private-name.bin"

    with pytest.raises(ForensicIntegrityError) as error:
        calculate_sha256(source)

    assert error.value.code == "NS-FORENSIC-INT-002"
    assert str(source) not in str(error.value)


@pytest.mark.parametrize("invalid_path", [None, b"fixture.bin", "bad\x00path.bin"])
def test_invalid_path_values_return_a_clear_error(invalid_path):
    with pytest.raises(ForensicIntegrityError) as error:
        calculate_sha256(invalid_path)

    assert error.value.code == "NS-FORENSIC-INT-001"


def test_directory_is_not_accepted_as_evidence_file(tmp_path):
    with pytest.raises(ForensicIntegrityError) as error:
        calculate_sha256(tmp_path)

    assert error.value.code == "NS-FORENSIC-INT-005"


def test_symbolic_link_is_rejected_when_platform_supports_it(tmp_path):
    source = tmp_path / "fixture.bin"
    source.write_bytes(b"fixture")
    link = tmp_path / "fixture-link.bin"

    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("Symbolic links are not available in this test environment.")

    with pytest.raises(ForensicIntegrityError) as error:
        calculate_sha256(link)

    assert error.value.code == "NS-FORENSIC-INT-004"


def test_empty_file_has_the_standard_empty_sha256(tmp_path):
    source = tmp_path / "empty.bin"
    source.write_bytes(b"")

    result = calculate_sha256(source)

    assert result.sha256 == hashlib.sha256(b"").hexdigest()
    assert result.size_bytes == 0
