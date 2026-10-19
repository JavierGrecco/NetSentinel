import pytest
from fastapi.testclient import TestClient

import netsentinel.main as main_module
import netsentinel.api.inventory_discovery as inventory_discovery_module

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
    with TestClient(app, base_url='http://127.0.0.1') as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert len(health.headers["x-request-id"]) == 12
        page = client.get("/")
        assert page.status_code == 200
        assert "NetSentinel" in page.text
        from pathlib import Path
        ui_source = page.text + Path("src/netsentinel/static/index.js").read_text(encoding="utf-8")
        assert "IP local de esta computadora según la última lectura" in ui_source
        assert "Equipo local identificado" in ui_source
        assert "La observación proviene de una interfaz Apple de enlace local" in ui_source
        assert client.get("/api/devices").json() == []
        assert client.get("/api/scans").json() == []
        assert client.get("/api/export/data.json").json()["format"] == "netsentinel-data-export-v4"


def test_request_validation_errors_do_not_echo_collector_token(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    secret = "TOKEN_LEAK"
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/activity/ingest",
            json={
                "session_id": 1,
                "collector_token": secret,
                "device_id": 1,
                "event_type": "dns_query",
                "source": "router_dns",
                "domain": "example.com",
            },
        )

    assert response.status_code == 422
    assert secret not in response.text
    errors = response.json()["detail"]
    assert errors[0]["loc"] == ["body", "collector_token"]
    assert "msg" in errors[0]
    assert "type" in errors[0]
    assert "input" not in errors[0]
    assert "ctx" not in errors[0]
    assert "TOKEN_LEAK" not in errors[0]["msg"]
    assert "TOKEN_LEAK" not in caplog.text
    assert not (tmp_path / "netsentinel-errors.jsonl").exists()
    assert response.json()["error_code"] == "NS-REQ-422"
    assert response.json()["request_id"] == response.headers["x-request-id"]
    assert response.json()["next_action"]
    assert response.json()["registered_in_log"] is False
    assert response.json()["should_log"] is False
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_api_device_trust_and_acknowledgement(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "AA:BB:CC:DD:EE:FF", "en0")])
    with TestClient(app, base_url='http://127.0.0.1') as client:
        device = client.get("/api/devices").json()[0]
        response = client.patch(f"/api/devices/{device['id']}", json={"trusted": True, "display_name": "Router de prueba"}, headers={"Origin": "http://127.0.0.1"})
        assert response.status_code == 200
        assert response.json()["trusted"] is True
        event = client.get("/api/events").json()[0]
        response = client.patch(f"/api/events/{event['id']}", json={"acknowledged": True}, headers={"Origin": "http://127.0.0.1"})
        assert response.status_code == 200


def test_api_scan_history_and_device_addresses(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "00:11:22:33:44:55", "en0")])
    with TestClient(app, base_url='http://127.0.0.1') as client:
        assert client.get("/api/scans").json()[0]["devices_found"] == 1
        device = client.get("/api/devices").json()[0]
        assert client.get(f"/api/devices/{device['id']}/addresses").json()[0]["ip_address"] == "192.168.5.2"
        missing = client.get("/api/devices/999/addresses")
        assert missing.status_code == 404
        assert missing.json()["error_code"] == "NS-HTTP-404"
        assert missing.json()["request_id"] == missing.headers["x-request-id"]
        assert missing.json()["registered_in_log"] is False
        assert missing.json()["should_log"] is False
        assert not (tmp_path / "netsentinel-errors.jsonl").exists()


