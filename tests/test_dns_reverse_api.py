from fastapi.testclient import TestClient

import netsentinel.main as main_module
from netsentinel.main import app


def test_dns_reverse_api_returns_ptr_result(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        main_module,
        "reverse_lookup_ip",
        lambda address: {
            "ip": "192.0.2.1",
            "hostname": "router.example.com",
            "source": "system-resolver",
            "record_type": "PTR",
            "note": "Un registro PTR no verifica la identidad ni la confiabilidad del equipo.",
        },
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/reverse", params={"address": "192.0.2.1"})
    assert response.status_code == 200
    assert response.json()["record_type"] == "PTR"
    assert response.json()["hostname"] == "router.example.com"


def test_dns_reverse_api_rejects_invalid_ip(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        main_module,
        "reverse_lookup_ip",
        lambda _address: (_ for _ in ()).throw(ValueError("Ingresá una dirección IPv4 o IPv6 válida.")),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/reverse", params={"address": "router"})
    assert response.status_code == 422


def test_dns_reverse_api_reports_ptr_failure(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        main_module,
        "reverse_lookup_ip",
        lambda _address: (_ for _ in ()).throw(OSError("no PTR")),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/reverse", params={"address": "192.0.2.9"})
    assert response.status_code == 502


def test_tools_page_exposes_dns_and_ptr_forms(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/tools")
    assert response.status_code == 200
    assert 'id="dns-form"' in response.text
    assert 'id="ptr-form"' in response.text
    assert "/api/tools/dns/reverse" in response.text
