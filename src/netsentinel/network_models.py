"""Contratos de datos compartidos por las funciones de red.

Este archivo contiene tipos sencillos que pueden usar descubrimiento, inventario
y persistencia. No depende de esos módulos: así la base de datos no necesita
importar el motor que obtiene las observaciones.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Neighbor:
    """Un vecino observado en la tabla local de vecinos del sistema operativo."""

    ip_address: str
    mac_address: str
    interface: str | None = None
    source: str = "system-neighbor-table"
