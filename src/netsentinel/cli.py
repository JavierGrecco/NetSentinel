"""Punto de entrada de la aplicación."""

from __future__ import annotations

import argparse
import webbrowser
from threading import Timer

import uvicorn

from . import __version__


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicia el panel local de NetSentinel.")
    parser.add_argument("--version", action="version", version=f"NetSentinel {__version__}")
    parser.add_argument("--host", default="127.0.0.1", help="Dirección de escucha (por defecto solo local).")
    parser.add_argument("--port", default=8765, type=int, help="Puerto HTTP (por defecto: 8765).")
    parser.add_argument("--no-browser", action="store_true", help="No abrir el navegador automáticamente.")
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("ADVERTENCIA: el panel puede quedar expuesto a otros equipos. No lo expongas sin autenticación y configuración adicional.")

    url = f"http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}"
    print(f"NetSentinel iniciará en {url}")
    print("Al iniciar no se sondea la red. El descubrimiento de la red local solo empieza cuando lo solicitás desde el panel.")
    if not args.no_browser:
        Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("netsentinel.main:app", host=args.host, port=args.port, reload=False, log_level="info")
