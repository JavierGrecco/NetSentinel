"""Pruebas sintéticas del manifiesto consolidado del expediente forense."""
from __future__ import annotations

from copy import deepcopy

from netsentinel.forensics_audit_manifest import build_audit_manifest
from netsentinel.forensics_case_manifest import (
    build_case_manifest,
    verify_case_manifest,
)


def _audit(status: str = "valid") -> dict:
    case = {
        "id": "case-id",
        "case_number": "LAB-001",
        "title": "Caso sintético",
        "status": "open",
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-20T10:01:00Z",
    }
    events = [{
        "id": 1,
        "case_id": "case-id",
        "action": "case_opened",
        "details": {"scope": "fixture sintética"},
        "integrity_status": status,
    }]
    return build_audit_manifest(
        case=case,
        events=events,
        exported_at="2026-10-20T10:02:00Z",
    )


def _sample():
    case = {
        "id": "case-id",
        "case_number": "LAB-001",
        "title": "Caso sintético",
        "authority_reference": "AUT-TEST",
        "objective": "Comprobar exportación",
        "scope": "Solo fixtures sintéticas",
        "examiner": "Examinador de prueba",
        "status": "open",
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-20T10:01:00Z",
        "evidence_count": 1,
    }
    evidence = [{
        "id": "evidence-id",
        "case_id": "case-id",
        "evidence_number": "E-0001",
        "label": "Archivo sintético",
        "source_type": "file_copy",
        "original_name": "synthetic.bin",
        "source_description": "Muestra artificial para pruebas.",
        "received_from": "Fixture",
        "received_by": "Examinador sintético",
        "received_at_original": "2026-10-20T09:00:00-03:00",
        "received_timezone": "America/Argentina/Cordoba",
        "size_bytes": 12,
        "reported_sha256": "a" * 64,
        "hash_source": "Fixture de pruebas",
        "created_at": "2026-10-20T10:01:00Z",
        "hash_status": "reported",
        "last_integrity_check_status": "match",
        "last_integrity_check_at": "2026-10-20T10:01:30Z",
        "last_calculated_sha256": "a" * 64,
        "integrity_checks": [{
            "id": 1,
            "case_id": "case-id",
            "evidence_id": "evidence-id",
            "checked_at": "2026-10-20T10:01:30Z",
            "actor": "Examinador de prueba",
            "copy_confirmed": True,
            "algorithm": "SHA-256",
            "source_name": "synthetic.bin",
            "expected_sha256": "a" * 64,
            "calculated_sha256": "a" * 64,
            "size_bytes": 12,
            "status": "match",
            "tool_version": "0.10.0.dev0",
            "error_code": None,
            "error_message": None,
        }],
    }]
    return case, evidence


def test_case_manifest_is_self_contained_and_has_a_stable_digest():
    case, evidence = _sample()
    kwargs = {
        "case": case,
        "evidence": evidence,
        "audit_manifest": _audit(),
        "exported_at": "2026-10-20T10:02:00Z",
    }
    first = build_case_manifest(**kwargs)
    second = build_case_manifest(**kwargs)

    assert first == second
    assert verify_case_manifest(first) is True
    assert first["evidence"][0]["received_by"] == "Examinador sintético"
    assert first["format"] == "netsentinel-forensic-case-manifest"
    assert first["schema_version"] == 1
    assert first["case"]["authority_reference"] == "AUT-TEST"
    assert first["evidence"][0]["integrity_checks"][0]["status"] == "match"
    assert first["audit_manifest"]["integrity"]["status"] == "valid"
    assert first["summary"] == {
        "evidence_count": 1,
        "report_count": 0,
        "evidence_with_reported_hash": 1,
        "evidence_without_reported_hash": 0,
        "integrity_check_count": 1,
        "matching_check_count": 1,
        "mismatching_check_count": 0,
        "failed_check_count": 0,
        "audit_event_count": 1,
        "audit_chain_status": "valid",
    }
    assert "file_contents" not in first["evidence"][0]
    assert "full_path" not in first["evidence"][0]


def test_case_manifest_digest_detects_changed_case_or_evidence():
    case, evidence = _sample()
    manifest = build_case_manifest(
        case=case,
        evidence=evidence,
        audit_manifest=_audit(),
        exported_at="2026-10-20T10:02:00Z",
    )

    changed_case = deepcopy(manifest)
    changed_case["case"]["scope"] = "scope alterado"
    assert verify_case_manifest(changed_case) is False

    changed_evidence = deepcopy(manifest)
    changed_evidence["evidence"][0]["integrity_checks"][0]["calculated_sha256"] = "b" * 64
    assert verify_case_manifest(changed_evidence) is False


def test_case_manifest_requires_supported_format_and_a_valid_inner_audit_digest():
    case, evidence = _sample()
    manifest = build_case_manifest(
        case=case,
        evidence=evidence,
        audit_manifest=_audit(),
        exported_at="2026-10-20T10:02:00Z",
    )

    unsupported = deepcopy(manifest)
    unsupported["schema_version"] = 99
    assert verify_case_manifest(unsupported) is False

    changed_audit = deepcopy(manifest)
    changed_audit["audit_manifest"]["events"][0]["action"] = "changed"
    # La huella externa sigue intacta, pero el digest de auditoría interno ya no coincide.
    assert verify_case_manifest(changed_audit) is False


def test_case_manifest_keeps_a_broken_audit_status_visible():
    case, evidence = _sample()
    manifest = build_case_manifest(
        case=case,
        evidence=evidence,
        audit_manifest=_audit("invalid"),
        exported_at="2026-10-20T10:02:00Z",
    )

    assert verify_case_manifest(manifest) is True
    assert manifest["summary"]["audit_chain_status"] == "invalid"
    assert manifest["audit_manifest"]["integrity"]["invalid_count"] == 1


def test_case_manifest_includes_report_references_in_its_digest():
    """El índice de informes forma parte del manifiesto consolidado del expediente."""
    case, evidence = _sample()
    reports = [{
        "id": "report-id",
        "case_id": "case-id",
        "version": 1,
        "title": "Informe sintético",
        "status": "draft_unsigned",
        "created_at": "2026-10-22T12:00:00Z",
        "created_by": "Autor sintético",
        "amends_report_id": None,
        "report_sha256": "c" * 64,
    }]
    manifest = build_case_manifest(
        case=case,
        evidence=evidence,
        audit_manifest=_audit(),
        exported_at="2026-10-22T12:01:00Z",
        reports=reports,
    )

    assert verify_case_manifest(manifest) is True
    assert manifest["summary"]["report_count"] == 1
    assert manifest["reports"][0]["id"] == "report-id"
    changed = deepcopy(manifest)
    changed["reports"][0]["report_sha256"] = "d" * 64
    assert verify_case_manifest(changed) is False
