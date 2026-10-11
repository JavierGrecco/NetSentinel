"""Herramientas DNS de solo lectura para NetSentinel."""

from __future__ import annotations

import ipaddress
import socket


def _normalize_hostname(hostname: str) -> str:
    """Valida un nombre DNS simple; no admite URLs, puertos ni credenciales."""
    value = hostname.strip().rstrip(".")
    if not value or len(value) > 253 or "://" in value or any(ch in value for ch in "/\\@?#"):
        raise ValueError("Ingresá un nombre de host válido, sin protocolo, ruta ni puerto.")
    if value.startswith("[") or value.endswith("]"):
        raise ValueError("Ingresá el nombre de host sin corchetes.")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ValueError("Ingresá un nombre de host, no una dirección IP.")
    try:
        ascii_name = value.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("El nombre de host no es válido.") from exc
    labels = ascii_name.split(".")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
           or not all(ch.isalnum() or ch == "-" for ch in label) for label in labels):
        raise ValueError("El nombre de host no es válido.")
    return ascii_name


def lookup_hostname(hostname: str) -> dict:
    """Consulta A/AAAA a través del resolvedor del sistema, sin generar escaneo."""
    normalized = _normalize_hostname(hostname)
    try:
        records = socket.getaddrinfo(normalized, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise OSError("El resolvedor no pudo encontrar el nombre solicitado.") from exc
    addresses = sorted({record[4][0].split("%", 1)[0] for record in records},
                       key=lambda value: (ipaddress.ip_address(value).version, int(ipaddress.ip_address(value))))
    return {
        "hostname": normalized,
        "addresses": [
            {"ip": address, "family": "IPv4" if ipaddress.ip_address(address).version == 4 else "IPv6"}
            for address in addresses
        ],
        "count": len(addresses),
        "source": "system-resolver",
        "note": "La resolución DNS no verifica la identidad ni la confiabilidad del equipo.",
    }


def reverse_lookup_ip(address: str) -> dict:
    """Consulta PTR para una IP literal; no verifica la identidad del dispositivo."""
    try:
        parsed = ipaddress.ip_address(address.strip())
    except ValueError as exc:
        raise ValueError("Ingresá una dirección IPv4 o IPv6 válida.") from exc

    normalized_ip = str(parsed)
    try:
        hostname, _service = socket.getnameinfo(
            (normalized_ip, 0),
            socket.NI_NAMEREQD,
        )
    except (socket.gaierror, OSError) as exc:
        raise OSError("El resolvedor no devolvió un nombre PTR para esa dirección.") from exc

    hostname = hostname.rstrip(".").lower()
    if not hostname:
        raise OSError("El resolvedor devolvió un nombre PTR vacío.")
    return {
        "ip": normalized_ip,
        "hostname": hostname,
        "source": "system-resolver",
        "record_type": "PTR",
        "note": "Un registro PTR es información declarada por DNS; no verifica la identidad ni la confiabilidad del equipo.",
    }
