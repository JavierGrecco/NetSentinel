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
    "/world-map": ("src/netsentinel/static/geolocation.html", "/world-map"),
    "/guided-test": ("src/netsentinel/static/guided-test.html", "/guided-test"),
}
NAV_RE = re.compile(
    r'<nav class="primary-nav" aria-label="Navegación principal">(.*?)</nav>',
    flags=re.DOTALL,
)
LINK_RE = re.compile(
    r'<a class="nav-link"(?P<current> aria-current="page")? '
    r'href="(?P<href>[^"]+)">(?P<label>[^<]+)</a>'
)
EXPECTED_HREFS = ["/", "/network", "/findings", "/monitors", "/tools", "/activity", "/world-map", "/guided-test"]


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
    shared_css = (ROOT / "src/netsentinel/static/styles.css").read_text(encoding="utf-8")
    assert ".scan-history-pagination{display:flex" in shared_css
    assert "@media(max-width:560px){.scan-history-pagination" in shared_css
    assert "before_started_at: cursor.started_at" in dashboard_js
    assert "before_started_at: cursor.started_at" in network_js
    assert "state.scansCursor = scans.length ? scans[scans.length - 1] : null;" in dashboard_js
    assert "state.scansCursor = scans.length ? scans[scans.length - 1] : null;" in network_js
    assert "if (page.length) state.scansCursor = page[page.length - 1];" in dashboard_js
    assert "if (page.length) state.scansCursor = page[page.length - 1];" in network_js



MODULE_PAGES = {
    "/": "src/netsentinel/static/index.html",
    "/network": "src/netsentinel/static/network.html",
    "/findings": "src/netsentinel/static/findings.html",
    "/monitors": "src/netsentinel/static/monitors.html",
    "/tools": "src/netsentinel/static/tools.html",
    "/activity": "src/netsentinel/static/activity.html",
    "/world-map": "src/netsentinel/static/geolocation.html",
    "/guided-test": "src/netsentinel/static/guided-test.html",
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


def test_forensics_manifest_exports_are_connected_to_the_screen():
    """Los dos manifiestos deben estar disponibles desde el caso seleccionado."""
    html = (ROOT / "src/netsentinel/static/forensics.html").read_text(encoding="utf-8")
    script = (ROOT / "src/netsentinel/static/forensics.js").read_text(encoding="utf-8")

    assert 'id="exportForensicAuditManifest"' in html
    assert 'id="exportForensicCaseManifest"' in html
    assert "function installManifestExport(buttonId, endpointSuffix, filename" in script
    assert '"exportForensicAuditManifest"' in script
    assert '"exportForensicCaseManifest"' in script
    assert '"/audit/manifest"' in script
    assert '"/manifest"' in script
    assert '"netsentinel-forensic-audit-manifest.json"' in script
    assert '"netsentinel-forensic-case-manifest.json"' in script
    assert "digest no es una firma digital" in script

    # El callback debe capturar la URL antes de limpiar la variable local.
    # Si usa objectUrl después de asignarle None, la descarga no libera su URL.
    assert "const downloadUrl = objectUrl;" in script
    assert "window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);" in script
    assert "window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);" not in script


def test_forensics_workspace_does_not_link_to_world_map() -> None:
    """El mapa de IP pertenece a Red y no debe aparecer como atajo de Forense."""
    html = (ROOT / "src/netsentinel/static/forensics.html").read_text(encoding="utf-8")
    assert 'href="/world-map"' not in html
    assert 'href="/"' in html

    assert 'id="forensicReceivedFrom"' in html
    assert 'id="forensicReceivedBy"' in html
    script = (ROOT / "src/netsentinel/static/forensics.js").read_text(encoding="utf-8")
    assert 'received_by: values.received_by' in script


def test_forensic_report_workspace_exposes_versioning_and_safe_exports() -> None:
    """La interfaz permite crear informes, enmendarlos y descargar formatos no firmados."""
    html = (ROOT / "src/netsentinel/static/forensics.html").read_text(encoding="utf-8")
    script = (ROOT / "src/netsentinel/static/forensics.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "src/netsentinel/static/forensics.css").read_text(encoding="utf-8")
    for element_id in (
        "forensicReportsList",
        "newForensicReportDetails",
        "forensicReportForm",
        "forensicReportProcesses",
        "forensicReportResults",
        "forensicReportLimitations",
        "forensicReportOriginalDisposition",
        "forensicReportDerivativeDisposition",
        "forensicReportAmends",
        "forensicReportAmendmentReason",
    ):
        assert f'id="{element_id}"' in html
    assert "Borrador sin firma" in script
    assert '"/api/forensics/cases/" + encodeURIComponent(caseId) + "/reports"' in script
    assert 'payload.amends_report_id = payload.amends_report_id || null' in script
    assert "renderReports();" in script
    assert "installReportForm();" in script
    assert ".forensic-report-actions a:focus-visible" in stylesheet
    report_module = (ROOT / "src/netsentinel/forensics_report.py").read_text(encoding="utf-8")
    assert "Borrador sin firma" in html
    assert "Borrador sin firma" in script
    assert "No hay firma digital" in report_module


def test_guided_test_page_contains_in_app_scenarios_and_checks() -> None:
    """El asistente guía un paso a la vez, muestra resultados y no dispara escaneos."""
    html = (ROOT / "src/netsentinel/static/guided-test.html").read_text(encoding="utf-8")
    script = (ROOT / "src/netsentinel/static/guided-test.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "src/netsentinel/static/guided-test.css").read_text(encoding="utf-8")

    for element_id in (
        "wizardStepTitle",
        "wizardObjective",
        "wizardWhy",
        "wizardInstructions",
        "wizardExpected",
        "wizardAutomaticPanel",
        "wizardActionLink",
        "wizardManualResultPanel",
        "wizardSummaryPanel",
        "wizardCopyReport",
        "wizardDownloadReport",
        "wizardRecoveryDetails",
    ):
        assert f'id="{element_id}"' in html

    assert 'target="_blank"' in html
    assert 'data-wizard-outcome="passed"' in html
    assert 'data-wizard-outcome="failed"' in html
    assert 'data-wizard-outcome="blocked"' in html
    assert "no llama a" in html
    assert "synthetic-test-fixture" in script
    assert 'getJson("/api/health")' in script
    assert 'getJson("/api/scans?limit=100")' in script
    assert 'getJson("/api/geolocation/map?limit=250")' in script
    assert 'method: "GET"' in script
    assert 'method: "POST"' not in script
    assert "netsentinel.acceptance-wizard.v2" in script
    assert "PRUEBA GUIADA" in script
    assert "wizard-summary-row" in script
    assert "prefers-reduced-motion" in stylesheet

    # The new experience replaces the dispersed checklist instead of duplicating it.
    assert 'data-guided-step="' not in html
    assert 'id="scenario-csv"' not in html


