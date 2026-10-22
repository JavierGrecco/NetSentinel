"""Regresiones para la estructura visual compartida de NetSentinel."""

import re
from pathlib import Path


STATIC = Path("src/netsentinel/static")
PAGE_NAMES = (
    "index.html",
    "network.html",
    "findings.html",
    "monitors.html",
    "tools.html",
    "activity.html",
    "geolocation.html",
    "guided-test.html",
)


def test_theme_card_styles_are_visible_and_keyboard_accessible():
    css = (STATIC / "theme.css").read_text(encoding="utf-8")

    assert ".theme-options" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert ".theme-option-icon" in css
    assert ".app-header-utilities .theme-option-card" in css
    assert "min-height: 48px" in css
    assert ".app-header-content > .primary-nav" in css
    assert "grid-template-columns: repeat(8, minmax(0, 1fr))" in css
    assert "min-height: 42px" in css
    assert ".app-section-title" in css
    assert "background: #101827" in css
    assert "background: #dfe5ec" in css
    assert "background: #ffffff" in css
    assert 'input[type="radio"]:checked + .theme-option-card' in css
    assert 'input[type="radio"]:focus-visible + .theme-option-card' in css
    assert "prefers-reduced-motion: reduce" in css


def test_theme_options_are_unique_and_have_one_default_selection():
    for page_name in PAGE_NAMES:
        html = (STATIC / page_name).read_text(encoding="utf-8")
        options = re.findall(r'<input\b([^>]*name="themeSelect"[^>]*)>', html)
        assert len(options) == 3, f"{page_name} must offer exactly three theme cards"

        ids = [re.search(r'\bid="([^"]+)"', option).group(1) for option in options]
        values = [re.search(r'\bvalue="([^"]+)"', option).group(1) for option in options]
        checked = [option for option in options if re.search(r"\schecked(?:\s|$)", option)]
        assert len(ids) == len(set(ids)), f"{page_name} has duplicate theme control IDs"
        assert set(values) == {"dark", "medium", "light"}
        assert len(checked) == 1 and 'value="dark"' in checked[0]


def test_each_page_uses_unique_html_ids():
    """Los ID duplicados rompen los enlaces entre controles y JavaScript."""
    for page_name in PAGE_NAMES:
        html = (STATIC / page_name).read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', html)
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        assert not duplicates, f"{page_name} has duplicate HTML IDs: {duplicates}"


def test_world_map_refresh_controls_are_both_wired_and_share_loading_state():
    """Los dos botones de actualización deben responder y deshabilitarse juntos."""
    html = (STATIC / "geolocation.html").read_text(encoding="utf-8")
    script = (STATIC / "geolocation.js").read_text(encoding="utf-8")

    assert html.count('class="quiet js-refresh-world-map"') == 2
    assert 'id="refreshWorldMapTop"' in html
    assert 'id="refreshWorldMap"' in html
    assert 'document.querySelectorAll(".js-refresh-world-map").forEach((button) => {' in script
    assert 'refreshButtons.forEach((button) => { button.disabled = true; });' in script
    assert 'refreshButtons.forEach((button) => { button.disabled = false; });' in script


def test_shared_theme_defines_one_page_and_control_scale():
    css = (STATIC / "theme.css").read_text(encoding="utf-8")

    # These values form the common frame; local CSS must not override the shell.
    assert "--ui-content-width: 1320px" in css
    assert "--ui-page-gutter: 24px" in css
    assert "--ui-section-gap: 16px" in css
    assert "--ui-panel-radius: 16px" in css
    assert "--ui-control-height: 40px" in css
    assert "html[data-theme] body > main" in css
    assert "max-width: var(--ui-content-width) !important" in css
    assert "scrollbar-gutter: stable" in css
    assert "@media (max-width: 760px)" in css
    assert "@media (max-width: 560px)" in css


def test_theme_script_syncs_selection_and_persists_across_tabs():
    script = (STATIC / "theme.js").read_text(encoding="utf-8")

    assert 'const STORAGE_KEY = "netsentinel-theme"' in script
    assert 'const CONTROL_NAME = "themeSelect"' in script
    assert 'querySelectorAll(`input[name="${CONTROL_NAME}"]`)' in script
    assert "control.checked = control.value === theme" in script
    assert 'control.addEventListener("change"' in script
    assert "localStorage.setItem(STORAGE_KEY, selected)" in script
    assert 'window.addEventListener("storage"' in script


