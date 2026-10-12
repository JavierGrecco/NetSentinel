from fastapi.testclient import TestClient
import pytest

from netsentinel import database
from netsentinel.findings import build_findings
from netsentinel.local_discovery import Neighbor
from netsentinel.main import app


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_build_findings_preserves_evidence_and_separates_confidence_from_severity():
    events = [{
        "id": 4,
        "event_type": "new_device",
        "severity": "warning",
        "device_id": 8,
        "created_at": "2026-10-12T10:00:00+00:00",
        "message": "Primer avistamiento en la red local.",
        "acknowledged": 0,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "ip_address": "192.168.1.20",
        "display_name": "",
        "manufacturer": "Fabricante de prueba",
    }]
    incidents = [{
        "id": 9,
        "monitor_id": 2,
        "monitor_name": "Servicio de prueba",
        "kind": "tcp",
        "target": "192.168.1.10:443",
        "status": "open",
        "opened_at": "2026-10-12T10:02:00+00:00",
        "updated_at": "2026-10-12T10:03:00+00:00",
        "resolved_at": None,
        "failure_count": 2,
        "last_detail": "Tiempo de espera agotado",
    }]

    report = build_findings(events, incidents, state="active", limit=10)

    assert report["format"] == "netsentinel-findings-v1"
    assert report["summary"] == {
        "returned": 2,
        "active": 2,
        "acknowledged": 0,
        "resolved": 0,
    }
    assert [item["id"] for item in report["findings"]] == ["incident:9", "event:4"]
    incident = report["findings"][0]
    assert incident["confidence"]["level"] == "measured"
    assert incident["severity"] == "warning"
    assert "causa raíz" in incident["confidence"]["explanation"]
    event = report["findings"][1]
    assert event["confidence"]["level"] == "observed"
    assert event["asset"]["label"] == "Fabricante de prueba"
    assert event["evidence"]["message"] == "Primer avistamiento en la red local."
    assert event["recommended_action"]
    assert "No es un motor SIEM" in report["notice"]


def test_build_findings_filters_states_limits_results_and_omits_duplicate_monitor_events():
    events = [
        {"id": 1, "event_type": "new_device", "severity": "warning", "created_at": "2026-10-12T09:00:00+00:00", "message": "Nuevo", "acknowledged": 0},
        {"id": 2, "event_type": "ip_changed", "severity": "warning", "created_at": "2026-10-12T10:00:00+00:00", "message": "Cambio", "acknowledged": 1},
        {"id": 3, "event_type": "monitor_down", "severity": "warning", "created_at": "2026-10-12T10:01:00+00:00", "message": "Se duplica con el incidente", "acknowledged": 0},
    ]
    incidents = [{
        "id": 5, "monitor_id": 2, "monitor_name": "Servicio", "kind": "tcp",
        "target": "192.0.2.10:443", "status": "resolved",
        "opened_at": "2026-10-12T08:00:00+00:00",
        "updated_at": "2026-10-12T10:02:00+00:00",
        "resolved_at": "2026-10-12T10:02:00+00:00",
        "failure_count": 3, "last_detail": "Recuperado",
    }]

    assert [f["id"] for f in build_findings(events, incidents, state="active")["findings"]] == ["event:1"]
    assert [f["id"] for f in build_findings(events, incidents, state="acknowledged")["findings"]] == ["event:2"]
    assert [f["id"] for f in build_findings(events, incidents, state="resolved")["findings"]] == ["incident:5"]
    all_findings = build_findings(events, incidents, state="all", limit=10)["findings"]
    assert {f["id"] for f in all_findings} == {"event:1", "event:2", "incident:5"}
    assert len(build_findings(events, incidents, state="all", limit=1)["findings"]) == 1


@pytest.mark.parametrize("state", ["", "unknown", "open"])
def test_build_findings_rejects_unknown_state(state):
    with pytest.raises(ValueError, match="estado"):
        build_findings([], [], state=state)


@pytest.mark.parametrize("limit", [0, 201, True, "10"])
def test_build_findings_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="límite"):
        build_findings([], [], limit=limit)


def test_findings_api_combines_inventory_and_monitor_incident_without_duplicate(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "AA:BB:CC:DD:EE:01", "en0")])
    monitor = database.create_monitor("Servicio de prueba", "tcp", "192.168.5.10:443")
    database.record_monitor_check(monitor["id"], "down", None, "Tiempo de espera agotado")

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/findings?state=active")

    assert response.status_code == 200
    report = response.json()
    findings = report["findings"]
    assert response.headers["cache-control"] == "no-store"
    assert {item["category"] for item in findings} == {"inventory", "availability"}
    assert any(item["id"].startswith("event:") for item in findings)
    assert any(item["id"].startswith("incident:") for item in findings)
    assert not any(item["evidence"].get("event_type") == "monitor_down" for item in findings)
    assert all(item["source"]["system"] in {"inventory", "monitoring"} for item in findings)
    assert all("confidence" in item and "severity" in item for item in findings)


def test_findings_api_acknowledged_and_resolved_states_and_json_export(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.3", "AA:BB:CC:DD:EE:02", "en0")])
    event = next(item for item in database.get_events(limit=10) if item["event_type"] == "new_device")
    monitor = database.create_monitor("Servicio recuperable", "tcp", "192.168.5.11:443")
    database.record_monitor_check(monitor["id"], "down", None, "No responde")
    incident_id = database.get_incidents(status="open")[0]["id"]
    database.acknowledge_event(event["id"])
    database.record_monitor_check(monitor["id"], "up", 10.0, "Conexión recuperada")

    with TestClient(app, base_url="http://127.0.0.1") as client:
        acknowledged = client.get("/api/findings?state=acknowledged")
        resolved = client.get("/api/findings?state=resolved")
        exported = client.get("/api/export/findings.json?state=resolved")

    assert acknowledged.status_code == 200
    assert [item["id"] for item in acknowledged.json()["findings"]] == [f"event:{event['id']}"]
    assert resolved.status_code == 200
    assert [item["id"] for item in resolved.json()["findings"]] == [f"incident:{incident_id}"]
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("application/json")
    assert exported.headers["cache-control"] == "no-store"
    assert "attachment;" in exported.headers["content-disposition"]
    assert exported.json()["findings"][0]["status"] == "resolved"


def test_findings_api_rejects_invalid_state_and_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/findings?state=open").status_code == 422
        assert client.get("/api/findings?limit=201").status_code == 422

def test_findings_exclude_duplicate_monitor_events_before_applying_source_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.9", "AA:BB:CC:DD:EE:99", "en0")])
    inventory_event = next(
        item for item in database.get_events(limit=10)
        if item["event_type"] == "new_device"
    )
    monitor = database.create_monitor("Flapping service", "tcp", "192.168.5.10:443")

    # Generate newer transition events that are duplicates of the persisted incidents.
    for index in range(4):
        database.record_monitor_check(
            monitor["id"], "down", None, f"timeout {index}"
        )
        database.record_monitor_check(
            monitor["id"], "up", 10.0, f"recovered {index}"
        )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/findings?state=active&limit=1")

    assert response.status_code == 200
    report = response.json()
    assert [item["id"] for item in report["findings"]] == [
        f"event:{inventory_event['id']}"
    ]
    assert report["summary"]["returned"] == 1
    assert report["findings"][0]["evidence"]["event_type"] == "new_device"
