from fastapi.testclient import TestClient

import netsentinel.main as main_module
import netsentinel.api.tools as tools_api
from netsentinel.main import app


def test_dns_reverse_api_returns_ptr_result(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        tools_api,
        "cached_reverse_lookup_ip",
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
        tools_api,
        "cached_reverse_lookup_ip",
        lambda _address: (_ for _ in ()).throw(ValueError("Ingresá una dirección IPv4 o IPv6 válida.")),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/reverse", params={"address": "router"})
    assert response.status_code == 422


def test_dns_reverse_api_reports_ptr_failure(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        tools_api,
        "cached_reverse_lookup_ip",
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



def test_dns_reverse_api_returns_not_found_when_ptr_is_absent(monkeypatch):
    from netsentinel.dns_tools import DNSLookupError

    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        tools_api,
        "cached_reverse_lookup_ip",
        lambda _address: (_ for _ in ()).throw(DNSLookupError("No se encontró un registro PTR para esa dirección.", "not_found")),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/tools/dns/reverse", params={"address": "192.0.2.99"})
    assert response.status_code == 404
    assert "PTR" in response.json()["detail"]


def test_device_dns_reverse_uses_latest_observed_address_on_demand(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(
        main_module.database,
        "get_device_addresses",
        lambda device_id: [
            {"ip_address": "192.0.2.10", "last_seen": "2026-10-11T10:00:00Z"},
            {"ip_address": "192.0.2.9", "last_seen": "2026-10-10T10:00:00Z"},
        ] if device_id == 7 else None,
    )
    calls = []
    monkeypatch.setattr(
        main_module,
        "cached_reverse_lookup_ip",
        lambda address: calls.append(address) or {
            "ip": address, "hostname": "router.example.test", "record_type": "PTR",
            "cache_hit": False, "source": "system-resolver",
        },
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/devices/7/dns-reverse")
    assert response.status_code == 200
    assert response.json()["ip"] == "192.0.2.10"
    assert response.json()["device_id"] == 7
    assert calls == ["192.0.2.10"]


def test_device_dns_reverse_returns_404_for_unknown_device(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(main_module.database, "get_device_addresses", lambda _device_id: None)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/devices/9999/dns-reverse")
    assert response.status_code == 404
    assert "dispositivo" in response.json()["detail"].lower()


def test_device_dns_reverse_returns_404_when_device_has_no_addresses(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    monkeypatch.setattr(main_module.database, "get_device_addresses", lambda _device_id: [])
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/devices/7/dns-reverse")
    assert response.status_code == 404
    assert "direcciones" in response.json()["detail"].lower()


def test_inventory_page_exposes_on_demand_ptr_action(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/")
    assert response.status_code == 200
    assert 'data-ptr="${d.id}"' in response.text
    assert "/dns-reverse" in response.text
    assert "nombre DNS no verificado" in response.text
