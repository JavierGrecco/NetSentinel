"""Pruebas unitarias del caso de uso de hallazgos, sin levantar FastAPI."""
from __future__ import annotations

import pytest

from netsentinel import findings_service


def _install_fakes(monkeypatch, *, events=None, incidents=None):
    """Instala dependencias controladas y registra las consultas realizadas."""
    calls = {"events": [], "incidents": []}
    event_result = events if events is not None else [{"id": "event"}]
    incident_result = incidents if incidents is not None else [{"id": "incident"}]

    def get_events(**kwargs):
        calls["events"].append(kwargs)
        return event_result

    def get_incidents(**kwargs):
        calls["incidents"].append(kwargs)
        return incident_result

    def build_findings(source_events, source_incidents, *, state, limit):
        return {
            "events": source_events,
            "incidents": source_incidents,
            "state": state,
            "limit": limit,
        }

    monkeypatch.setattr(findings_service.database, "get_events", get_events)
    monkeypatch.setattr(findings_service.database, "get_incidents", get_incidents)
    monkeypatch.setattr(findings_service, "build_findings", build_findings)
    return calls


def test_active_report_reads_unacknowledged_events_and_open_incidents(monkeypatch):
    calls = _install_fakes(monkeypatch)

    report = findings_service.collect_findings_report("active", 15)

    assert report["state"] == "active"
    assert report["limit"] == 15
    assert calls["events"] == [{
        "limit": 15,
        "acknowledged": False,
        "exclude_event_types": ("monitor_down", "monitor_recovered"),
    }]
    assert calls["incidents"] == [{"limit": 15, "status": "open"}]


def test_acknowledged_report_only_reads_acknowledged_events(monkeypatch):
    calls = _install_fakes(monkeypatch)

    report = findings_service.collect_findings_report("acknowledged", 20)

    assert report["events"]
    assert report["incidents"] == []
    assert calls["events"] == [{
        "limit": 20,
        "acknowledged": True,
        "exclude_event_types": ("monitor_down", "monitor_recovered"),
    }]
    assert calls["incidents"] == []


def test_resolved_report_only_reads_resolved_incidents(monkeypatch):
    calls = _install_fakes(monkeypatch, events=[])

    report = findings_service.collect_findings_report("resolved", 30)

    assert report["events"] == []
    assert report["incidents"]
    assert calls["events"] == []
    assert calls["incidents"] == [{"limit": 30, "status": "resolved"}]


def test_all_report_reads_all_events_and_incidents_with_limit(monkeypatch):
    calls = _install_fakes(monkeypatch)

    report = findings_service.collect_findings_report("all", 40)

    assert report["events"]
    assert report["incidents"]
    assert calls["events"] == [{
        "limit": 40,
        "exclude_event_types": ("monitor_down", "monitor_recovered"),
    }]
    assert calls["incidents"] == [{"limit": 40}]


def test_invalid_state_is_rejected_before_any_database_read(monkeypatch):
    calls = _install_fakes(monkeypatch)

    with pytest.raises(ValueError, match="active, acknowledged, resolved or all"):
        findings_service.collect_findings_report("open", 10)

    assert calls == {"events": [], "incidents": []}
