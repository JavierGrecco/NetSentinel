from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "/": ("src/netsentinel/static/index.html", "/"),
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
EXPECTED_HREFS = ["/", "/findings", "/monitors", "/tools", "/activity"]


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



MODULE_PAGES = {
    "/": "src/netsentinel/static/index.html",
    "/findings": "src/netsentinel/static/findings.html",
    "/monitors": "src/netsentinel/static/monitors.html",
    "/tools": "src/netsentinel/static/tools.html",
    "/activity": "src/netsentinel/static/activity.html",
    "/forensics": "src/netsentinel/static/forensics.html",
}
MODULE_SWITCHER_RE = re.compile(
    r'<nav class="product-switcher" aria-label="Cambiar entre módulos NetSentinel">(.*?)</nav>',
    flags=re.DOTALL,
)
PRODUCT_LINK_RE = re.compile(
    r'<a class="product-link(?P<classes>[^"]*)" href="(?P<href>[^"]+)"'
    r'(?P<current> aria-current="true")?>(?P<label>.*?)</a>',
    flags=re.DOTALL,
)


def test_every_page_can_switch_between_red_and_forensics():
    """El acceso a ambos productos debe estar disponible en todas las vistas."""
    for current_route, relative_path in MODULE_PAGES.items():
        html = (ROOT / relative_path).read_text(encoding="utf-8")
        match = MODULE_SWITCHER_RE.search(html)
        assert match, f"{relative_path} is missing the product switcher"

        links = list(PRODUCT_LINK_RE.finditer(match.group(1)))
        assert [link.group("href") for link in links] == ["/", "/forensics"]

        active = [link.group("href") for link in links if link.group("current")]
        expected = ["/forensics"] if current_route == "/forensics" else ["/"]
        assert active == expected, f"{relative_path} has the wrong active product"

        labels = [
            re.sub(r"<[^>]+>", "", link.group("label")).strip()
            for link in links
        ]
        assert labels == ["NetSentinel Red", "NetSentinel Forense"]
