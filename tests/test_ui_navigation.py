from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "/": ("src/netsentinel/static/index.html", "/"),
    "/network": ("src/netsentinel/static/network.html", "/network"),
    "/findings": ("src/netsentinel/static/findings.html", "/findings"),
    "/monitors": ("src/netsentinel/static/monitors.html", "/monitors"),
    "/tools": ("src/netsentinel/static/tools.html", "/tools"),
    "/activity": ("src/netsentinel/static/activity.html", "/activity"),
}
NAV_RE = re.compile(
    r'<nav class="primary-nav" aria-label="Navegación principal">(.*?)</nav>',
    flags=re.DOTALL,
)
LINK_RE = re.compile(
    r'<a class="nav-link"(?P<current> aria-current="page")? '
    r'href="(?P<href>[^"]+)">(?P<label>[^<]+)</a>'
)
EXPECTED_HREFS = ["/", "/network", "/findings", "/monitors", "/tools", "/activity"]


def test_every_module_has_consistent_primary_navigation():
    for route, (relative_path, current_route) in PAGES.items():
        html = (ROOT / relative_path).read_text(encoding="utf-8")
        match = NAV_RE.search(html)
        assert match, f"{relative_path} is missing accessible primary navigation"

        links = list(LINK_RE.finditer(match.group(1)))
        hrefs = [link.group("href") for link in links]
        active = [link.group("href") for link in links if link.group("current")]

        assert hrefs == EXPECTED_HREFS, f"{relative_path} has inconsistent module links"
        assert active == [current_route], (
            f"{relative_path} must mark only {current_route!r} as the current page"
        )
        assert all(link.group("label").strip() for link in links)


def test_historical_selectors_offer_more_readings_without_expanding_recent_activity():
    """Los selectores consultan más historial y la lista principal sigue acotada."""
    dashboard_js = (ROOT / "src/netsentinel/static/index.js").read_text(encoding="utf-8")
    network_js = (ROOT / "src/netsentinel/static/network.js").read_text(encoding="utf-8")
    inventory_html = (ROOT / "src/netsentinel/static/index.html").read_text(encoding="utf-8")
    network_html = (ROOT / "src/netsentinel/static/network.html").read_text(encoding="utf-8")

    assert "api('/api/scans?limit=100')" in dashboard_js
    assert "const recentScans = state.scans.slice(0, 12);" in dashboard_js
    assert "recentScans.map(scan=>" in dashboard_js
    assert 'api("/api/scans?limit=100")' in network_js
    assert "hasta las 100 lecturas más recientes" not in inventory_html
    assert "hasta las 100 lecturas más recientes" not in network_html
    assert "id=\"loadMoreScansButton\"" in inventory_html
    assert "id=\"loadMoreScansButton\"" in network_html
    assert "id=\"scanHistoryLoadStatus\"" in inventory_html
    assert "id=\"scanHistoryLoadStatus\"" in network_html
    assert "before_started_at: cursor.started_at" in dashboard_js
    assert "before_started_at: cursor.started_at" in network_js
    assert "state.scansCursor = scans.length ? scans[scans.length - 1] : null;" in dashboard_js
    assert "state.scansCursor = scans.length ? scans[scans.length - 1] : null;" in network_js
    assert "if (page.length) state.scansCursor = page[page.length - 1];" in dashboard_js
    assert "if (page.length) state.scansCursor = page[page.length - 1];" in network_js
