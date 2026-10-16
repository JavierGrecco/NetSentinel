"""Pruebas unitarias del validador de tamaños para la revisión responsive."""

import pytest

from scripts.check_responsive_ui import DEFAULT_VIEWPORTS, parse_viewports


def test_default_viewports_cover_small_screens_and_layout_breakpoints():
    sizes = {(viewport.width, viewport.height) for viewport in DEFAULT_VIEWPORTS}
    widths = {width for width, _ in sizes}

    assert (320, 640) in sizes
    assert (390, 844) in sizes
    assert (1920, 1080) in sizes
    # Incluye ambos lados del breakpoint de la cuadrícula del Inventario.
    assert 1080 in widths
    assert 1081 in widths
    # También cubre los breakpoints del encabezado y del marco compartido.
    assert {560, 620, 760, 768, 900, 1024}.issubset(widths)


def test_custom_viewport_list_is_parsed_and_spaces_are_allowed():
    result = parse_viewports(" 320x640, 390 x 844, 1440X900 ")

    assert [(item.width, item.height) for item in result] == [
        (320, 640),
        (390, 844),
        (1440, 900),
    ]


@pytest.mark.parametrize(
    "value",
    [
        "",
        "mobile",
        "320",
        "279x640",
        "4000x900",
        "390x319",
        "390x2200",
        "390x844,390x844",
    ],
)
def test_invalid_viewport_values_are_rejected(value):
    with pytest.raises(ValueError):
        parse_viewports(value)
