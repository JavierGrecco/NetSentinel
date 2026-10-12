"""Herramientas DNS de solo lectura para NetSentinel."""

from __future__ import annotations

import ipaddress
import json
import socket
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock


# Caché acotada: evita repetir consultas PTR al inspeccionar varias veces una IP.
_PTR_CACHE_TTL_SECONDS = 300
_PTR_CACHE_MAX_ENTRIES = 256
# System name resolution can block inside libc/OS resolver code. Run it in a
# terminable child so a stalled resolver cannot pin a request worker indefinitely.
DNS_RESOLVER_TIMEOUT_SECONDS = 3.0
_ptr_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_ptr_cache_lock = Lock()


class DNSLookupError(OSError):
    """Error DNS con una categoría estable para la API y la interfaz."""

    def __init__(self, message: str, kind: str):
        super().__init__(message)
        self.kind = kind


def _resolver_error_kind_from_code(code: object) -> str:
    """Classify resolver errors using platform constants, not localized messages."""
    missing_codes = {
        value for value in (
            getattr(socket, "EAI_NONAME", None),
            getattr(socket, "EAI_NODATA", None),
        ) if value is not None
    }
    if code in missing_codes:
        return "not_found"
    if code == getattr(socket, "EAI_AGAIN", object()):
        return "temporary"
    return "resolver_error"


def _resolver_error_kind(exc: socket.gaierror) -> str:
    """Clasifica errores comunes sin depender de textos localizados del sistema."""
    return _resolver_error_kind_from_code(exc.errno)


def _resolver_error_message(operation: str, kind: str) -> str:
    """Return a safe, localized summary for a bounded resolver failure."""
    if kind == "not_found":
        return (
            "El resolvedor no encontró ese nombre."
            if operation == "forward"
            else "No se encontró un registro PTR para esa dirección."
        )
    if kind == "temporary":
        return "El resolvedor DNS no respondió a tiempo; probá nuevamente."
    return (
        "El resolvedor DNS devolvió un error."
        if operation == "forward"
        else "El resolvedor DNS devolvió un error al consultar PTR."
    )


_RESOLVER_CHILD_SCRIPT = """
import ipaddress
import json
import socket
import sys

operation, value = sys.argv[1:3]
try:
    if operation == "forward":
        records = socket.getaddrinfo(
            value, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
        addresses = sorted({
            str(ipaddress.ip_address(item[4][0].split("%", 1)[0]))
            for item in records
        })
        print(json.dumps({"addresses": addresses}))
    elif operation == "reverse":
        parsed = ipaddress.ip_address(value)
        sockaddr = (str(parsed), 0, 0, 0) if parsed.version == 6 else (str(parsed), 0)
        hostname, _service = socket.getnameinfo(sockaddr, socket.NI_NAMEREQD)
        print(json.dumps({"hostname": hostname}))
    else:
        raise ValueError("unsupported resolver operation")
except socket.gaierror as exc:
    print(json.dumps({"error": "gaierror", "errno": exc.errno}))
    sys.exit(2)
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__}))
    sys.exit(3)
"""


