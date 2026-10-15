"""Pruebas de API de casos y evidencia con datos sintéticos."""
from __future__ import annotations

import hashlib
import sqlite3

import pytest

from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.main import app


def _case_payload(**overrides):
    body = {
        "case_number": "LAB-2026-001",
        "title": "Caso de prueba",
        "authority_reference": "Autorización sintética AUT-001",
        "objective": "Practicar el registro de metadatos y su procedencia.",
        "scope": "Solo archivos sintéticos creados para las pruebas.",
        "examiner": "Examinador de prueba",
        "actor": "Operador de prueba",
    }
    body.update(overrides)
    return body


def _open_case(client):
    response = client.post(
        "/api/forensics/cases",
        json=_case_payload(),
        headers={"Origin": "http://127.0.0.1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_case_creation_requires_authority_scope_and_records_audit(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        created = _open_case(client)
        listed = client.get("/api/forensics/cases").json()
        audit = client.get(f"/api/forensics/cases/{created['id']}/audit").json()

    assert created["case_number"] == "LAB-2026-001"
    assert created["status"] == "open"
    assert created["evidence_count"] == 0
    assert len(listed["items"]) == 1
    assert listed["items"][0]["id"] == created["id"]
    assert [event["action"] for event in audit["items"]] == ["case_opened"]
    assert audit["items"][0]["details"]["case_number"] == "LAB-2026-001"


def test_duplicate_case_number_is_a_conflict(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        _open_case(client)
        response = client.post(
            "/api/forensics/cases",
            json=_case_payload(title="Otro título"),
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 409
    assert "Ya existe un caso" in response.json()["detail"]


def test_evidence_registration_stores_metadata_but_not_file_contents_or_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    expected_hash = hashlib.sha256(b"synthetic evidence fixture").hexdigest()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        response = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Exportación sintética",
                "source_type": "browser_export",
                "original_name": "browser-history.json",
                "source_description": "Exportación sintética de un perfil de prueba.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T09:30:00-03:00",
                "received_timezone": "America/Argentina/Cordoba",
                "size_bytes": 26,
                "reported_sha256": expected_hash,
                "hash_source": "Manifiesto de la muestra de prueba",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        listing = client.get(f"/api/forensics/cases/{case['id']}/evidence")
        updated_case = client.get(f"/api/forensics/cases/{case['id']}")
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert response.status_code == 201, response.text
    evidence = response.json()
    assert evidence["evidence_number"] == "E-0001"
    assert evidence["reported_sha256"] == expected_hash
    assert evidence["hash_status"] == "reported"
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1
    assert updated_case.json()["evidence_count"] == 1
    audit_actions = [entry["action"] for entry in audit.json()["items"]]
    assert audit_actions == ["evidence_registered", "case_opened"]
    assert "file_path" not in evidence
    assert "content" not in evidence
    assert str(tmp_path) not in response.text

    with TestClient(app, base_url="http://127.0.0.1") as client:
        second = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Segunda exportación sintética",
                "source_type": "browser_export",
                "source_description": "Segunda muestra de prueba.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T09:31:00-03:00",
                "received_timezone": "America/Argentina/Cordoba",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
    assert second.status_code == 201, second.text
    assert second.json()["evidence_number"] == "E-0002"


def test_evidence_name_rejects_full_paths_to_avoid_storing_private_directories(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        response = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Archivo sintético",
                "source_type": "file_copy",
                "original_name": r"C:\Users\Private\Desktop\evidence.bin",
                "source_description": "Muestra de prueba.",
                "received_from": "Operador de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 422
    assert "sin carpetas ni ruta completa" in response.json()["detail"]


def test_reported_hash_must_be_valid_and_identify_its_source(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        base = {
            "label": "Archivo de prueba",
            "source_type": "file_copy",
            "source_description": "Archivo sintético.",
            "received_from": "Operador de prueba",
            "received_at_original": "2026-10-15T12:00:00Z",
            "received_timezone": "UTC",
            "actor": "Operador de prueba",
        }
        invalid = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={**base, "reported_sha256": "not-a-hash", "hash_source": "Muestra"},
            headers={"Origin": "http://127.0.0.1"},
        )
        missing_source = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={**base, "reported_sha256": "a" * 64, "hash_source": "   "},
            headers={"Origin": "http://127.0.0.1"},
        )
        missing_offset = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                **base,
                "received_at_original": "2026-10-15T12:00:00",
            },
            headers={"Origin": "http://127.0.0.1"},
        )

    assert invalid.status_code == 422
    assert "64 caracteres hexadecimales" in invalid.json()["detail"]
    assert missing_source.status_code == 422
    assert "quién o qué herramienta informó" in missing_source.json()["detail"]
    assert missing_offset.status_code == 422
    assert "zona horaria o un offset" in missing_offset.json()["detail"]


def test_closed_case_keeps_history_and_rejects_new_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        close = client.post(
            f"/api/forensics/cases/{case['id']}/close",
            json={"actor": "Operador de prueba"},
            headers={"Origin": "http://127.0.0.1"},
        )
        evidence = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "No debe registrarse",
                "source_type": "other",
                "source_description": "Prueba posterior al cierre.",
                "received_from": "Operador de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert close.status_code == 200
    assert close.json()["status"] == "closed"
    assert evidence.status_code == 422
    assert "caso está cerrado" in evidence.json()["detail"]
    assert [row["action"] for row in audit.json()["items"]] == ["case_closed", "case_opened"]


def test_audit_rows_cannot_be_updated_or_deleted(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)

    with database.connect() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(
                "UPDATE forensic_audit SET result = 'changed' WHERE case_id = ?",
                (case["id"],),
            )
        with __import__("pytest").raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM forensic_audit WHERE case_id = ?", (case["id"],))


def test_hash_comparison_records_match_then_mismatch_without_storing_full_path(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    working_copy = tmp_path / "evidence.bin"
    original_content = b"approved synthetic evidence copy"
    working_copy.write_bytes(original_content)
    reported_hash = hashlib.sha256(original_content).hexdigest()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Copia sintética para comparar",
                "source_type": "file_copy",
                "original_name": "evidence.bin",
                "source_description": "Archivo sintético preparado para probar el flujo.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "size_bytes": len(original_content),
                "reported_sha256": reported_hash,
                "hash_source": "Manifiesto sintético",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        assert registered.status_code == 201, registered.text
        evidence_id = registered.json()["id"]
        verify_url = f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash"
        consent = {"source_path": str(working_copy), "actor": "Operador de prueba", "confirm_working_copy": True}

        first = client.post(verify_url, json=consent, headers={"Origin": "http://127.0.0.1"})
        working_copy.write_bytes(b"changed synthetic copy")
        second = client.post(verify_url, json=consent, headers={"Origin": "http://127.0.0.1"})

        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )
        evidence_listing = client.get(f"/api/forensics/cases/{case['id']}/evidence")
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert first.status_code == 200, first.text
    assert first.json()["status"] == "match"
    assert first.json()["copy_confirmed"] is True
    assert first.json()["calculated_sha256"] == reported_hash
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "mismatch"
    assert second.json()["expected_sha256"] == reported_hash
    assert second.json()["calculated_sha256"] == hashlib.sha256(b"changed synthetic copy").hexdigest()
    assert [item["status"] for item in checks.json()["items"]] == ["mismatch", "match"]
    assert all(item["copy_confirmed"] is True for item in checks.json()["items"])
    assert evidence_listing.json()["items"][0]["reported_sha256"] == reported_hash
    assert evidence_listing.json()["items"][0]["last_integrity_check_status"] == "mismatch"
    audit_actions = [event["action"] for event in audit.json()["items"]]
    assert audit_actions[:2] == ["evidence_hash_compared", "evidence_hash_compared"]
    combined_output = first.text + second.text + checks.text + evidence_listing.text + audit.text
    assert str(tmp_path) not in combined_output
    assert str(working_copy) not in combined_output

    with database.connect() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(
                "UPDATE forensic_integrity_checks SET status = 'match' WHERE evidence_id = ?",
                (evidence_id,),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(
                "DELETE FROM forensic_integrity_checks WHERE evidence_id = ?",
                (evidence_id,),
            )


def test_failed_hash_read_is_recorded_without_revealing_the_path(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    missing_path = tmp_path / "private-folder" / "missing-evidence.bin"
    reference_hash = hashlib.sha256(b"declared source bytes").hexdigest()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Fuente todavía no disponible",
                "source_type": "file_copy",
                "original_name": "missing-evidence.bin",
                "source_description": "Elemento sintético para probar errores de lectura.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "reported_sha256": reference_hash,
                "hash_source": "Manifiesto sintético",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        evidence_id = registered.json()["id"]
        url = f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash"
        result = client.post(
            url,
            json={
                "source_path": str(missing_path),
                "actor": "Operador de prueba",
                "confirm_working_copy": True,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert result.status_code == 422
    assert result.json()["detail"]["code"] == "NS-FORENSIC-INT-002"
    assert str(missing_path) not in result.text
    assert checks.json()["items"][0]["status"] == "failed"
    assert checks.json()["items"][0]["error_code"] == "NS-FORENSIC-INT-002"
    assert str(missing_path) not in checks.text + audit.text


def test_closed_case_rejects_hash_comparison_without_writing_a_new_check(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    working_copy = tmp_path / "evidence.bin"
    content = b"synthetic closed-case evidence"
    working_copy.write_bytes(content)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Copia sintética",
                "source_type": "file_copy",
                "source_description": "Prueba de cierre.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "reported_sha256": hashlib.sha256(content).hexdigest(),
                "hash_source": "Manifiesto sintético",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        evidence_id = registered.json()["id"]
        close = client.post(
            f"/api/forensics/cases/{case['id']}/close",
            json={"actor": "Operador de prueba"},
            headers={"Origin": "http://127.0.0.1"},
        )
        verify = client.post(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash",
            json={
                "source_path": str(working_copy),
                "actor": "Operador de prueba",
                "confirm_working_copy": True,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )

    assert close.status_code == 200
    assert verify.status_code == 409
    assert "caso está cerrado" in verify.json()["detail"]
    assert checks.json()["items"] == []


def test_hash_comparison_requires_explicit_working_copy_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    working_copy = tmp_path / "evidence.bin"
    working_copy.write_bytes(b"synthetic bytes")

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        expected_hash = hashlib.sha256(b"synthetic bytes").hexdigest()
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Copia sintética",
                "source_type": "file_copy",
                "source_description": "Muestra de prueba.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "reported_sha256": expected_hash,
                "hash_source": "Manifiesto sintético",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        evidence_id = registered.json()["id"]
        result = client.post(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash",
            json={
                "source_path": str(working_copy),
                "actor": "Operador de prueba",
                "confirm_working_copy": False,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )

    assert result.status_code == 422
    assert "Confirmá que el archivo elegido es una copia de trabajo" in result.json()["detail"]
    assert checks.json()["items"] == []
