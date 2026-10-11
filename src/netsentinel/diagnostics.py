"""Comprobaciones de conectividad explícitas y de bajo impacto."""

from __future__ import annotations

import platform
import re
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any


def _run(command: list[str], timeout: float = 3.0) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def find_default_gateway() -> str | None:
    system = platform.system()
    if system == "Darwin":
        result = _run(["route", "-n", "get", "default"])
        if result:
            match = re.search(r"(?m)^\s*gateway:\s*(\S+)", result.stdout)
            if match:
                return match.group(1)
    elif system == "Linux":
        result = _run(["ip", "route", "show", "default"])
        if result:
            match = re.search(r"(?m)^default via (\S+)", result.stdout)
            if match:
                return match.group(1)
    elif system == "Windows":
        result = _run(["route", "print", "-4"])
        if result:
            match = re.search(r"(?m)^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})", result.stdout)
            if match:
                return match.group(1)
    return None



def _ping_command(target: str) -> list[str]:
    """Construye el ping con flags y unidades apropiadas al sistema operativo."""
    system = platform.system()
    if system == "Windows":
        return ["ping", "-n", "1", "-w", "1200", target]
    if system == "Darwin":
        # En macOS, `-W` se expresa en milisegundos; en Linux son segundos.
        return ["ping", "-c", "1", "-W", "2000", target]
    return ["ping", "-c", "1", "-W", "2", target]


def run_diagnostics() -> dict[str, Any]:
    """Ejecuta comprobaciones solo después de una solicitud explícita del usuario.

    La resolución DNS usa example.com; la prueba de conectividad externa intenta
    contactar 1.1.1.1 mediante ping. Ambas implican tráfico de salida.
    """
    checks: list[dict[str, Any]] = []
    gateway = find_default_gateway()
    checks.append({
        "name": "Puerta de enlace",
        "status": "ok" if gateway else "warning",
        "detail": gateway or "No se pudo determinar automáticamente la puerta de enlace.",
    })

    if gateway:
        result = _run(_ping_command(gateway), timeout=3.5)
        reachable = bool(result and result.returncode == 0)
        checks.append({
            "name": "Respuesta del router",
            "status": "ok" if reachable else "warning",
            "detail": "La puerta de enlace respondió al ping." if reachable else "No hubo respuesta al ping; algunos routers bloquean ICMP.",
        })
    else:
        checks.append({"name": "Respuesta del router", "status": "skipped", "detail": "No se encontró la puerta de enlace para probarla."})

    try:
        addresses = sorted({result[4][0] for result in socket.getaddrinfo("example.com", 443, type=socket.SOCK_STREAM)})
        checks.append({"name": "Resolución DNS", "status": "ok", "detail": f"example.com resolvió a {', '.join(addresses[:3])}."})
    except socket.gaierror as exc:
        checks.append({"name": "Resolución DNS", "status": "warning", "detail": f"No se pudo resolver example.com: {exc}"})

    ping_target = "1.1.1.1"
    result = _run(_ping_command(ping_target), timeout=3.5)
    reachable = bool(result and result.returncode == 0)
    checks.append({
        "name": "Conectividad IP externa",
        "status": "ok" if reachable else "warning",
        "detail": "1.1.1.1 respondió al ping." if reachable else "No hubo respuesta de 1.1.1.1; ICMP puede estar filtrado por la red.",
    })

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notice": "Las pruebas DNS y ping generan tráfico de salida. Un ping bloqueado no demuestra por sí solo una caída de Internet.",
        "checks": checks,
    }
