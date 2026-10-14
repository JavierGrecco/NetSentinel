"""Validación pura de objetivos y límites de los controles de monitorización.

Este módulo no realiza conexiones ni escribe en SQLite. Mantiene las reglas de
entrada separadas del adaptador que ejecuta cada comprobación.
"""
from __future__ import annotations

from ipaddress import ip_address
import re
from urllib.parse import urlsplit


MIN_INTERVAL_SECONDS = 15
MAX_INTERVAL_SECONDS = 86_400
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 10
SUPPORTED_KINDS = {"ping", "tcp", "http"}
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def valid_host(host: str) -> bool:
    host = host.strip().rstrip(".")
    if not host or len(host) > 253 or any(ch.isspace() for ch in host):
        return False
    try:
        ip_address(host.split("%", 1)[0])
        return True
    except ValueError:
        pass
    return all(_HOST_LABEL.fullmatch(label) for label in host.split("."))


def validate_spec(kind: str, target: str, interval_seconds: int, timeout_seconds: int) -> tuple[str, str, int, int]:
    kind = kind.strip().lower()
    target = target.strip()
    if kind not in SUPPORTED_KINDS:
        raise ValueError("Tipo de comprobación no admitido.")
    if not target or len(target) > 500 or any(ord(ch) < 32 for ch in target):
        raise ValueError("El objetivo está vacío o tiene un formato inválido.")
    if not MIN_INTERVAL_SECONDS <= int(interval_seconds) <= MAX_INTERVAL_SECONDS:
        raise ValueError(f"El intervalo debe estar entre {MIN_INTERVAL_SECONDS} y {MAX_INTERVAL_SECONDS} segundos.")
    if not MIN_TIMEOUT_SECONDS <= int(timeout_seconds) <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"El tiempo límite debe estar entre {MIN_TIMEOUT_SECONDS} y {MAX_TIMEOUT_SECONDS} segundos.")

    if kind == "ping":
        if not valid_host(target) or target.startswith("-"):
            raise ValueError("Para ping usá una IP o un nombre de host válido, sin argumentos adicionales.")
    elif kind == "tcp":
        if target.startswith("["):
            closing = target.find("]")
            if closing < 0 or target[closing + 1:closing + 2] != ":":
                raise ValueError("Para IPv6 usá el formato [dirección]:puerto.")
            host, port_text = target[1:closing], target[closing + 2:]
        else:
            if target.count(":") != 1:
                raise ValueError("Para TCP usá host:puerto; las direcciones IPv6 deben ir entre corchetes.")
            host, port_text = target.rsplit(":", 1)
        if not valid_host(host) or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            raise ValueError("El objetivo TCP debe ser host:puerto con un puerto entre 1 y 65535.")
    else:
        parsed = urlsplit(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Para HTTP usá una URL http:// o https:// sin credenciales incrustadas.")
        if not valid_host(parsed.hostname):
            raise ValueError("El host de la URL no es válido.")
        if parsed.query or parsed.fragment:
            raise ValueError("Por seguridad, la URL de monitorización no debe incluir query strings ni fragmentos; no coloques tokens en la dirección.")
        try:
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError("El puerto HTTP no es válido.")
        except ValueError as exc:
            raise ValueError("El puerto HTTP no es válido.") from exc
    return kind, target, int(interval_seconds), int(timeout_seconds)
