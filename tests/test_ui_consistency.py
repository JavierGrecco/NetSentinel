"""Regresiones para la estructura visual compartida de NetSentinel."""

import re
from pathlib import Path


STATIC = Path("src/netsentinel/static")
PAGE_NAMES = (
    "index.html",
    "findings.html",
    "monitors.html",
    "tools.html",
    "activity.html",
)


def test_theme_card_styles_are_visible_and_keyboard_accessible():
    css = (STATIC / "theme.css").read_text(encoding="utf-8")

    assert ".theme-options" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert ".theme-option-icon" in css
    assert ".app-header-utilities .theme-option-card" in css
    assert "min-height: 48px" in css
    assert ".app-header-content > .primary-nav" in css
    assert "grid-template-columns: repeat(5, minmax(0, 1fr))" in css
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
