"""Herramientas DNS de solo lectura para NetSentinel."""

from __future__ import annotations

import ipaddress
import socket
import time
from collections import OrderedDict
from datetime import datetime, timezone
from threading import Lock


# Caché acotada: evita repetir consultas PTR al inspeccionar varias veces una IP.
_PTR_CACHE_TTL_SECONDS = 300
_PTR_CACHE_MAX_ENTRIES = 256
_ptr_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()
_ptr_cache_lock = Lock()


class DNSLookupError(OSError):
    """Error DNS con una categoría estable para la API y la interfaz."""

    def __init__(self, message: str, kind: str):
        super().__init__(message)
        self.kind = kind


def _resolver_error_kind(exc: socket.gaierror) -> str:
    """Clasifica errores comunes sin depender de textos localizados del sistema."""
    code = exc.errno
    if code == getattr(socket, "EAI_NONAME", object()) or code == getattr(socket, "EAI_NODATA", object()):
        return "not_found"
    if code == getattr(socket, "EAI_AGAIN", object()):
        return "temporary"
    return "resolver_error"


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
        kind = _resolver_error_kind(exc)
        if kind == "not_found":
            message = "El resolvedor no encontró ese nombre."
        elif kind == "temporary":
            message = "El resolvedor DNS no respondió a tiempo; probá nuevamente."
        else:
            message = "El resolvedor DNS devolvió un error."
        raise DNSLookupError(message, kind) from exc
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
        sockaddr = (normalized_ip, 0, 0, 0) if parsed.version == 6 else (normalized_ip, 0)
        hostname, _service = socket.getnameinfo(
            sockaddr,
            socket.NI_NAMEREQD,
        )
    except socket.gaierror as exc:
        kind = _resolver_error_kind(exc)
        if kind == "not_found":
            message = "No se encontró un registro PTR para esa dirección."
        elif kind == "temporary":
            message = "El resolvedor DNS no respondió a tiempo; probá nuevamente."
        else:
            message = "El resolvedor DNS devolvió un error al consultar PTR."
        raise DNSLookupError(message, kind) from exc
    except OSError as exc:
        raise DNSLookupError("No se pudo completar la consulta PTR.", "resolver_error") from exc

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
