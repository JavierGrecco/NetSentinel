from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "/": ("src/netsentinel/static/index.html", "/"),
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
EXPECTED_HREFS = ["/", "/findings", "/monitors", "/tools", "/activity", "/world-map", "/guided-test"]


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
    """La guía se ve dentro de la app y ofrece escenarios concretos y comprobables."""
    html = (ROOT / "src/netsentinel/static/guided-test.html").read_text(encoding="utf-8")
    script = (ROOT / "src/netsentinel/static/guided-test.js").read_text(encoding="utf-8")
    for scenario_id in ("scenario-csv", "scenario-rejections", "scenario-map", "scenario-forensics", "scenario-forensics-safety", "scenario-forensics-manifests", "scenario-forensics-report"):
        assert f'id="{scenario_id}"' in html
    assert len(re.findall(r'data-guided-step="[^"]+"', html)) == 19
    assert 'id="copySetupCommand"' in html
    assert "--force" not in html
    assert 'id="guidedProgressBar"' in html
    assert 'aria-valuemax="19"' in html
    assert 'data-guided-step="forensics-custody-transfer"' in html
    assert 'id="checkMapApi"' in html
    assert 'id="checkForensicsApi"' in html
    assert 'id="copyEvidenceChangeCommand"' in html
    assert 'id="evidenceChangeCommand"' in html
    assert "netsentinel.guided-test.progress.v1" in script
    assert 'checkApi("/api/geolocation/map?limit=1"' in script
    assert 'checkApi("/api/forensics/cases?limit=1"' in script
