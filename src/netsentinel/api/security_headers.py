"""Cabeceras HTTP defensivas, CSP y respuestas de error correlacionadas.

Este módulo se ocupa de cómo se protegen las respuestas que genera la aplicación.
El middleware y las reglas de host/origen permanecen en security.py.
"""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, Response


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
    "/world-map": _STATIC_DIR / "geolocation.html",
}
_INLINE_SCRIPT_PATTERN = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script\b[^>]*>", re.IGNORECASE | re.DOTALL)


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
    """Agrega correlación y cabeceras defensivas a una respuesta de error."""
    response_headers = dict(headers or {})
    response_headers["X-Request-ID"] = _request_id(request)
    return _apply_security_headers(
        JSONResponse(status_code=status_code, content=content, headers=response_headers)
    )
