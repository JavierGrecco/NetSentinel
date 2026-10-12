import pytest
from fastapi.testclient import TestClient

from netsentinel import database
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
