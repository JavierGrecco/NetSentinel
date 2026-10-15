"""Middleware y reglas de host/origen para proteger el panel local.

Las políticas de respuesta y CSP viven en security_headers.py. Este módulo
conserva el middleware utilizado por main.py y las funciones de compatibilidad.
"""
from __future__ import annotations

import ipaddress
import os
import re
import uuid
from urllib.parse import urlsplit

from fastapi import Request

from .security_headers import (
    _APP_HTML_PATHS,
    _apply_security_headers,
    _base_content_security_policy,
    _error_response,
    _inline_script_hashes,
    _inline_script_hashes_in_html,
    _request_id,
)

NETWORK_SIDE_EFFECT_GET_PATHS = frozenset({
    "/api/tools/dns/lookup",
    "/api/tools/dns/reverse",
})
_RFC1918_HOST_NETWORKS = tuple(
    ipaddress.IPv4Network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_IPV6_UNIQUE_LOCAL = ipaddress.IPv6Network("fc00::/7")
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
# These GET routes initiate DNS traffic. They must not be triggerable by pages
# from another origin merely by embedding a local URL in an image/link/script.
_NETWORK_SIDE_EFFECT_GET_PATHS = NETWORK_SIDE_EFFECT_GET_PATHS
_DEVICE_DNS_REVERSE_PATH = re.compile(r"^/api/devices/\d+/dns-reverse$")


def _host_is_allowed(host: str | None) -> bool:
    """Allow loopback/private LAN IPs and explicit extra hostnames only."""
    if not host:
        return False
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        extras = {
            item.strip().rstrip(".").lower()
            for item in os.environ.get("NETSENTINEL_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        }
        return normalized in extras
    if address.is_loopback:
        return True
    if isinstance(address, ipaddress.IPv4Address):
        return any(address in network for network in _RFC1918_HOST_NETWORKS)
    return address in _IPV6_UNIQUE_LOCAL


def _same_origin(origin: str, request: Request) -> bool:
    """Compare scheme, normalized host and effective port without trusting Origin."""
    try:
        parsed = urlsplit(origin)
        origin_host_value = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not origin_host_value:
        return False
    request_host = (request.url.hostname or "").rstrip(".").lower()
    origin_host = origin_host_value.rstrip(".").lower()
    request_scheme = request.url.scheme.lower()
    origin_scheme = parsed.scheme.lower()
    if request_host != origin_host or request_scheme != origin_scheme:
        return False
    try:
        request_port = request.url.port or (443 if request_scheme == "https" else 80)
        origin_port = parsed.port or (443 if origin_scheme == "https" else 80)
    except ValueError:
        return False
    return request_port == origin_port


def _is_network_side_effect_get(path: str) -> bool:
    """Identify GET endpoints that can initiate outbound DNS lookups."""
    return path in _NETWORK_SIDE_EFFECT_GET_PATHS or bool(_DEVICE_DNS_REVERSE_PATH.fullmatch(path))


async def protect_local_app(request: Request, call_next):
    """Mitiga DNS rebinding/CSRF y aplica cabeceras a todas las respuestas."""
    request_id = uuid.uuid4().hex[:12].upper()
    request.state.request_id = request_id
    if not _host_is_allowed(request.url.hostname):
        return _error_response(
            request,
            status_code=400,
            content={
                "detail": "Host no permitido para NetSentinel.",
                "error_code": "NS-HTTP-400",
                "request_id": request_id,
                "next_action": "Abrí NetSentinel usando la dirección local indicada por la aplicación.",
                "should_log": False,
                "registered_in_log": False,
            },
        )

    if request.method.upper() == "GET" and _is_network_side_effect_get(request.url.path):
        # Modern browsers expose Fetch Metadata even for image/link requests
        # whose Origin header may be absent. Direct navigation (Sec-Fetch-Site:
        # none) remains available; requests initiated by the app are same-origin.
        fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
        origin = request.headers.get("origin")
        cross_site_fetch = fetch_site and fetch_site not in {"same-origin", "none"}
        cross_origin_header = origin and not _same_origin(origin, request)
        if cross_site_fetch or cross_origin_header:
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Consulta de red iniciada desde otro origen bloqueada.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Iniciá la consulta desde el panel local de NetSentinel.",
                    "should_log": False,
                    "registered_in_log": False,
                },
            )

    if request.method.upper() in _MUTATING_METHODS:
        fetch_site = request.headers.get("sec-fetch-site", "").strip().lower()
        # Reject same-site as well as cross-site requests. A malicious sibling
        # origin may be "same-site" without being the exact UI origin; browser
        # Fetch Metadata is available even when an Origin header is omitted.
        non_same_origin_fetch = fetch_site and fetch_site not in {"same-origin", "none"}
        if non_same_origin_fetch:
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Solicitud desde otro origen bloqueada.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Iniciá la operación desde el panel local de NetSentinel.",
                    "should_log": False,
                    "registered_in_log": False,
                },
            )
        origin = request.headers.get("origin")
        if origin and not _same_origin(origin, request):
            return _error_response(
                request,
                status_code=403,
                content={
                    "detail": "Origen no permitido para esta operación.",
                    "error_code": "NS-HTTP-403",
                    "request_id": request_id,
                    "next_action": "Recargá el panel local y volvé a intentar la operación desde allí.",
                    "should_log": False,
                    "registered_in_log": False,
                },
            )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return _apply_security_headers(response, page_path=request.url.path)
