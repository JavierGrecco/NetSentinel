"""Funciones pequeñas compartidas por los repositorios del inventario."""
from __future__ import annotations

import sqlite3
from ipaddress import ip_address
from typing import Any


def _device_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["trusted"] = bool(item["trusted"])
    item["mac_locally_administered"] = bool(item.get("mac_locally_administered", 0))
    return item


def _ip_sort_key(address: str) -> tuple[int, int]:
    parsed = ip_address(address)
    return (parsed.version, int(parsed))
