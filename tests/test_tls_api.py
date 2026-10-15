import pytest
from pathlib import Path

from fastapi.testclient import TestClient

import netsentinel.api.tools_tls as tools_api
from netsentinel import database
from netsentinel.main import app


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_tls_inspection_api_returns_point_in_time_report(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    expected = {
        "host": "example.com",
        "port": 443,
        "status": "ok",
        "summary": "El certificado fue validado.",
        "certificate": {"days_remaining": 90},
        "tls": {"version": "TLSv1.3"},
        "findings": [],
    }
    calls = []
    monkeypatch.setattr(
        tools_api, "inspect_tls_endpoint",
        lambda host, port: calls.append((host, port)) or expected,
    )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/tools/tls/inspect",
            json={"host": "example.com", "port": 443},
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 200
    assert response.json() == expected
    assert calls == [("example.com", 443)]


def test_tls_inspection_api_rejects_url_instead_of_host(monkeypatch):
    monkeypatch.setattr(
        tools_api, "inspect_tls_endpoint",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Ingresá solo el host o la IP, sin esquema, ruta ni credenciales.")
        ),
    )
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/tools/tls/inspect",
            json={"host": "https://example.com/path", "port": 443},
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 422
    assert "solo el host o la IP" in response.json()["detail"]


def test_tls_inspection_api_rejects_extra_fields():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/tools/tls/inspect",
            json={"host": "example.com", "port": 443, "url": "https://example.com"},
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 422


def test_tls_inspection_api_rejects_cross_site_post():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/tools/tls/inspect",
            json={"host": "example.com", "port": 443},
            headers={"Origin": "http://attacker.example", "Sec-Fetch-Site": "cross-site"},
        )

    assert response.status_code == 403



def test_tools_page_exposes_tls_inspection_with_clear_scope(monkeypatch):
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/tools")
        script = client.get("/static/tools.js")

    assert response.status_code == 200
    assert script.status_code == 200
    assert 'id="tls-form"' in response.text
    assert '"/api/tools/tls/inspect"' in script.text
    scope_source = response.text + script.text
    assert "no solicita páginas" in scope_source
    assert "autorización para evaluar" in scope_source
