from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from netsentinel.main import app


ROOT = Path(__file__).resolve().parents[1]
FINDINGS_PAGE = ROOT / "src/netsentinel/static/findings.html"
FINDINGS_SCRIPT = ROOT / "src/netsentinel/static/findings.js"
NAV_PAGES = [
    ROOT / "src/netsentinel/static/index.html",
    ROOT / "src/netsentinel/static/monitors.html",
    ROOT / "src/netsentinel/static/tools.html",
    ROOT / "src/netsentinel/static/activity.html",
    FINDINGS_PAGE,
]


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_findings_page_is_served_without_browser_caching(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/findings")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert '<title>NetSentinel · Hallazgos</title>' in response.text
    assert 'aria-current="page" href="/findings">Hallazgos</a>' in response.text
    assert 'id="stateFilter"' in response.text
    assert 'id="exportLink"' in response.text
    assert 'id="findingsList"' in response.text


def test_all_primary_navigation_pages_link_to_findings():
    for path in NAV_PAGES:
        content = path.read_text(encoding="utf-8")
        assert 'href="/findings">Hallazgos</a>' in content, path.name

    page = FINDINGS_PAGE.read_text(encoding="utf-8")
    assert page.count('aria-current="page"') == 1
    assert 'aria-current="page" href="/findings"' in page


def test_findings_ui_uses_safe_text_rendering_and_no_store_fetches():
    page = FINDINGS_PAGE.read_text(encoding="utf-8")
    script = FINDINGS_SCRIPT.read_text(encoding="utf-8")
    source = page + script
    assert 'cache: "no-store"' in script
    assert "textContent" in script
    assert "innerHTML" not in script
    assert 'method: "PATCH"' in script
    assert 'JSON.stringify({acknowledged:true})' in script
    assert "DNS/TLS" in source
    assert "no demuestra identidad, ataque ni causa raíz" in source
    assert "Conexiones Zeek en contexto temporal" in script
    assert 'link.href = "/activity?"' in script
    assert 'params.toString() + "#eventos"' in script
    assert 'params.set("import_format", "zeek_conn_log")' in script
    assert "related.notice" in script
