"""Prueba de API para el manifiesto consolidado del expediente."""
from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.forensics_case_manifest import verify_case_manifest
from netsentinel.main import app


def _case_payload():
    return {
        "case_number": "MANIFEST-API-001",
        "title": "Caso de manifiesto sintético",
        "authority_reference": "AUT-TEST-001",
        "objective": "Verificar la exportación consolidada del expediente.",
        "scope": "Solo datos y archivos sintéticos.",
        "examiner": "Examinador de pruebas",
        "actor": "Operador de pruebas",
    }


def test_consolidated_case_manifest_includes_evidence_checks_and_audit(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    payload_bytes = b"NetSentinel synthetic evidence v1"
    source_name = "synthetic-evidence.bin"
    working_copies = tmp_path / "forensics-working-copies"
    working_copies.mkdir()
    (working_copies / source_name).write_bytes(payload_bytes)
    source_hash = hashlib.sha256(payload_bytes).hexdigest()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case_response = client.post(
            "/api/forensics/cases",
            json=_case_payload(),
            headers={"Origin": "http://127.0.0.1"},
        )
        assert case_response.status_code == 201, case_response.text
        case = case_response.json()

        evidence_response = client.post(
            f"/api/forensics/cases/{case['id']}/evidence",
            json={
                "label": "Archivo sintético de prueba",
                "source_type": "file_copy",
                "original_name": source_name,
                "source_description": "Archivo generado exclusivamente para este test.",
                "received_from": "Fixture automatizada",
                "received_at_original": "2026-10-20T10:00:00-03:00",
                "received_timezone": "America/Argentina/Cordoba",
                "size_bytes": len(payload_bytes),
                "reported_sha256": source_hash,
                "hash_source": "SHA-256 calculado por la fixture de prueba",
                "actor": "Operador de pruebas",
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        assert evidence_response.status_code == 201, evidence_response.text
        evidence = evidence_response.json()

        check_response = client.post(
            f"/api/forensics/cases/{case['id']}/evidence/{evidence['id']}/verify-hash",
            json={
                "source_name": source_name,
                "actor": "Operador de pruebas",
                "confirm_working_copy": True,
            },
            headers={"Origin": "http://127.0.0.1"},
        )
        assert check_response.status_code == 200, check_response.text
        assert check_response.json()["status"] == "match"

        response = client.get(f"/api/forensics/cases/{case['id']}/manifest")

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment;" in response.headers["content-disposition"]
    assert "netsentinel-forensic-case-manifest.json" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"

    manifest = response.json()
    assert verify_case_manifest(manifest) is True
    assert manifest["format"] == "netsentinel-forensic-case-manifest"
    assert manifest["schema_version"] == 1
    assert manifest["case"]["authority_reference"] == "AUT-TEST-001"
    assert len(manifest["evidence"]) == 1
    exported_evidence = manifest["evidence"][0]
    assert exported_evidence["id"] == evidence["id"]
    assert exported_evidence["reported_sha256"] == source_hash
    assert exported_evidence["integrity_checks"][0]["status"] == "match"
    assert exported_evidence["integrity_checks"][0]["calculated_sha256"] == source_hash
    assert manifest["summary"]["audit_event_count"] == 3
    assert manifest["summary"]["integrity_check_count"] == 1
    assert manifest["summary"]["matching_check_count"] == 1
    assert manifest["summary"]["audit_chain_status"] == "valid"
    assert [entry["action"] for entry in manifest["audit_manifest"]["events"]] == [
        "case_opened",
        "evidence_registered",
        "evidence_hash_compared",
    ]
    # El expediente no contiene el contenido binario ni una ruta absoluta de la copia.
    assert payload_bytes.decode("ascii") not in response.text
    assert str(tmp_path) not in response.text
    assert "full_path" not in response.text
    assert "file_contents" not in response.text