def test_every_page_keeps_a_fixed_brand_and_a_distinct_section_heading():
    expected_titles = {
        "index.html": "Inventario de red",
        "findings.html": "Hallazgos con evidencia",
        "monitors.html": "Monitorización",
        "tools.html": "Herramientas de red",
        "activity.html": "Actividad y telemetría",
        "geolocation.html": "Mapa mundial de IP",
    }

    for page_name, section_title in expected_titles.items():
        html = (STATIC / page_name).read_text(encoding="utf-8")
        assert 'class="app-brand-name">NetSentinel</div>' in html, page_name
        assert 'class="eyebrow">Observabilidad local</div>' in html, page_name
        assert f'<h1 class="app-section-title">{section_title}</h1>' in html, page_name
        assert 'class="app-section-description"' in html, page_name

        brand_start = html.index('class="app-brand"')
        section_start = html.index('class="app-section-heading"')
        navigation_start = html.index('class="primary-nav"')
        assert brand_start < section_start < navigation_start, (
            f"{page_name} must present brand, current section, then full-width navigation"
        )
        assert html.count('aria-current="page"') == 1, (
            f"{page_name} must mark exactly one current navigation item"
        )


def test_all_main_pages_load_shared_layout_after_module_styles():
    for page_name in PAGE_NAMES:
        html = (STATIC / page_name).read_text(encoding="utf-8")
        links = re.findall(
            r'<link\b[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>',
            html,
            flags=re.IGNORECASE,
        )
        assert "/static/theme.css" in links, (
            f"{page_name} must load the shared design layer."
        )
        assert links[-1] == "/static/theme.css", (
            f"{page_name} must load the shared design layer after local styles."
        )
        assert 'id="themeSelect"' in html
        assert 'class="theme-control"' in html
        assert 'class="theme-options"' in html
        assert 'role="radiogroup" aria-label="Tema visual"' in html
        assert 'class="theme-option-card"' in html
        assert 'id="themeSelectMedium"' in html and 'id="themeSelectLight"' in html
        assert '<select id="themeSelect"' not in html, f"{page_name} must not use the old theme dropdown"
        assert html.count('name="themeSelect" type="radio"') == 3
        assert 'aria-hidden="true" focusable="false"' in html
        assert 'aria-label="Navegación principal"' in html
        assert 'class="top app-header"' in html, f"{page_name} must use the shared page header"
        assert 'class="app-brand"' in html and 'class="app-header-content"' in html
        assert 'class="app-header-utilities"' in html



def test_inventory_dashboard_uses_available_width_and_stacks_on_narrow_screens():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    css = (STATIC / "styles.css").read_text(encoding="utf-8")

    assert '<div class="layout inventory-layout">' in html
    assert '<div class="inventory-column inventory-primary-column">' in html
    assert '<div class="inventory-column inventory-secondary-column">' in html

    # El orden del documento sigue las dos columnas: Inventario y Diagnóstico,
    # seguido de Actividad reciente e Historial de lecturas.
    panel_classes = (
        'class="panel inventory-panel"',
        'class="panel diagnostics-panel"',
        'class="panel activity-panel"',
        'class="panel scans-panel"',
    )
    positions = [html.index(panel_class) for panel_class in panel_classes]
    assert positions == sorted(positions), "Dashboard panels must keep a useful column reading order"

    assert "grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr);" in css
    assert ".inventory-column {" in css
    assert "flex-direction: column;" in css
    assert "gap: 16px;" in css
    assert '@media (max-width: 1080px)' in css
    assert "grid-template-columns: minmax(0, 1fr);" in css

    # The table must stay readable by scrolling within its own container.
    assert ".table-wrap{overflow:auto;width:100%}" in css


def test_every_main_page_uses_the_shared_content_shell():
    """Las secciones principales comparten el mismo contenedor principal."""
    for page_name in PAGE_NAMES:
        html = (STATIC / page_name).read_text(encoding="utf-8")
        assert '<main class="wrap">' in html, (
            f"{page_name} must use the shared content shell"
        )

def test_guided_acceptance_lab_covers_topology_zeek_and_isolated_setup():
    """El recorrido local incluye los módulos integrados y prepara datos ficticios."""
    html = (STATIC / "guided-test.html").read_text(encoding="utf-8")
    assert 'id="scenario-topology"' in html
    assert 'id="scenario-zeek"' in html
    assert 'id="checkTopologyApi"' in html
    assert 'id="topologyApiStatus"' in html
    assert 'data-guided-step="topology-api"' in html
    assert 'data-guided-step="zeek-preview"' in html
    assert 'data-guided-step="zeek-idempotence"' in html
    assert "seed_manual_test_database.py --device-ip 192.168.56.20 --include-topology" in html
    assert 'export SCENARIO_DIR="$PWD/netsentinel-test-artifacts/' in html
    assert 'manual-scenarios-$(date +%Y%m%d-%H%M%S)-$"' in html
    assert 'aria-valuemax="24"' in html
    assert len(re.findall(r'<article class="panel guided-scenario" id="scenario-[^"]+">', html)) == 9
    assert len(re.findall(r'data-guided-step="[^"]+"', html)) == 24
