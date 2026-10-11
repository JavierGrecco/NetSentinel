import pytest
from fastapi.testclient import TestClient

import netsentinel.main as main_module

from importlib.metadata import version as installed_version

from netsentinel import __version__, database
from netsentinel.main import app
from netsentinel.discovery import Neighbor


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_api_health_and_dashboard(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        page = client.get("/")
        assert page.status_code == 200
        assert "NetSentinel" in page.text
        assert client.get("/api/devices").json() == []
        assert client.get("/api/scans").json() == []
        assert client.get("/api/export/data.json").json()["format"] == "netsentinel-data-export-v3"


def test_api_device_trust_and_acknowledgement(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "AA:BB:CC:DD:EE:FF", "en0")])
    with TestClient(app) as client:
        device = client.get("/api/devices").json()[0]
        response = client.patch(f"/api/devices/{device['id']}", json={"trusted": True, "display_name": "Router de prueba"})
        assert response.status_code == 200
        assert response.json()["trusted"] is True
        event = client.get("/api/events").json()[0]
        response = client.patch(f"/api/events/{event['id']}", json={"acknowledged": True})
        assert response.status_code == 200


def test_api_scan_history_and_device_addresses(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "00:11:22:33:44:55", "en0")])
    with TestClient(app) as client:
        assert client.get("/api/scans").json()[0]["devices_found"] == 1
        device = client.get("/api/devices").json()[0]
        assert client.get(f"/api/devices/{device['id']}/addresses").json()[0]["ip_address"] == "192.168.5.2"
        assert client.get("/api/devices/999/addresses").status_code == 404


def test_scan_rejects_parallel_discovery_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    assert main_module._scan_lock.acquire(blocking=False)
    try:
        with TestClient(app) as client:
            response = client.post("/api/scan")
    finally:
        main_module._scan_lock.release()
    assert response.status_code == 409
    assert "Ya hay un descubrimiento de red en curso" in response.json()["detail"]


def test_scan_endpoint_uses_discovery_and_records_history(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monkeypatch.setattr(
        "netsentinel.main.discover_local_network",
        lambda: ([Neighbor("192.168.5.3", "00:11:22:33:44:55", "en0", "automatic-local-network")], [], {"networks": [{"network": "192.168.5.0/24", "interface": "en0", "local_address": "192.168.5.20", "range_limited": False}], "addresses_checked": 254, "ping_responses": 1, "scope": "fixture"}),
    )
    with TestClient(app) as client:
        response = client.post("/api/scan")
        assert response.status_code == 200
        assert response.json()["devices_found"] == 1
        assert response.json()["addresses_found"] == 1
        assert response.json()["discovery"]["networks"][0]["network"] == "192.168.5.0/24"
        assert response.json()["discovery"]["addresses_checked"] == 254
        history = client.get("/api/scans").json()[0]
        assert history["source"] == "automatic-local-network"
        assert history["discovery"]["addresses_checked"] == 254
        assert history["discovery"]["ping_responses"] == 1
        assert client.get("/api/health").json()["version"] == __version__


def test_installed_package_version_matches_runtime():
    assert installed_version("netsentinel") == __version__