def _run_resolver_child(operation: str, value: str) -> dict:
    """Run one system-resolver query with a hard deadline and validate its output."""
    if operation not in {"forward", "reverse"}:
        raise ValueError("Operación DNS no admitida.")
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _RESOLVER_CHILD_SCRIPT, operation, value],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=DNS_RESOLVER_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise DNSLookupError(
            "El resolvedor DNS no respondió a tiempo; probá nuevamente.",
            "temporary",
        ) from exc
    except OSError as exc:
        raise DNSLookupError(
            "No se pudo iniciar una consulta limitada al resolvedor del sistema.",
            "resolver_error",
        ) from exc

    try:
        payload = json.loads(completed.stdout.strip())
    except (json.JSONDecodeError, TypeError, AttributeError) as exc:
        raise DNSLookupError(
            _resolver_error_message(operation, "resolver_error"),
            "resolver_error",
        ) from exc
    if not isinstance(payload, dict):
        raise DNSLookupError(
            _resolver_error_message(operation, "resolver_error"),
            "resolver_error",
        )

    if payload.get("error"):
        if payload.get("error") == "gaierror":
            kind = _resolver_error_kind_from_code(payload.get("errno"))
        else:
            kind = "resolver_error"
        raise DNSLookupError(_resolver_error_message(operation, kind), kind)

    if completed.returncode != 0:
        raise DNSLookupError(
            _resolver_error_message(operation, "resolver_error"),
            "resolver_error",
        )
    return payload


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
    """Consulta A/AAAA con el resolvedor del sistema y un plazo terminable."""
    normalized = _normalize_hostname(hostname)
    payload = _run_resolver_child("forward", normalized)
    raw_addresses = payload.get("addresses")
    if not isinstance(raw_addresses, list) or any(not isinstance(item, str) for item in raw_addresses):
        raise DNSLookupError(_resolver_error_message("forward", "resolver_error"), "resolver_error")

    addresses_set: set[str] = set()
    try:
        for address in raw_addresses:
            addresses_set.add(str(ipaddress.ip_address(address.split("%", 1)[0])))
    except ValueError as exc:
        raise DNSLookupError(_resolver_error_message("forward", "resolver_error"), "resolver_error") from exc
    addresses = sorted(
        addresses_set,
        key=lambda value: (ipaddress.ip_address(value).version, int(ipaddress.ip_address(value))),
    )
    return {
        "hostname": normalized,
        "addresses": [
            {"ip": address, "family": "IPv4" if ipaddress.ip_address(address).version == 4 else "IPv6"}
            for address in addresses
        ],
        "count": len(addresses),
        "source": "system-resolver",
        "timeout_seconds": DNS_RESOLVER_TIMEOUT_SECONDS,
        "note": "La resolución DNS no verifica la identidad ni la confiabilidad del equipo.",
    }


def reverse_lookup_ip(address: str) -> dict:
    """Consulta PTR para una IP literal con un plazo terminable."""
    try:
        parsed = ipaddress.ip_address(address.strip())
    except ValueError as exc:
        raise ValueError("Ingresá una dirección IPv4 o IPv6 válida.") from exc

    normalized_ip = str(parsed)
    payload = _run_resolver_child("reverse", normalized_ip)
    hostname = payload.get("hostname")
    if not isinstance(hostname, str):
        raise DNSLookupError(_resolver_error_message("reverse", "resolver_error"), "resolver_error")
    hostname = hostname.rstrip(".").lower()
    if not hostname:
        raise DNSLookupError(_resolver_error_message("reverse", "resolver_error"), "resolver_error")
    return {
        "ip": normalized_ip,
        "hostname": hostname,
        "source": "system-resolver",
        "record_type": "PTR",
        "timeout_seconds": DNS_RESOLVER_TIMEOUT_SECONDS,
        "note": "Un registro PTR es información declarada por DNS; no verifica la identidad ni la confiabilidad del equipo.",
    }



def cached_reverse_lookup_ip(address: str) -> dict:
    """Consulta PTR bajo demanda con caché TTL acotada y marca temporal de resolución.

    Solo almacena resultados correctos; los errores temporales no quedan cacheados.
    La llamada inicial sigue usando el resolvedor del sistema y sus límites de tiempo.
    """
    try:
        normalized_ip = str(ipaddress.ip_address(address.strip()))
    except ValueError as exc:
        raise ValueError("Ingresá una dirección IPv4 o IPv6 válida.") from exc

    now = time.monotonic()
    with _ptr_cache_lock:
        entry = _ptr_cache.get(normalized_ip)
        if entry is not None:
            expires_at, cached_result = entry
            if expires_at > now:
                _ptr_cache.move_to_end(normalized_ip)
                result = dict(cached_result)
                result["cache_hit"] = True
                return result
            del _ptr_cache[normalized_ip]

    result = reverse_lookup_ip(normalized_ip)
    result["resolved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["cache_hit"] = False
    with _ptr_cache_lock:
        _ptr_cache[normalized_ip] = (time.monotonic() + _PTR_CACHE_TTL_SECONDS, dict(result))
        _ptr_cache.move_to_end(normalized_ip)
        while len(_ptr_cache) > _PTR_CACHE_MAX_ENTRIES:
            _ptr_cache.popitem(last=False)
    return result


def clear_ptr_cache() -> None:
    """Limpia la caché PTR; útil para pruebas y para reiniciar estado en memoria."""
    with _ptr_cache_lock:
        _ptr_cache.clear()
