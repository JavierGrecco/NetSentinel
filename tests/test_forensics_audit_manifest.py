"""Pruebas del manifiesto de auditoría que no dependen de SQLite."""
from __future__ import annotations

from netsentinel.forensics_audit_manifest import (
    build_audit_manifest,
    verify_audit_manifest,
)


def test_manifest_digest_is_stable_for_the_same_payload():
    case = {
        "id": "case-1",
        "case_number": "LAB-001",
        "title": "Caso sintético",
        "status": "closed",
        "created_at": "2026-10-16T12:00:00Z",
        "updated_at": "2026-10-16T12:10:00Z",
    }
    events = [
        {
            "id": 1,
            "case_id": "case-1",
            "action": "case_opened",
            "details": {"scope": "synthetic"},
            "integrity_status": "valid",
        }
    ]
    first = build_audit_manifest(case=case, events=events, exported_at="2026-10-16T12:15:00Z")
    second = build_audit_manifest(case=case, events=events, exported_at="2026-10-16T12:15:00Z")

    assert first == second
    assert verify_audit_manifest(first) is True
    assert first["integrity"]["status"] == "valid"
    assert first["integrity"]["event_count"] == 1


def test_manifest_summary_reports_invalid_and_missing_entries():
    manifest = build_audit_manifest(
        case={"id": "case-2", "case_number": "LAB-002"},
        events=[
            {"id": 1, "integrity_status": "valid"},
            {"id": 2, "integrity_status": "missing"},
            {"id": 3, "integrity_status": "invalid"},
        ],
        exported_at="2026-10-16T12:15:00Z",
    )

    assert manifest["integrity"] == {
        "status": "invalid",
        "event_count": 3,
        "valid_count": 1,
        "invalid_count": 1,
        "missing_count": 1,
    }
    assert verify_audit_manifest(manifest) is True


def test_manifest_verifier_rejects_changed_payload_or_unsupported_format():
    manifest = build_audit_manifest(
        case={"id": "case-3", "case_number": "LAB-003"},
        events=[{"id": 1, "integrity_status": "valid"}],
        exported_at="2026-10-16T12:15:00Z",
    )
    changed = {**manifest, "events": [{"id": 1, "integrity_status": "invalid"}]}
    unsupported = {**manifest, "schema_version": 99}

    assert verify_audit_manifest(changed) is False
    assert verify_audit_manifest(unsupported) is False
    assert verify_audit_manifest(None) is False
