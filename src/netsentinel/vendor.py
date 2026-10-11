"""Identificación de fabricantes desde una base OUI local y opcional.

No realiza consultas externas ni transmite direcciones MAC. Se acepta tanto un CSV
mínimo (prefix,vendor) como el CSV de registros MA-L/MA-M/MA-S de IEEE, con columnas
"Assignment" y "Organization Name".
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

from .config import data_dir

_HEX = re.compile(r"^[0-9A-F]{6,9}$")


def oui_database_path() -> Path:
    """Ubicación del archivo OUI local, sin dependencia de red."""
    return data_dir() / "oui.csv"


def normalize_prefix(value: str) -> str | None:
    normalized = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
    if len(normalized) not in (6, 7, 9) or not _HEX.fullmatch(normalized):
        return None
    return normalized


def is_locally_administered(mac_address: str) -> bool:
    """True si el bit U/L está activado; puede indicar una MAC aleatoria o manual."""
    try:
        first_octet = int(mac_address.replace("-", ":").split(":")[0], 16)
    except (ValueError, IndexError):
        return False
    return bool(first_octet & 0x02)


def is_unicast(mac_address: str) -> bool:
    """Indica si la MAC es unicast (bit I/G a cero)."""
    try:
        first_octet = int(mac_address.replace("-", ":").split(":")[0], 16)
    except (ValueError, IndexError):
        return False
    return not bool(first_octet & 0x01)


def _read_database(path: Path) -> dict[str, str]:
    vendors: dict[str, str] = {}
    if not path.is_file():
        return vendors
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                return vendors
            names = {name.casefold().strip(): name for name in reader.fieldnames if name}
            prefix_column = names.get("prefix") or names.get("oui_prefix") or names.get("assignment")
            vendor_column = names.get("vendor") or names.get("organization name") or names.get("organization")
            if not prefix_column or not vendor_column:
                return vendors
            for row in reader:
                prefix = normalize_prefix(row.get(prefix_column, ""))
                vendor = (row.get(vendor_column) or "").strip()
                if prefix and vendor:
                    vendors[prefix] = vendor[:180]
    except (OSError, csv.Error, UnicodeError):
        return {}
    return vendors


@lru_cache(maxsize=8)
def _cached_database(path_text: str, mtime_ns: int, size: int) -> dict[str, str]:
    return _read_database(Path(path_text))


def manufacturer_for_mac(mac_address: str, database_path: Path | None = None) -> str | None:
    """Busca la asignación local más específica (MA-S, MA-M y MA-L)."""
    path = database_path or oui_database_path()
    try:
        stat = path.stat()
        records = _cached_database(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None
    compact = re.sub(r"[^0-9A-F]", "", mac_address.upper())
    if len(compact) != 12:
        return None
    for length in (9, 7, 6):
        vendor = records.get(compact[:length])
        if vendor:
            return vendor
    return None
