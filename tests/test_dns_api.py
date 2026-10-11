import socket

import pytest
from fastapi.testclient import TestClient

import netsentinel.main as main_module
from netsentinel.main import app


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_dns_lookup_api_returns_system_resolver_results(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "lookup_hostname",
        lambda hostname: {
            "hostname": hostname,
            "addresses": [{"ip": "192.0.2.5", "family": "IPv4"}],
            "count": 1,
            "source": "system-resolver",
            "note": "La resolución DNS no verifica la identidad ni la confiabilidad del equipo.",
        },
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/lookup", params={"hostname": "example.com"})
    assert response.status_code == 200
    assert response.json()["addresses"][0]["ip"] == "192.0.2.5"


def test_dns_lookup_api_validates_hostname(monkeypatch):
    def reject(_hostname):
        raise ValueError("Ingresá un nombre de host válido.")
    monkeypatch.setattr(main_module, "lookup_hostname", reject)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/lookup", params={"hostname": "https://example.com"})
    assert response.status_code == 422
    assert "nombre de host" in response.json()["detail"]


def test_dns_lookup_api_reports_resolver_errors(monkeypatch):
    def fail(_hostname):
        raise OSError("resolver error")
    monkeypatch.setattr(main_module, "lookup_hostname", fail)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/lookup", params={"hostname": "missing.example"})
    assert response.status_code == 502
    assert "DNS configurado" in response.json()["detail"]
