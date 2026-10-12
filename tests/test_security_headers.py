import pytest
from fastapi.testclient import TestClient

from netsentinel import database
import netsentinel.main as main_module
from netsentinel.main import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def assert_defensive_headers(response):
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/api/health",
        "/api/summary",
        "/api/devices",
        "/api/events",
        "/api/scans",
        "/api/findings",
        "/api/export/findings.json",
        "/api/export/data.json",
        "/api/export/backup.sqlite3",
    ],
)
def test_local_pages_inventory_and_exports_are_never_cached(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert_defensive_headers(response)


def test_host_rejection_also_receives_defensive_headers(client):
    response = client.get("/api/health", headers={"Host": "untrusted.example"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Host no permitido para NetSentinel."
    assert_defensive_headers(response)


def test_cross_origin_rejection_also_receives_defensive_headers(client):
    response = client.post(
        "/api/scan",
        headers={"Origin": "http://attacker.example"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Origen no permitido para esta operación."
    assert_defensive_headers(response)



@pytest.mark.parametrize(
    "path",
    [
        "/api/tools/dns/lookup?hostname=probe.attacker.example",
        "/api/tools/dns/reverse?address=192.0.2.42",
        "/api/devices/7/dns-reverse",
    ],
)
@pytest.mark.parametrize(
    "headers",
    [
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Origin": "http://attacker.example"},
    ],
)
def test_cross_site_dns_requests_are_blocked_before_resolver(client, monkeypatch, path, headers):
    def unexpected_call(*_args, **_kwargs):
        pytest.fail("A cross-origin request must not trigger DNS traffic.")

    monkeypatch.setattr(main_module, "lookup_hostname", unexpected_call)
    monkeypatch.setattr(main_module, "cached_reverse_lookup_ip", unexpected_call)
    monkeypatch.setattr(main_module.database, "get_device_addresses", unexpected_call)

    response = client.get(path, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Consulta de red iniciada desde otro origen bloqueada."
    assert_defensive_headers(response)


def test_same_origin_dns_request_is_still_allowed(client, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "lookup_hostname",
        lambda hostname: {"hostname": hostname, "addresses": [], "count": 0, "source": "test"},
    )

    response = client.get(
        "/api/tools/dns/lookup",
        params={"hostname": "example.test"},
        headers={"Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1"},
    )

    assert response.status_code == 200
    assert response.json()["hostname"] == "example.test"
