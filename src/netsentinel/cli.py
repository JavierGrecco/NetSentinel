"""Punto de entrada de la aplicación."""

from __future__ import annotations

import argparse
import ipaddress
import webbrowser
from threading import Timer

import uvicorn

from . import __version__


def _is_loopback_host(host: str) -> bool:
    """Accept only loopback addresses; remote exposure is unsupported without auth."""
    normalized = host.strip().rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _parse_port(value: str) -> int:
    """Parse a valid TCP port for argparse."""
    try:
        port = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("el puerto debe ser un número entero") from None
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("el puerto debe estar entre 1 y 65535")
    return port


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia el panel local de NetSentinel.")
    parser.add_argument("--version", action="version", version=f"NetSentinel {__version__}")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Dirección loopback de escucha (por defecto: 127.0.0.1; no admite acceso remoto).",
    )
    parser.add_argument("--port", default=8765, type=_parse_port, help="Puerto HTTP (por defecto: 8765).")
    parser.add_argument("--no-browser", action="store_true", help="No abrir el navegador automáticamente.")
    args = parser.parse_args()

    if not _is_loopback_host(args.host):
        parser.error(
            "por seguridad, --host debe ser una dirección loopback (127.0.0.1, localhost o ::1). "
            "El acceso remoto no está disponible hasta implementar autenticación y control de acceso."
        )

    # URLs IPv6 requieren corchetes; Uvicorn debe recibir el host sin ellos.
    url_host = f"[{args.host}]" if ":" in args.host else args.host
    url = f"http://{url_host}:{args.port}"
    print(f"NetSentinel iniciará en {url}")
    print("Al iniciar no se sondea la red. El descubrimiento de la red local solo empieza cuando lo solicitás desde el panel.")
    if not args.no_browser:
        Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("netsentinel.main:app", host=args.host, port=args.port, reload=False, log_level="info")
