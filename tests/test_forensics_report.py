"""Pruebas de API e inmutabilidad del informe de examen versionado."""
from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.forensics_case_manifest import verify_case_manifest
from netsentinel.forensics_report import verify_examination_report
from netsentinel.main import app


def _case_payload():
    return {
        "case_number": "REPORT-LAB-001",
        "title": "Caso sintético para informe",
        "authority_reference": "AUTORIZACION-REPORT-001",
        "objective": "Validar el borrador de informe con datos artificiales.",
        "scope": "Solo fixture de API; ningún material real.",
        "examiner": "Examinador sintético",
        "actor": "Operador sintético",
    }


def _open_case(client):
    response = client.post(
        "/api/forensics/cases",
        json=_case_payload(),
        headers={"Origin": "http://127.0.0.1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _report_payload(**overrides):
    payload = {
        "title": "Informe de examen sintético",
        "examining_organization": "Laboratorio de pruebas",
        "request_date": "2026-10-21",
        "requester_name": "Solicitante sintético",
        "requester_organization": "Unidad de pruebas",
        "purpose": "Comprobar el flujo de generación y verificación del informe.",
        "scope_performed": "Solo caso, metadatos y una muestra artificial.",
        "processes_performed": "Se verificaron campos obligatorios y el expediente base.",
        "results": "El flujo de generación se ejecutó con datos sintéticos.",
        "conclusions": "No se formula una conclusión sobre evidencia real.",
        "conclusion_basis": "La conclusión se limita a la respuesta observada en esta prueba automatizada.",
        "limitations": "No hubo adquisición ni examen de evidencia real.",
        "deviations": "Ninguna desviación en el escenario automatizado.",
        "supporting_material": "Salida sintética de la prueba.",
        "original_disposition": "El original no existe; se usó una muestra artificial.",
        "derivative_disposition": "Los artefactos temporales quedan en el directorio aislado de pruebas.",
        "author_name": "Autor de pruebas",
        "authorizer_name": "Autorizador declarado no autenticado",
        "actor": "Operador sintético",
    }
    payload.update(overrides)
    return payload


def _register_evidence(client, case_id, *, label="Muestra sintética"):
    response = client.post(
        f"/api/forensics/cases/{case_id}/evidence",
        json={
            "label": label,
            "source_type": "file_copy",
            "original_name": "report-sample.bin",
            "source_description": "Contenido artificial para pruebas automatizadas.",
            "received_from": "Generador sintético",
            "received_by": "Examinador sintético",
            "received_at_original": "2026-10-21T10:00:00-03:00",
            "received_timezone": "America/Argentina/Cordoba",
            "actor": "Operador sintético",
            "size_bytes": 12,
        },
        headers={"Origin": "http://127.0.0.1"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_report_draft_exports_json_markdown_and_case_manifest_reference(monkeypatch, tmp_path):
    """El borrador contiene una captura verificable y se puede leer fuera de la app."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        evidence = _register_evidence(client, case["id"])
        response = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(results="Resultado sintético. <script>alert(1)</script>\n# encabezado falso\n![exfil](https://example.invalid/test.png)"),
            headers={"Origin": "http://127.0.0.1"},
        )
        listing = client.get(f"/api/forensics/cases/{case['id']}/reports")
        case_manifest_response = client.get(
            f"/api/forensics/cases/{case['id']}/manifest"
        )
        audit = client.get(f"/api/forensics/cases/{case['id']}/audit")

    assert response.status_code == 201, response.text
    saved = response.json()
    report = saved["report"]
    assert saved["version"] == 1
    assert saved["status"] == "draft_unsigned"
    assert saved["integrity_valid"] is True
    assert report["report"]["status"] == "draft_unsigned"
    assert report["report"]["authorization"]["status"] == "unsigned_pending_review"
    assert report["report"]["authorization"]["signature"] is None
    assert report["request"]["request_date"] == "2026-10-21"
    assert report["examination"]["processes_performed"].startswith("Se verificaron")
    assert report["source_case_manifest"]["evidence"][0]["id"] == evidence["id"]
    assert report["integrity"]["source_audit_chain_status"] == "valid"
    assert verify_examination_report(report) is True

    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == saved["id"]
    assert listing.json()["items"][0]["integrity_valid"] is True

    assert case_manifest_response.status_code == 200
    case_manifest = case_manifest_response.json()
    assert verify_case_manifest(case_manifest) is True
    assert case_manifest["summary"]["report_count"] == 1
    assert case_manifest["reports"][0]["report_sha256"] == saved["report_sha256"]
    audit_actions = [event["action"] for event in audit.json()["items"]]
    assert audit_actions[0] == "report_draft_created"

    with TestClient(app, base_url="http://127.0.0.1") as client:
        json_download = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{saved['id']}/json"
        )
        markdown_download = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{saved['id']}/markdown"
        )

    assert json_download.status_code == 200, json_download.text
    exported_report = json.loads(json_download.text)
    assert verify_examination_report(exported_report) is True
    assert exported_report["report_sha256"] == saved["report_sha256"]
    assert "draft_unsigned" == exported_report["report"]["status"]
    assert markdown_download.status_code == 200
    assert "BORRADOR SIN FIRMA" in markdown_download.text
    assert "Procedimientos realizados" in markdown_download.text
    assert "No hay firma digital" in markdown_download.text
    assert "&lt;script&gt;" in markdown_download.text
    assert "<script>" not in markdown_download.text
    assert "\\# encabezado falso" in markdown_download.text
    assert "\\!\\[exfil\\]\\(https://example.invalid/test.png\\)" in markdown_download.text
    assert "![exfil]" not in markdown_download.text
    assert str(tmp_path) not in json_download.text + markdown_download.text


def test_report_requires_valid_request_date_and_basis_for_conclusions(monkeypatch, tmp_path):
    """No se guarda un informe con fecha inválida o conclusiones sin fundamento."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        invalid_date = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(request_date="2026-02-31"),
            headers={"Origin": "http://127.0.0.1"},
        )
        no_basis = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(conclusions="Conclusión sin sustento.", conclusion_basis=""),
            headers={"Origin": "http://127.0.0.1"},
        )
        listed = client.get(f"/api/forensics/cases/{case['id']}/reports")

    assert invalid_date.status_code == 422
    assert "fecha de solicitud" in invalid_date.json()["detail"]
    assert no_basis.status_code == 422
    assert "datos que las sustentan" in no_basis.json()["detail"]
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_report_amendment_creates_immutable_next_version(monkeypatch, tmp_path):
    """Las correcciones generan una versión nueva y nunca reemplazan el documento anterior."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        first_response = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(),
            headers={"Origin": "http://127.0.0.1"},
        )
        first = first_response.json()

        missing_amendment = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(title="Corrección sin referencia"),
            headers={"Origin": "http://127.0.0.1"},
        )
        missing_reason = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(
                title="Corrección sin motivo",
                amends_report_id=first["id"],
            ),
            headers={"Origin": "http://127.0.0.1"},
        )
        amended = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(
                title="Informe de examen sintético — corrección",
                amends_report_id=first["id"],
                amendment_reason="Se corrigió una descripción del alcance.",
            ),
            headers={"Origin": "http://127.0.0.1"},
        )
        listing = client.get(f"/api/forensics/cases/{case['id']}/reports")

    assert first_response.status_code == 201, first_response.text
    assert missing_amendment.status_code == 409
    assert missing_reason.status_code == 422
    assert amended.status_code == 201, amended.text
    second = amended.json()
    assert second["version"] == 2
    assert second["amends_report_id"] == first["id"]
    assert second["report"]["report"]["amendment_reason"] == "Se corrigió una descripción del alcance."
    assert second["id"] != first["id"]
    assert first["report"]["report"]["version"] == 1
    assert first["report"]["report"]["title"] == "Informe de examen sintético"
    assert [item["version"] for item in listing.json()["items"]] == [2, 1]

    with database.connect() as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(
                "UPDATE forensic_reports SET title = 'cambio' WHERE id = ?",
                (first["id"],),
            )
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM forensic_reports WHERE id = ?", (first["id"],))


def test_markdown_export_escapes_html_and_keeps_evidence_inside_its_table(
    monkeypatch, tmp_path
):
    """Texto declarado no puede inyectar HTML ni nuevas filas en el informe legible."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        evidence = _register_evidence(
            client,
            case["id"],
            label="<img src=x>\n| fila fabricada",
        )
        created = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(results="<script>alert(1)</script>\n# título inyectado"),
            headers={"Origin": "http://127.0.0.1"},
        )
        assert created.status_code == 201, created.text
        report = created.json()
        markdown = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{report['id']}/markdown"
        )

    assert markdown.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in markdown.text
    assert "<script>alert(1)</script>" not in markdown.text
    assert "&lt;img src=x&gt;" in markdown.text
    assert "<img src=x>" not in markdown.text
    assert "&lt;img src=x&gt;<br>\\| fila fabricada" in markdown.text
    assert report["report"]["source_case_manifest"]["evidence"][0]["label"] == "<img src=x>\n| fila fabricada"
    assert evidence["id"] == report["report"]["source_case_manifest"]["evidence"][0]["id"]


def test_corrupted_report_is_not_exported(monkeypatch, tmp_path):
    """La API detecta un documento guardado alterado y bloquea ambas exportaciones."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        case = _open_case(client)
        saved_response = client.post(
            f"/api/forensics/cases/{case['id']}/reports",
            json=_report_payload(conclusions="", conclusion_basis=""),
            headers={"Origin": "http://127.0.0.1"},
        )
        assert saved_response.status_code == 201, saved_response.text
        saved = saved_response.json()
        with database.connect() as db:
            db.execute("DROP TRIGGER IF EXISTS forensic_reports_no_update")
            db.execute(
                "UPDATE forensic_reports SET report_json = ? WHERE id = ?",
                ('{"format":"modified"}', saved["id"]),
            )
        detail = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{saved['id']}"
        )
        json_download = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{saved['id']}/json"
        )
        markdown_download = client.get(
            f"/api/forensics/cases/{case['id']}/reports/{saved['id']}/markdown"
        )

    assert detail.status_code == 200
    assert detail.json()["integrity_valid"] is False
    assert json_download.status_code == 409
    assert markdown_download.status_code == 409
