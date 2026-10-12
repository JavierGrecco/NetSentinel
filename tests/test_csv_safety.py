import pytest

from netsentinel.csv_safety import spreadsheet_safe_text


@pytest.mark.parametrize(
    "value",
    [
        "=1+1",
        "+SUM(1,1)",
        "-1+2",
        "@SUM(1,1)",
        "  =1+1",
        "\t+SUM(1,1)",
        "\r\n@SUM(1,1)",
        "\x00=1+1",
        "\x0b@cmd",
        "\x00\u2003=1+1",
        "\u00a0+SUM(1,1)",
    ],
)
def test_spreadsheet_safe_text_prefixes_formula_like_values(value):
    assert spreadsheet_safe_text(value) == "'" + value


@pytest.mark.parametrize("value", ["ordinary text", "192.168.1.1", "", None, 10, -10, 1.25, True])
def test_spreadsheet_safe_text_preserves_non_formula_values(value):
    assert spreadsheet_safe_text(value) == value
