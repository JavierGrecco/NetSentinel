"""Pruebas de API de casos y evidencia con datos sintéticos."""
from __future__ import annotations

import hashlib
import os
import sqlite3
import stat

import pytest

from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.forensics_audit_manifest import verify_audit_manifest
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
    assert audit["items"][0]["integrity_status"] == "valid"
    assert len(audit["items"][0]["event_hash"]) == 64
    assert audit["items"][0]["previous_event_hash"] is None


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

        chain_row = db.execute(
            "SELECT audit_id FROM forensic_audit_chain WHERE case_id = ? LIMIT 1",
            (case["id"],),
        ).fetchone()
        assert chain_row is not None
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(
                "UPDATE forensic_audit_chain SET event_hash = ? WHERE audit_id = ?",
                ("0" * 64, chain_row["audit_id"]),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM forensic_audit_chain WHERE audit_id = ?", (chain_row["audit_id"],))


def test_audit_chain_detects_tampering_in_an_earlier_event(monkeypatch, tmp_path):
    """Una modificación del evento inicial invalida ese evento y los siguientes."""
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
        assert close.status_code == 200
        before = client.get(f"/api/forensics/cases/{case['id']}/audit")
        assert all(item["integrity_status"] == "valid" for item in before.json()["items"])

        with database.connect() as db:
            first = db.execute(
                "SELECT id FROM forensic_audit WHERE case_id = ? ORDER BY id ASC LIMIT 1",
                (case["id"],),
            ).fetchone()
            assert first is not None
            db.execute("DROP TRIGGER forensic_audit_no_update")
            db.execute(
                "UPDATE forensic_audit SET action = 'tampered_event' WHERE id = ?",
                (first["id"],),
            )

        after = client.get(f"/api/forensics/cases/{case['id']}/audit")
        assert after.status_code == 200
        items = after.json()["items"]
        assert len(items) == 2
        assert [item["integrity_status"] for item in items] == ["invalid", "invalid"]
        assert items[1]["action"] == "tampered_event"


def test_audit_chain_marks_missing_entry_and_invalidates_following_events(monkeypatch, tmp_path):
    """Un eslabón faltante se informa; no se reconstruye al consultar el historial."""
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
        assert close.status_code == 200

        with database.connect() as db:
            first = db.execute(
                "SELECT id FROM forensic_audit WHERE case_id = ? ORDER BY id ASC LIMIT 1",
                (case["id"],),
            ).fetchone()
            assert first is not None
            db.execute("DROP TRIGGER IF EXISTS forensic_audit_chain_no_delete")
            db.execute(
                "DELETE FROM forensic_audit_chain WHERE audit_id = ?",
                (first["id"],),
            )

        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")
        assert audit.status_code == 200
        items = audit.json()["items"]

    # La respuesta está ordenada de más reciente a más antiguo.
    assert [item["action"] for item in items] == ["case_closed", "case_opened"]
    assert [item["integrity_status"] for item in items] == ["invalid", "missing"]
    assert items[0]["event_hash"] is not None
    assert items[1]["event_hash"] is None


def test_audit_chain_detects_moved_entry_without_cross_case_contamination(monkeypatch, tmp_path):
    """Una fila asignada a otro caso se detecta y no altera la cadena legítima."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        first_case = _open_case(client)
        created = client.post(
            "/api/forensics/cases",
            json=_case_payload(case_number="LAB-2026-002", title="Segundo caso sintético"),
            headers={"Origin": "http://127.0.0.1"},
        )
        assert created.status_code == 201, created.text
        second_case = created.json()

        with database.connect() as db:
            second_audit = db.execute(
                "SELECT id FROM forensic_audit WHERE case_id = ? ORDER BY id ASC LIMIT 1",
                (second_case["id"],),
            ).fetchone()
            assert second_audit is not None
            db.execute("DROP TRIGGER IF EXISTS forensic_audit_chain_no_update")
            db.execute(
                "UPDATE forensic_audit_chain SET case_id = ? WHERE audit_id = ?",
                (first_case["id"], second_audit["id"]),
            )

        close = client.post(
            f"/api/forensics/cases/{first_case['id']}/close",
            json={"actor": "Operador de prueba"},
            headers={"Origin": "http://127.0.0.1"},
        )
        assert close.status_code == 200
        first_audit = client.get(f"/api/forensics/cases/{first_case['id']}/audit")
        second_audit_response = client.get(f"/api/forensics/cases/{second_case['id']}/audit")

    assert first_audit.status_code == 200
    assert [item["integrity_status"] for item in first_audit.json()["items"]] == ["valid", "valid"]
    assert second_audit_response.status_code == 200
    second_items = second_audit_response.json()["items"]
    assert len(second_items) == 1
    assert second_items[0]["integrity_status"] == "invalid"


def test_audit_chain_migration_backfills_existing_events_once(monkeypatch, tmp_path):
    """Al actualizar una base anterior se encadenan sus eventos sin perderlos."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        assert client.get(f"/api/forensics/cases/{case['id']}/audit").json()["items"][0]["integrity_status"] == "valid"
        with database.connect() as db:
            db.execute("DROP TRIGGER IF EXISTS forensic_audit_chain_no_update")
            db.execute("DROP TRIGGER IF EXISTS forensic_audit_chain_no_delete")
            db.execute("DROP TABLE forensic_audit_chain")

        database.initialize()
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")
        assert audit.status_code == 200
        assert len(audit.json()["items"]) == 1
        assert audit.json()["items"][0]["integrity_status"] == "valid"
        assert len(audit.json()["items"][0]["event_hash"]) == 64


def test_hash_comparison_records_match_then_mismatch_without_storing_full_path(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    working_copy_dir = tmp_path / "forensics-working-copies"
    working_copy_dir.mkdir(parents=True, exist_ok=True)
    working_copy = working_copy_dir / "evidence.bin"
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
        consent = {"source_name": "evidence.bin", "actor": "Operador de prueba", "confirm_working_copy": True}

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
    missing_name = "missing-evidence.bin"
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
                "source_name": missing_name,
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
    assert str(tmp_path) not in result.text
    assert checks.json()["items"][0]["status"] == "failed"
    assert checks.json()["items"][0]["error_code"] == "NS-FORENSIC-INT-002"
    assert str(tmp_path) not in checks.text + audit.text


def test_closed_case_rejects_hash_comparison_without_writing_a_new_check(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    working_copy_dir = tmp_path / "forensics-working-copies"
    working_copy_dir.mkdir(parents=True, exist_ok=True)
    working_copy = working_copy_dir / "evidence.bin"
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
                "source_name": "evidence.bin",
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


def test_hash_comparison_without_reference_hash_is_a_conflict(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Copia sintética sin hash",
                "source_type": "file_copy",
                "source_description": "Prueba sin hash de referencia.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        evidence_id = registered.json()["id"]
        result = client.post(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash",
            json={
                "source_name": "never-read.bin",
                "actor": "Operador de prueba",
                "confirm_working_copy": True,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )

    assert registered.status_code == 201
    assert result.status_code == 409
    assert "SHA-256 de referencia" in result.json()["detail"]
    assert checks.json()["items"] == []


def test_hash_comparison_requires_explicit_working_copy_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    working_copy_dir = tmp_path / "forensics-working-copies"
    working_copy_dir.mkdir(parents=True, exist_ok=True)
    working_copy = working_copy_dir / "evidence.bin"
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
                "source_name": "evidence.bin",
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


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../outside.bin",
        r"..\outside.bin",
        "/etc/passwd",
        r"C:\Windows\win.ini",
        "..",
        "NUL.txt",
        "COM1.log",
        "",
        "   ",
        "x" * 256,
        "bad\x01name.bin",
    ],
)
def test_hash_comparison_rejects_paths_and_traversal_names(monkeypatch, tmp_path, unsafe_name):
    """La API acepta nombres de archivo, no rutas arbitrarias del equipo."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        reference_hash = hashlib.sha256(b"synthetic evidence").hexdigest()
        registered = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Copia sintética",
                "source_type": "file_copy",
                "source_description": "Prueba de validación de nombres.",
                "received_from": "Responsable de prueba",
                "received_at_original": "2026-10-15T12:00:00Z",
                "received_timezone": "UTC",
                "reported_sha256": reference_hash,
                "hash_source": "Manifiesto sintético",
                "actor": "Operador de prueba",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        assert registered.status_code == 201, registered.text
        evidence_id = registered.json()["id"]
        response = client.post(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/verify-hash",
            json={
                "source_name": unsafe_name,
                "actor": "Operador de prueba",
                "confirm_working_copy": True,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        checks = client.get(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence_id}/integrity-checks"
        )
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert response.status_code == 422
    assert "nombre no es válido" in response.json()["detail"]["message"]
    assert response.json()["detail"]["code"] == "NS-FORENSIC-INT-014"
    check_items = checks.json()["items"]
    assert len(check_items) == 1
    assert check_items[0]["status"] == "failed"
    assert check_items[0]["error_code"] == "NS-FORENSIC-INT-014"
    assert check_items[0]["source_name"] == "[nombre rechazado]"
    if unsafe_name:
        assert unsafe_name not in response.text + checks.text + audit.text
    assert str(tmp_path) not in response.text + checks.text + audit.text


def test_safe_working_copy_name_allows_double_dots_inside_a_name():
    """Dos puntos seguidos dentro del nombre no lo convierten en una ruta."""
    from netsentinel.forensics_service import _is_safe_file_name

    assert _is_safe_file_name("file..backup.bin") is True
    assert _is_safe_file_name("evidence.v2.bin") is True


@pytest.mark.parametrize(
    "unsafe_name",
    [
        ".",
        "..",
        "../outside.bin",
        r"..\outside.bin",
        "C:evidence.bin",
        "NUL.txt",
        "report.pdf.",
        "report.pdf ",
    ],
)
def test_safe_working_copy_name_rejects_nonportable_names(unsafe_name):
    """El mismo filtro se usa para nombres originales y copias de trabajo."""
    from netsentinel.forensics_service import _is_safe_file_name

    assert _is_safe_file_name(unsafe_name) is False



@pytest.mark.skipif(os.name != "posix", reason="Los permisos POSIX no se aplican en Windows.")
def test_existing_working_copy_directory_is_restricted_to_current_user(monkeypatch, tmp_path):
    """Una carpeta existente con permisos abiertos se endurece antes de usarse."""
    from netsentinel.forensics_service import _working_copy_path

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    workspace = tmp_path / "forensics-working-copies"
    workspace.mkdir()
    os.chmod(workspace, 0o755)

    resolved = _working_copy_path("evidence.bin")

    assert resolved == workspace.resolve() / "evidence.bin"
    assert stat.S_IMODE(workspace.stat().st_mode) == 0o700


@pytest.mark.skipif(os.name != "posix", reason="Los permisos POSIX no se aplican en Windows.")
def test_working_copy_directory_fails_closed_when_permissions_cannot_be_restricted(
    monkeypatch, tmp_path
):
    """No se inicia una lectura cuando no se pueden proteger las copias."""
    from netsentinel import forensics_service
    from netsentinel.forensics_integrity import ForensicIntegrityError

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    workspace = tmp_path / "forensics-working-copies"
    workspace.mkdir()

    def deny_permission_change(*_args):
        raise PermissionError("synthetic permission failure")

    monkeypatch.setattr(forensics_service.os, "fchmod", deny_permission_change)

    with pytest.raises(ForensicIntegrityError) as error:
        forensics_service._working_copy_path("evidence.bin")

    assert error.value.code == "NS-FORENSIC-INT-015"
    assert str(tmp_path) not in str(error.value)


def test_audit_manifest_export_is_complete_chronological_and_verifiable(monkeypatch, tmp_path):
    """El manifiesto incluye todo el historial y se verifica fuera de SQLite."""
    import json

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
        assert close.status_code == 200
        response = client.get(f"/api/forensics/cases/{case['id']}/audit/manifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment;" in response.headers["content-disposition"]
    manifest = json.loads(response.text)
    assert manifest["format"] == "netsentinel-forensic-audit-manifest"
    assert manifest["schema_version"] == 1
    assert manifest["case"]["id"] == case["id"]
    assert manifest["integrity"] == {
        "status": "valid",
        "event_count": 2,
        "valid_count": 2,
        "invalid_count": 0,
        "missing_count": 0,
    }
    assert [event["action"] for event in manifest["events"]] == [
        "case_opened",
        "case_closed",
    ]
    assert verify_audit_manifest(manifest) is True

    manifest["events"][0]["action"] = "modified_after_export"
    assert verify_audit_manifest(manifest) is False


def test_audit_manifest_export_marks_preexisting_chain_tampering(monkeypatch, tmp_path):
    """El manifiesto refleja corrupción previa en vez de declarar la cadena válida."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        with database.connect() as db:
            first = db.execute(
                "SELECT id FROM forensic_audit WHERE case_id = ? ORDER BY id ASC LIMIT 1",
                (case["id"],),
            ).fetchone()
            assert first is not None
            db.execute("DROP TRIGGER IF EXISTS forensic_audit_no_update")
            db.execute(
                "UPDATE forensic_audit SET action = 'tampered_after_creation' WHERE id = ?",
                (first["id"],),
            )
        response = client.get(f"/api/forensics/cases/{case['id']}/audit/manifest")

    assert response.status_code == 200
    manifest = response.json()
    assert manifest["integrity"]["status"] == "invalid"
    assert manifest["integrity"]["invalid_count"] == 1
    assert verify_audit_manifest(manifest) is True
