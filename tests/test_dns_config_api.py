import pytest
from fastapi.testclient import TestClient

import netsentinel.main as main_module
from netsentinel.main import app


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_dns_configuration_api_returns_local_read_only_data(monkeypatch):
    monkeypatch.setattr(main_module, "get_dns_configuration", lambda: {
        "platform": "linux",
        "servers": ["192.168.1.1"],
        "count": 1,
        "source": "resolv.conf",
        "detected": True,
        "note": "Vista parcial.",
    })
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/configuration")
    assert response.status_code == 200
    assert response.json()["servers"] == ["192.168.1.1"]
    assert response.json()["detected"] is True
