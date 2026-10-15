"""Entrega opcional de notificaciones por webhook, sin bloquear el supervisor.

La URL se lee desde el entorno únicamente dentro del proceso de envío; los resultados
devueltos no incluyen el token ni la ruta secreta configurada.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any
from urllib.parse import urlsplit

from . import __version__
from .monitoring_probe import _NO_REDIRECT_OPENER


_WEBHOOK_TOTAL_TIMEOUT_SECONDS = 5.0


def _send_webhook_direct(transition: dict[str, Any]) -> tuple[bool, str]:
    """Envía solo transiciones de estado; URL secreta configurada por variable de entorno."""
    webhook_url = os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return False, "Webhook no configurado"
    parsed = urlsplit(webhook_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False, "La URL del webhook debe ser HTTPS y no contener credenciales incrustadas"
    message = str(transition.get("message", "NetSentinel detectó un cambio de estado."))[:1500]
    payload = {
        "content": message,
        "source": "NetSentinel",
        "event": transition.get("transition"),
        "monitor": transition.get("monitor_name"),
        "target": transition.get("target"),
        "timestamp": transition.get("at"),
    }
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": f"NetSentinel/{__version__}"},
        method="POST",
    )
    try:
        with _NO_REDIRECT_OPENER.open(request, timeout=4) as response:
            if 200 <= response.status < 300:
                return True, f"HTTP {response.status}"
            return False, f"HTTP {response.status}"
    except Exception as exc:  # webhook is optional; don't disrupt monitoring
        return False, f"Error de entrega: {type(exc).__name__}"
