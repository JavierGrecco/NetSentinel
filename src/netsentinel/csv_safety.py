"""Protección común de celdas CSV frente a interpretación como fórmulas."""

from __future__ import annotations

import re
from typing import Any


_FORMULA_PREFIX_RE = re.compile(r"^[\s\x00-\x1f]*[=+@-]")


def spreadsheet_safe_text(value: Any) -> Any:
    """Prefix formula-like text with an apostrophe without mutating source data.

    The whitespace check covers values that Excel may treat as formulas even when
    spaces, tabs, or line breaks precede the formula operator. Non-string cells
    remain typed values, so ordinary negative numbers are not rewritten.
    """
    if isinstance(value, str) and _FORMULA_PREFIX_RE.match(value):
        return "'" + value
    return value
