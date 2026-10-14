"""Controles HTTP compartidos para proteger el panel local.

Este módulo concentra la validación del host y del origen, las cabeceras defensivas
y la política CSP de las páginas empaquetadas. No crea la aplicación ni registra rutas.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse, Response


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


_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STATIC = _STATIC_DIR / "index.html"
_MONITORS_STATIC = _STATIC_DIR / "monitors.html"
_ACTIVITY_STATIC = _STATIC_DIR / "activity.html"
_APP_HTML_PATHS = {
    "/": _STATIC,
    "/monitors": _MONITORS_STATIC,
    "/activity": _ACTIVITY_STATIC,
    "/tools": _STATIC_DIR / "tools.html",
    "/findings": _STATIC_DIR / "findings.html",
}
_INLINE_SCRIPT_PATTERN = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def _inline_script_hashes_in_html(content: str) -> tuple[str, ...]:
    """Return CSP SHA-256 sources for non-empty inline scripts in trusted HTML."""
    # The HTML parser normalizes CRLF and CR to LF before calculating script hashes.
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    hashes: list[str] = []
    for match in _INLINE_SCRIPT_PATTERN.finditer(normalized):
        script = match.group(1)
        if not script.strip():
            continue
        digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
        hashes.append(f"'sha256-{digest}'")
    return tuple(hashes)


def _inline_script_hashes(path: str) -> tuple[str, ...]:
    """Hash trusted inline script blocks in one packaged HTML page for CSP."""
    html_path = _APP_HTML_PATHS.get(path)
    if html_path is None or not html_path.is_file():
        return ()
    return _inline_script_hashes_in_html(html_path.read_text(encoding="utf-8"))


def _base_content_security_policy(path: str) -> str:
    """Allow fixed inline scripts by content hash, not by the unsafe-inline escape."""
    script_sources = " ".join(("'self'", *_inline_script_hashes(path)))
    return (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "frame-src 'none'; form-action 'self'; "
        f"script-src {script_sources}; style-src 'self'; "
        "img-src 'self' data:; font-src 'self' data:; connect-src 'self'"
    )


def _apply_security_headers(response: Response, *, page_path: str = "") -> Response:
    """Evita cachés locales y aplica una política defensiva uniforme al navegador."""
    # El inventario, el historial y las exportaciones pueden revelar topología y
    # actividad sensibles. No permitimos que navegadores o proxies los almacenen.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault("Content-Security-Policy", _base_content_security_policy(page_path))
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
    return response


def _request_id(request: Request) -> str:
    """Return the identifier created for this request, including handler fallbacks."""
    current = getattr(request.state, "request_id", None)
    if isinstance(current, str) and re.fullmatch(r"[A-F0-9]{12}", current):
        return current
    return uuid.uuid4().hex[:12].upper()


def _error_response(
    request: Request,
    *,
    status_code: int,
    content: dict,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Add correlation metadata and the app's defensive headers to an error."""
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = _request_id(request)
    return _apply_security_headers(
        JSONResponse(status_code=status_code, content=content, headers=response_headers)
    )


def _error_response(
    request: Request,
    *,
    status_code: int,
    content: dict,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Agrega correlación y cabeceras defensivas a una respuesta de error."""
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = _request_id(request)
    return _apply_security_headers(
        JSONResponse(status_code=status_code, content=content, headers=response_headers)
    )


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
