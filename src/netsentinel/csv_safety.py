"""Protección común de celdas CSV frente a interpretación como fórmulas."""

from __future__ import annotations

from typing import Any


_FORMULA_PREFIXES = ("=", "+", "-", "@")


def spreadsheet_safe_text(value: Any) -> Any:
    """Prefix formula-like text with an apostrophe without mutating source data.

    The whitespace check covers values that Excel may treat as formulas even when
    spaces, tabs, or line breaks precede the formula operator. Non-string cells
    remain typed values, so ordinary negative numbers are not rewritten.
    """
    if isinstance(value, str) and value.lstrip(" \t\r\n").startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value
