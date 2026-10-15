import re

import pytest
from fastapi.testclient import TestClient

from netsentinel import database
import netsentinel.main as main_module
import netsentinel.api.inventory_assets as inventory_api
import netsentinel.api.tools as tools_api
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
    "closing_tag",
    [
        "</script >",
        "</script\t\n bar>",
    ],
)
def test_inline_script_hashing_handles_unusual_closing_tag_whitespace(closing_tag):
    """CSP debe calcular el hash del bloque que el navegador reconoce como script."""
    import base64
    import hashlib

    from netsentinel.api.security import _inline_script_hashes_in_html

    script = "window.netsentinelReady = true;"
    html = f"<script>{script}{closing_tag}"
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")

    assert _inline_script_hashes_in_html(html) == (f"'sha256-{digest}'",)



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

    monkeypatch.setattr(tools_api, "lookup_hostname", unexpected_call)
    monkeypatch.setattr(tools_api, "cached_reverse_lookup_ip", unexpected_call)
    monkeypatch.setattr(inventory_api, "cached_reverse_lookup_ip", unexpected_call)
    monkeypatch.setattr(main_module.database, "get_device_addresses", unexpected_call)

    response = client.get(path, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Consulta de red iniciada desde otro origen bloqueada."
    assert_defensive_headers(response)


def test_same_origin_dns_request_is_still_allowed(client, monkeypatch):
    monkeypatch.setattr(
        tools_api,
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

@pytest.mark.parametrize(
    ("path", "expected_title", "expected_scripts"),
    [
        ("/", "NetSentinel · Red local", ("/static/theme.js", "/static/index.js")),
        ("/monitors", "NetSentinel · Monitorización", ("/static/theme.js", "/static/section-tabs.js", "/static/monitors.js")),
        ("/activity", "NetSentinel · Actividad y telemetría", ("/static/theme.js", "/static/section-tabs.js", "/static/activity.js")),
        ("/findings", "NetSentinel · Hallazgos", ("/static/theme.js", "/static/findings.js")),
        ("/tools", "Herramientas · NetSentinel", ("/static/theme.js", "/static/tools.js")),
    ],
)
def test_all_local_html_pages_preserve_csp_and_cache_protection(
    client, path, expected_title, expected_scripts
):
    """Pages allow only their expected external scripts under same-origin CSP."""
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert expected_title in response.text
    assert_defensive_headers(response)

    policy = response.headers["content-security-policy"]
    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "'unsafe-inline'" not in policy

    scripts = re.findall(
        r"<script\b([^>]*)>(.*?)</script\b[^>]*>",
        response.text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    observed_scripts = []
    for attributes, inline_body in scripts:
        match = re.fullmatch(r'src="(/static/[^"]+)"( defer)?', attributes.strip())
        assert match, f"{path} contains a script with unexpected attributes: {attributes}"
        source = match.group(1)
        observed_scripts.append(source)
        assert not inline_body.strip(), "Page scripts must stay in separate files."
        if source == "/static/theme.js":
            assert match.group(2) is None, "The shared theme must apply before first paint."
        else:
            assert match.group(2) == " defer", "Page behavior scripts must be deferred."

    assert tuple(observed_scripts) == expected_scripts
    for source in expected_scripts:
        assert client.get(source).status_code == 200, f"Missing frontend asset: {source}"
    assert main_module._inline_script_hashes(path) == ()


@pytest.mark.parametrize(
    "asset",
    [
        "/static/index.js",
        "/static/monitors.js",
        "/static/activity.js",
        "/static/findings.js",
        "/static/tools.js",
        "/static/theme.js",
        "/static/section-tabs.js",
    ],
)
def test_local_page_javascript_is_served_with_defensive_headers(client, asset):
    response = client.get(asset)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(("text/javascript", "application/javascript"))
    assert response.text.strip()
    assert_defensive_headers(response)

    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "'unsafe-inline'" not in policy
    assert "sha256-" not in policy
