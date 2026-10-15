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
        assert 'aria-label="Navegación principal"' in html
        assert 'class="top app-header"' in html, f"{page_name} must use the shared page header"
        assert 'class="app-brand"' in html and 'class="app-header-content"' in html
        assert 'class="app-header-utilities"' in html
