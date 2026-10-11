"""Lectura de configuración DNS local sin modificar el sistema."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path


def _clean_servers(values: str) -> list[str]:
    """Extrae direcciones IP de una lista de servidores DNS, sin aceptar texto arbitrario."""
    import ipaddress

    found: list[str] = []
    for token in re.split(r"[\s,;]+", values.strip()):
        if not token:
            continue
        token = token.strip("[]")
        try:
            address = str(ipaddress.ip_address(token.split("%", 1)[0]))
        except ValueError:
            continue
        if address not in found:
            found.append(address)
    return found


def _read_resolv_conf(path: Path = Path("/etc/resolv.conf")) -> list[str]:
    """Lee directivas nameserver en Unix; no ejecuta comandos externos."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    values = []
    for line in lines:
        directive = line.split("#", 1)[0].split(";", 1)[0].strip().split()
        if len(directive) >= 2 and directive[0].lower() == "nameserver":
            values.extend(_clean_servers(directive[1]))
    return values


def _windows_dns_servers() -> list[str]:
    """Lee servidores DNS del registro de Windows en modo de solo lectura."""
    try:
        import winreg
    except ImportError:
        return []

    locations = [
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters",
         ("NameServer", "DhcpNameServer")),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters",
         ("NameServer", "DhcpNameServer")),
    ]
    result: list[str] = []
    for root, path, names in locations:
        try:
            with winreg.OpenKey(root, path) as key:
                for name in names:
                    try:
                        value, _kind = winreg.QueryValueEx(key, name)
                    except OSError:
                        continue
                    if isinstance(value, str):
                        for address in _clean_servers(value):
                            if address not in result:
                                result.append(address)
        except OSError:
            pass

    # Las interfaces suelen tener servidores DHCP específicos; leerlos evita
    # depender exclusivamente de los valores globales.
    interfaces = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, interfaces) as root_key:
            count = winreg.QueryInfoKey(root_key)[0]
            for index in range(count):
                try:
                    interface = winreg.EnumKey(root_key, index)
                    with winreg.OpenKey(root_key, interface) as key:
                        for name in ("NameServer", "DhcpNameServer"):
                            try:
                                value, _kind = winreg.QueryValueEx(key, name)
                            except OSError:
                                continue
                            if isinstance(value, str):
                                for address in _clean_servers(value):
                                    if address not in result:
                                        result.append(address)
                except OSError:
                    continue
    except OSError:
        pass
    return result


def get_dns_configuration() -> dict:
    """Devuelve los servidores DNS visibles localmente y explica límites de la lectura."""
    system = platform.system().lower()
    if system == "windows":
        servers = _windows_dns_servers()
        source = "windows-registry"
        note = "Lectura de valores DNS del registro; algunos adaptadores o políticas pueden usar configuración adicional."
    else:
        servers = _read_resolv_conf()
        source = "resolv.conf"
        note = (
            "En macOS y algunos Linux, esta vista puede omitir DNS por interfaz, VPN, split DNS o resolvedores locales."
        )
    return {
        "platform": system or "unknown",
        "servers": servers,
        "count": len(servers),
        "source": source,
        "detected": bool(servers),
        "note": note if servers else note + " No se detectaron direcciones en la fuente consultada.",
    }
