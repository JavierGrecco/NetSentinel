"""Adaptador de red para comprobaciones directas y acotadas de monitorización.

El proceso llamador impone un deadline total para TCP/HTTP. Este módulo implementa
una comprobación puntual y normaliza el resultado sin incluir URLs ni salidas del SO.
"""
from __future__ import annotations

import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

from . import __version__


_LATENCY = re.compile(r"(?:time|tiempo)\s*[=<]\s*([\d.,]+)\s*ms", re.IGNORECASE)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """No sigue redirecciones: el monitor solo comprueba el objetivo configurado."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler())


def _probe_direct(kind: str, target: str, timeout_seconds: int) -> dict[str, Any]:
    """Ejecuta una comprobación con tiempo límite y devuelve un resultado sin secretos."""
    started = time.monotonic()
    try:
        if kind == "ping":
            if os.name == "nt":
                command = ["ping", "-n", "1", "-w", str(timeout_seconds * 1000), target]
            elif __import__("sys").platform == "darwin":
                command = ["ping", "-c", "1", target]
            else:
                command = ["ping", "-n", "-c", "1", "-W", str(timeout_seconds), target]
            try:
                completed = subprocess.run(
                    command, capture_output=True, text=True, timeout=timeout_seconds + 1,
                    check=False, shell=False,
                )
            except FileNotFoundError:
                return {"status": "down", "latency_ms": None, "detail": "El comando ping no está disponible en este sistema."}
            elapsed = round((time.monotonic() - started) * 1000, 2)
            output = f"{completed.stdout}\n{completed.stderr}"
            match = _LATENCY.search(output)
            latency = float(match.group(1).replace(",", ".")) if match else (elapsed if completed.returncode == 0 else None)
            if completed.returncode == 0:
                return {"status": "up", "latency_ms": latency, "detail": f"El host respondió al ping ({latency:.2f} ms)." if latency is not None else "El host respondió al ping."}
            return {"status": "down", "latency_ms": None, "detail": "No se recibió respuesta al ping dentro del tiempo configurado."}

        if kind == "tcp":
            if target.startswith("["):
                end = target.find("]")
                host, port = target[1:end], int(target[end + 2:])
            else:
                host, port_text = target.rsplit(":", 1)
                port = int(port_text)
            with socket.create_connection((host, port), timeout=timeout_seconds):
                pass
            elapsed = round((time.monotonic() - started) * 1000, 2)
            return {"status": "up", "latency_ms": elapsed, "detail": f"El puerto TCP {port} aceptó la conexión."}

        request = urllib.request.Request(
            target,
            headers={"User-Agent": f"NetSentinel/{__version__}", "Accept": "*/*"},
            method="GET",
        )
        try:
            response = _NO_REDIRECT_OPENER.open(request, timeout=timeout_seconds)
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            exc.close()
        else:
            with response:
                status_code = int(response.status)
        elapsed = round((time.monotonic() - started) * 1000, 2)
        good = 200 <= status_code < 400
        return {
            "status": "up" if good else "down",
            "latency_ms": elapsed,
            "detail": f"HTTP respondió con estado {status_code} en {elapsed:.2f} ms.",
        }
    except (OSError, TimeoutError, subprocess.TimeoutExpired, ValueError) as exc:
        elapsed = round((time.monotonic() - started) * 1000, 2)
        if isinstance(exc, subprocess.TimeoutExpired):
            detail = "La comprobación superó el tiempo límite configurado."
        elif isinstance(exc, TimeoutError) or isinstance(exc, socket.timeout):
            detail = "La conexión superó el tiempo límite configurado."
        else:
            # Don't include raw URLs, system output, exception reprs or possible secrets.
            detail = f"No se pudo completar la comprobación ({type(exc).__name__})."
        return {"status": "down", "latency_ms": None, "detail": detail, "elapsed_ms": elapsed}