def test_scan_rejects_parallel_discovery_requests(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    assert inventory_discovery_module._scan_lock.acquire(blocking=False)
    try:
        with TestClient(app, base_url='http://127.0.0.1') as client:
            response = client.post("/api/scan")
    finally:
        inventory_discovery_module._scan_lock.release()
    assert response.status_code == 409
    assert "Ya hay un descubrimiento de red en curso" in response.json()["detail"]


def test_scan_endpoint_uses_discovery_and_records_history(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monkeypatch.setattr(
        "netsentinel.api.inventory_discovery.discover_local_network",
        lambda: ([Neighbor("192.168.5.3", "00:11:22:33:44:55", "en0", "automatic-local-network")], [], {"networks": [{"network": "192.168.5.0/24", "interface": "en0", "local_address": "192.168.5.20", "range_limited": False}], "addresses_checked": 254, "ping_responses": 1, "scope": "fixture"}),
    )
    with TestClient(app, base_url='http://127.0.0.1') as client:
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


def test_sqlite_backup_download_is_openable(monkeypatch, tmp_path):
    import sqlite3

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.7.5", "AA:BB:CC:DD:EE:77", "en0")])
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/export/backup.sqlite3")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.sqlite3")
    assert response.headers["cache-control"] == "no-store"
    assert "netsentinel-backup.sqlite3" in response.headers["content-disposition"]
    backup_path = tmp_path / "downloaded.sqlite3"
    backup_path.write_bytes(response.content)
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("SELECT mac_address FROM devices").fetchone()[0] == "AA:BB:CC:DD:EE:77"
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_unhandled_error_is_sanitized_and_keeps_security_headers(monkeypatch, tmp_path, caplog):
    import logging

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    secret = "PRIVATE_TOKEN=must-not-be-logged"

    def fail_summary():
        raise RuntimeError(secret)

    monkeypatch.setattr(main_module.database, "get_summary", fail_summary)
    with TestClient(
        app,
        base_url="http://127.0.0.1",
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/api/summary")

    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "NS-500-001"
    assert body["request_id"] == response.headers["x-request-id"]
    assert body["next_action"]
    assert body["registered_in_log"] is True
    assert body["should_log"] is True
    assert (tmp_path / "netsentinel-errors.jsonl").exists()
    assert "PRIVATE_TOKEN" not in response.text
    assert "PRIVATE_TOKEN" not in caplog.text
    assert body["detail"] == "NetSentinel no pudo completar la operación por un error interno."
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"


def test_host_guard_rejects_unknown_hostname(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://untrusted.example") as client:
        response = client.get("/api/health")
    assert response.status_code == 400
    assert response.json()["detail"] == "Host no permitido para NetSentinel."


def test_csrf_guard_rejects_cross_origin_mutations(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        origin_response = client.post("/api/scan", headers={"Origin": "http://attacker.example"})
        fetch_response = client.post("/api/scan", headers={"Sec-Fetch-Site": "cross-site"})
        same_site_response = client.patch("/api/devices/999", json={"trusted": True}, headers={"Sec-Fetch-Site": "same-site"})
        malformed_response = client.post("/api/scan", headers={"Origin": "http://["})
        same_origin_response = client.patch(
            "/api/devices/999",
            json={"trusted": True},
            headers={"Sec-Fetch-Site": "same-origin", "Origin": "http://127.0.0.1"},
        )
    assert origin_response.status_code == 403
    assert fetch_response.status_code == 403
    assert same_site_response.status_code == 403
    assert malformed_response.status_code == 403
    # A legitimate same-origin browser request is not rejected by Fetch Metadata.
    assert same_origin_response.status_code == 404
    assert origin_response.json()["detail"] == "Origen no permitido para esta operación."
    assert fetch_response.json()["detail"] == "Solicitud desde otro origen bloqueada."
    assert same_site_response.json()["detail"] == "Solicitud desde otro origen bloqueada."
    assert malformed_response.json()["detail"] == "Origen no permitido para esta operación."


def test_extra_hostname_must_be_explicitly_allowed(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_ALLOWED_HOSTS", "netsentinel.home, dashboard.lan")
    with TestClient(app, base_url="http://netsentinel.home") as client:
        response = client.get("/api/health")
    assert response.status_code == 200


def test_security_headers_are_set(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    policy = response.headers["content-security-policy"]
    for directive in (
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'none'",
        "frame-src 'none'",
        "form-action 'self'",
        "connect-src 'self'",
    ):
        assert directive in policy
    script_policy = next(item for item in policy.split("; ") if item.startswith("script-src "))
    assert "'unsafe-inline'" not in script_policy
    assert "https://cdn.jsdelivr.net" not in policy
    style_policy = next(item for item in policy.split("; ") if item.startswith("style-src "))
    assert "'unsafe-inline'" not in style_policy


@pytest.mark.parametrize(
    ("route", "html_asset", "script_asset"),
    [
        ("/", "index.html", "index.js"),
        ("/network", "network.html", "network.js"),
        ("/monitors", "monitors.html", "monitors.js"),
        ("/activity", "activity.html", "activity.js"),
        ("/tools", "tools.html", "tools.js"),
        ("/findings", "findings.html", "findings.js"),
    ],
)
def test_page_javascript_is_external_and_allowed_by_same_origin_csp(
    monkeypatch, tmp_path, route, html_asset, script_asset
):
    import re
    from pathlib import Path

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    expected_scripts = {f"/static/{script_asset}", "/static/theme.js"}
    if route == "/":
        expected_scripts.add("/static/scan-comparison.js")
    if route == "/network":
        expected_scripts.add("/static/cytoscape.min.js")
        expected_scripts.add("/static/topology.js")
        expected_scripts.add("/static/scan-comparison.js")
    if route in {"/monitors", "/activity"}:
        expected_scripts.add("/static/section-tabs.js")

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(route)
        script_responses = {source: client.get(source) for source in expected_scripts}

    assert response.status_code == 200
    html = response.text.replace("\r\n", "\n").replace("\r", "\n")
    assert html == Path("src/netsentinel/static", html_asset).read_text(encoding="utf-8")
    scripts = list(re.finditer(
        r"<script\b([^>]*)>(.*?)</script\b[^>]*>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ))
    observed_scripts = set()
    for script in scripts:
        attributes = script.group(1).strip()
        match = re.fullmatch(r'src="(/static/[^"]+)"( defer)?', attributes)
        assert match, f"{route} contains a script with unexpected attributes: {attributes}"
        source = match.group(1)
        assert source not in observed_scripts, f"{route} loads {source} more than once"
        observed_scripts.add(source)
        assert not script.group(2).strip(), "Inline JavaScript must not be reintroduced."
        if source.endswith("/theme.js"):
            assert match.group(2) is None, "The shared theme must apply before first paint."
        else:
            assert match.group(2) == " defer", "Application behavior scripts must be deferred."

    assert observed_scripts == expected_scripts, f"{route} has an unexpected script set."
    for source, script_response in script_responses.items():
        script_asset_path = source.removeprefix("/static/")
        script_source = Path("src/netsentinel/static", script_asset_path).read_text(encoding="utf-8")
        assert script_response.status_code == 200
        assert script_response.text.replace("\r\n", "\n").replace("\r", "\n") == script_source
        assert script_response.text.strip()

    policy = response.headers["content-security-policy"]
    script_policy = next(item for item in policy.split("; ") if item.startswith("script-src "))
    assert "'self'" in script_policy
    assert "'unsafe-inline'" not in script_policy
    assert "'sha256-" not in script_policy
    assert "https://cdn.jsdelivr.net" not in script_policy



def test_shared_theme_and_task_focused_sections_are_present():
    from pathlib import Path

    static = Path("src/netsentinel/static")
    page_names = ("index.html", "findings.html", "monitors.html", "tools.html", "activity.html")
    for page_name in page_names:
        html = (static / page_name).read_text(encoding="utf-8")
        assert 'id="themeSelect"' in html, f"{page_name} must expose the shared theme selector"
        assert 'href="/static/theme.css"' in html, f"{page_name} must load the shared theme"
        assert 'src="/static/theme.js"' in html, f"{page_name} must persist the theme selection"
        assert 'value="dark"' in html and 'value="medium"' in html and 'value="light"' in html
        assert 'role="radiogroup" aria-label="Tema visual"' in html
        assert 'class="app-brand-name">NetSentinel</div>' in html
        assert 'class="app-section-title"' in html
        assert 'class="app-section-description"' in html
        assert 'class="theme-option-card"' in html
        assert 'name="themeSelect" type="radio"' in html
        assert '<select id="themeSelect"' not in html

    theme_js = (static / "theme.js").read_text(encoding="utf-8")
    assert 'const STORAGE_KEY = "netsentinel-theme"' in theme_js
    assert "localStorage.getItem(STORAGE_KEY)" in theme_js
    assert "localStorage.setItem(STORAGE_KEY, selected)" in theme_js

    for page_name, expected_panels in (
        ("monitors.html", ("monitor-overview", "monitor-config", "monitor-incidents", "monitor-notifications")),
        ("activity.html", ("activity-overview", "activity-tracking", "activity-import", "activity-events", "activity-privacy")),
    ):
        html = (static / page_name).read_text(encoding="utf-8")
        assert 'src="/static/section-tabs.js" defer' in html
        for panel_id in expected_panels:
            assert f'id="{panel_id}"' in html
            assert f'data-tab-target="{panel_id}"' in html

    activity_html = (static / "activity.html").read_text(encoding="utf-8")
    activity_js = (static / "activity.js").read_text(encoding="utf-8")
    assert 'id="sourceHelp"' in activity_html
    assert "adaptadores de router no vienen integrados" in activity_html
    assert "Qué necesitás:" in activity_js
    assert "router_dns:" in activity_js and "router_flow:" in activity_js and "device_agent:" in activity_js
    assert "todavía no viene integrado" in activity_js

    findings_js = (static / "findings.js").read_text(encoding="utf-8")
    assert "Marcar dispositivo como conocido" in findings_js
    assert "Solo marcar como revisado" in findings_js
    assert "PATCH" in findings_js and "/api/devices/" in findings_js
    assert "Esto no equivale a una certificación de seguridad" in findings_js


def test_inline_event_handlers_are_not_reintroduced_in_application_pages():
    import re
    from pathlib import Path

    for asset in ("index.html", "monitors.html", "activity.html", "tools.html", "findings.html"):
        content = Path("src/netsentinel/static", asset).read_text(encoding="utf-8")
        assert not re.search(r"\son[a-z]+\s*=", content, re.IGNORECASE), (
            f"{asset} contains an inline event handler incompatible with the local CSP policy"
        )


@pytest.mark.parametrize(
    ("route", "asset"),
    [
        ("/", "index.html"),
        ("/monitors", "monitors.html"),
        ("/activity", "activity.html"),
        ("/tools", "tools.html"),
        ("/findings", "findings.html"),
    ],
)
def test_application_pages_use_external_styles_without_inline_style(monkeypatch, tmp_path, route, asset):
    import re
    from pathlib import Path

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(route)

        assert response.status_code == 200
        html = response.text.replace("\r\n", "\n").replace("\r", "\n")
        assert html == Path("src/netsentinel/static", asset).read_text(encoding="utf-8")
        assert not re.search(r"<style(?:\s[^>]*)?>", html, re.IGNORECASE), (
            f"{asset} must not contain a style element"
        )
        assert not re.search(r"\sstyle\s*=", html, re.IGNORECASE), (
            f"{asset} must not contain style attributes, including generated templates"
        )

        policy = response.headers["content-security-policy"]
        style_policy = next(item for item in policy.split("; ") if item.startswith("style-src "))
        assert "'unsafe-inline'" not in style_policy

        stylesheets = set(re.findall(r'href="(/static/[^"]+\.css)"', html, re.IGNORECASE))
        assert stylesheets, f"{asset} must load at least one local stylesheet"
        for stylesheet in stylesheets:
            css_response = client.get(stylesheet)
            assert css_response.status_code == 200, f"Missing stylesheet: {stylesheet}"
            assert "text/css" in css_response.headers["content-type"]


def test_api_docs_style_policy_does_not_allow_inline_styles(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/docs")
    assert response.status_code == 200
    style_policy = next(
        item for item in response.headers["content-security-policy"].split("; ")
        if item.startswith("style-src ")
    )
    assert "'unsafe-inline'" not in style_policy
    assert "https://cdn.jsdelivr.net" in style_policy


def test_api_docs_content_security_policy_hashes_initializer_and_scopes_cdn(monkeypatch, tmp_path):
    import base64
    import hashlib
    import re

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/docs")
    assert response.status_code == 200
    html = response.text.replace("\r\n", "\n").replace("\r", "\n")
    policy = response.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in policy
    assert "https://fastapi.tiangolo.com" in policy
    assert "frame-ancestors 'none'" in policy
    assert "connect-src 'self'" in policy

    scripts = [
        match.group(1).replace("\r\n", "\n").replace("\r", "\n")
        for match in re.finditer(r"<script(?:\s[^>]*)?>(.*?)</script\b[^>]*>", html, re.IGNORECASE | re.DOTALL)
        if match.group(1).strip()
    ]
    assert scripts, "Swagger UI must include an inline initializer that is authorized by hash"
    expected = {
        "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
        for script in scripts
    }
    script_policy = next(item for item in policy.split("; ") if item.startswith("script-src "))
    observed = {token for token in script_policy.split()[1:] if token.startswith("'sha256-")}

    assert expected == observed
    assert "'unsafe-inline'" not in script_policy
    assert "https://cdn.jsdelivr.net" not in policy.split("script-src ", 1)[0]


def test_security_headers_are_present_on_host_rejections(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://untrusted.example") as client:
        response = client.get("/api/health")
    assert response.status_code == 400
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    assert response.headers["cache-control"] == "no-store"
    script_policy = next(
        item for item in response.headers["content-security-policy"].split("; ")
        if item.startswith("script-src ")
    )
    assert not any(token.startswith("'sha256-") for token in script_policy.split())


def test_device_history_returns_observations_for_selected_device(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.2", "AA:BB:CC:DD:EE:01", "en0")])
    database.record_scan([Neighbor("192.168.5.3", "AA:BB:CC:DD:EE:01", "en0")])
    with TestClient(app, base_url="http://127.0.0.1") as client:
        device = client.get("/api/devices").json()[0]
        response = client.get(f"/api/devices/{device['id']}/history")
    assert response.status_code == 200
    payload = response.json()
    assert payload["device"]["id"] == device["id"]
    assert payload["count"] == 2
    assert {item["ip_address"] for item in payload["observations"]} == {"192.168.5.2", "192.168.5.3"}
    assert "no registra páginas web" in payload["note"]


def test_device_history_returns_404_for_unknown_device(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/devices/9999/history")
    assert response.status_code == 404


def test_device_history_limits_observation_count(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/devices/9999/history?limit=10000")
    assert response.status_code == 422

@pytest.mark.parametrize(
    ("status_code", "expected_detail"),
    [
        (500, "NetSentinel no pudo completar la operación por un error interno."),
        (502, "La comprobación externa no pudo completarse."),
        (503, "El servicio todavía no está disponible temporalmente."),
    ],
)
def test_http_5xx_details_are_sanitized(monkeypatch, tmp_path, status_code, expected_detail):
    import asyncio
    import json

    from fastapi import HTTPException
    from starlette.requests import Request

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    secret = "PRIVATE_HTTP_DETAIL=must-not-be-returned"
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/test",
        "raw_path": b"/api/test",
        "query_string": b"",
        "headers": [(b"host", b"127.0.0.1")],
        "client": ("testclient", 12345),
        "server": ("testserver", 80),
    }
    request = Request(scope)

    response = asyncio.run(
        main_module.handle_http_exception(
            request,
            HTTPException(status_code=status_code, detail=secret),
        )
    )
    body = json.loads(response.body)

    assert response.status_code == status_code
    assert body["detail"] == expected_detail
    assert secret not in response.body.decode("utf-8")
    assert body["should_log"] is True
    assert body["registered_in_log"] is True
    journal = (tmp_path / "netsentinel-errors.jsonl").read_text(encoding="utf-8")
    assert secret not in journal

def test_scan_observations_endpoint_returns_exact_evidence_and_safe_not_found(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    mac = "AA:BB:CC:DD:EE:92"
    first = database.record_scan(
        [Neighbor("192.168.8.12", mac, "en0", "automatic-local-network")],
        discovery={
            "networks": [{
                "network": "192.168.8.0/24",
                "interface": "en0",
                "local_address": "192.168.8.6",
                "range_limited": False,
            }]
        },
    )
    database.record_scan(
        [Neighbor("192.168.8.12", mac, "en0", "system-neighbor-table")],
        discovery={
            "networks": [{
                "network": "192.168.8.0/24",
                "interface": "en0",
                "local_address": "192.168.8.6",
                "range_limited": False,
            }]
        },
    )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(f"/api/scans/{first['scan_id']}/observations")
        missing = client.get("/api/scans/99999/observations")

    assert response.status_code == 200
    observations = response.json()
    assert len(observations) == 1
    assert observations[0]["scan_id"] == first["scan_id"]
    assert observations[0]["ip_address"] == "192.168.8.12"
    assert observations[0]["source"] == "automatic-local-network"
    assert observations[0]["trusted"] is False
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "NS-HTTP-404"
    assert missing.json()["registered_in_log"] is False
    assert missing.json()["should_log"] is False



def test_scan_comparison_endpoint_is_read_only_and_handles_invalid_pairs(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    scope = {"networks": [{"network": "192.168.5.0/24", "interface": "en0"}]}
    first = database.record_scan(
        [Neighbor("192.168.5.4", "AA:BB:CC:DD:EE:41", "en0", "automatic-local-network")],
        discovery=scope,
    )
    second = database.record_scan(
        [Neighbor("192.168.5.5", "AA:BB:CC:DD:EE:41", "en0", "automatic-local-network")],
        discovery=scope,
    )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(
            "/api/scans/compare",
            params={"first_scan_id": second["scan_id"], "second_scan_id": first["scan_id"]},
        )
        same = client.get(
            "/api/scans/compare",
            params={"first_scan_id": first["scan_id"], "second_scan_id": first["scan_id"]},
        )
        missing = client.get(
            "/api/scans/compare",
            params={"first_scan_id": first["scan_id"], "second_scan_id": 9999},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["comparable"] is True
    assert body["baseline_scan"]["id"] == first["scan_id"]
    assert body["comparison_scan"]["id"] == second["scan_id"]
    assert body["summary"]["address_changed"] == 1
    assert body["changes"][0]["baseline_addresses"] == ["192.168.5.4"]
    assert body["changes"][0]["comparison_addresses"] == ["192.168.5.5"]
    assert body["absence_note"]
    assert response.headers["cache-control"] == "no-store"
    assert same.status_code == 422
    assert missing.status_code == 404


def test_events_api_can_filter_history_to_one_device(monkeypatch, tmp_path):
    """Los eventos de un dispositivo no se mezclan con los de otro equipo."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([
        Neighbor("192.168.50.10", "02:00:00:00:50:10", "fixture0", "fixture-events"),
        Neighbor("192.168.50.20", "02:00:00:00:50:20", "fixture0", "fixture-events"),
    ])

    with TestClient(app, base_url="http://127.0.0.1") as client:
        devices = {
            item["ip_address"]: item
            for item in client.get("/api/devices").json()
        }
        first_id = devices["192.168.50.10"]["id"]
        second_id = devices["192.168.50.20"]["id"]

        all_events = client.get("/api/events?limit=50").json()
        first_events = client.get(
            "/api/events",
            params={"device_id": first_id, "limit": 8},
        )
        second_events = client.get(
            "/api/events",
            params={"device_id": second_id, "limit": 8},
        )

    assert first_events.status_code == 200
    assert second_events.status_code == 200
    assert first_events.json()
    assert second_events.json()
    assert all(item["device_id"] == first_id for item in first_events.json())
    assert all(item["device_id"] == second_id for item in second_events.json())
    assert {item["device_id"] for item in all_events} == {first_id, second_id}


def test_topology_api_returns_evidence_and_preserves_missing_scan_errors(monkeypatch, tmp_path):
    """La API entrega un grafo documentado y distingue una lectura inexistente."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    scan = database.record_scan(
        [Neighbor("192.168.56.20", "02:00:00:00:00:20", "en0", "fixture-topology")],
        discovery={
            "networks": [
                {
                    "network": "192.168.56.0/24",
                    "interface": "en0",
                    "local_address": "192.168.56.10",
                    "range_limited": False,
                }
            ],
            "scope": "Fixture sintética de prueba.",
        },
    )
    scan_id = int(scan["scan_id"])

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get(f"/api/scans/{scan_id}/topology")
        missing = client.get("/api/scans/999999/topology")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    graph = response.json()
    assert graph["scan_id"] == str(scan_id)
    assert graph["evidence_available"] is True
    assert graph["network_scope_available"] is True
    assert graph["stats"] == {
        "observed_devices": 1,
        "known_subnets": 1,
        "observed_memberships": 1,
        "unlinked_devices": 0,
    }
    subnet_node = next(node for node in graph["nodes"] if node["kind"] == "subnet")
    assert subnet_node["local_address"] == "192.168.56.10"
    assert subnet_node["range_limited"] is False
    device_node = next(node for node in graph["nodes"] if node["kind"] == "device")
    assert device_node["observations"] == [{
        "ip_address": "192.168.56.20",
        "sources": ["fixture-topology"],
        "observed_at": [device_node["observations"][0]["observed_at"][0]],
    }]
    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert edge["kind"] == "observed-subnet-membership"
    assert edge["ip_address"] == "192.168.56.20"
    assert edge["label"] == "192.168.56.20"
    assert edge["sources"] == ["fixture-topology"]
    assert missing.status_code == 404
    assert missing.json()["detail"] == "No se encontró la lectura solicitada."
