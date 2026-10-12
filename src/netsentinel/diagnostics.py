"""Comprobaciones de conectividad explícitas y de bajo impacto."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
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


def _resolve_hostname(hostname: str, timeout: float = 3.0) -> tuple[list[str], str | None]:
    """Resolve a host in a killable child process with a strict timeout.

    A timeout in the calling thread does not stop the operating system resolver.
    The child process can be terminated when the deadline expires.
    """
    resolver_script = chr(10).join(
        [
            "import json, socket, sys",
            "try:",
            "    addresses = sorted({item[4][0] for item in socket.getaddrinfo(sys.argv[1], 443, type=socket.SOCK_STREAM)})",
            "    print(json.dumps(addresses))",
            "except OSError as exc:",
            "    print(json.dumps({'error': type(exc).__name__}))",
            "    sys.exit(1)",
        ]
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", resolver_script, hostname],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "timeout"
    except OSError:
        return [], "unavailable"

    try:
        payload = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, TypeError):
        return [], "error"
    if result.returncode != 0 or not isinstance(payload, list):
        return [], "error"
    if not all(isinstance(address, str) for address in payload):
        return [], "error"
    return sorted(set(payload)), None


def _ping_command(target: str) -> list[str]:
    """Construye el ping con flags y unidades apropiadas al sistema operativo."""
    system = platform.system()
    if system == "Windows":
        return ["ping", "-n", "1", "-w", "1200", target]
    if system == "Darwin":
        # En macOS, `-W` se expresa en milisegundos; en Linux son segundos.
        return ["ping", "-c", "1", "-W", "2000", target]
    return ["ping", "-c", "1", "-W", "2", target]


def build_assessment(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Resume los hallazgos y propone pasos prudentes sin afirmar causas no verificadas."""
    statuses = {str(check.get("name")): check.get("status") for check in checks}
    gateway = statuses.get("Puerta de enlace")
    router = statuses.get("Respuesta del router")
    dns = statuses.get("Resolución DNS")
    external = statuses.get("Conectividad IP externa")

    if dns == "timeout":
        title = "La consulta DNS tardó demasiado"
        if external == "ok":
            summary = (
                "La prueba IP externa respondió, pero la consulta DNS superó el límite de espera. "
                "Puede ser un resolvedor lento o un problema temporal; no confirma una avería permanente."
            )
            next_steps = [
                "Volvé a ejecutar el diagnóstico una vez para comprobar si fue algo transitorio.",
                "Probá abrir un sitio HTTPS desde el navegador.",
                "No cambies la configuración DNS hasta tener una segunda señal del problema.",
            ]
        else:
            summary = (
                "La consulta DNS superó el límite de espera y la prueba de ping externa tampoco respondió. "
                "Con estos datos no se puede determinar una causa única."
            )
            next_steps = [
                "Confirmá que Wi-Fi o Ethernet estén conectados y probá abrir un sitio HTTPS.",
                "Si el problema continúa, revisá la VPN o consultá al administrador de la red.",
                "Volvé a ejecutar el diagnóstico antes de modificar DNS o firewall.",
            ]
        status = "warning"
    elif dns == "ok" and external == "ok":
        if router == "warning":
            title = "La conectividad funciona; el router no respondió al ping"
            summary = (
                "DNS resolvió el dominio y la prueba IP externa respondió. "
                "El router puede bloquear ICMP; ese resultado, por sí solo, no indica una avería."
            )
            next_steps = [
                "No cambies la configuración de la red solo por este resultado.",
                "Si una aplicación concreta falla, comprobá ese servicio con una prueba HTTP o TCP.",
            ]
        elif gateway != "ok":
            title = "La conectividad externa funciona"
            summary = (
                "La resolución DNS y la prueba IP externa respondieron, aunque no se pudo "
                "identificar automáticamente la puerta de enlace."
            )
            next_steps = [
                "La detección de la puerta de enlace varía según el sistema operativo.",
                "Si las aplicaciones funcionan, no hace falta corregir la ruta por este dato aislado.",
            ]
        else:
            title = "Conectividad básica correcta"
            summary = "Se pudo resolver un dominio y la prueba de conectividad IP externa respondió."
            next_steps = [
                "Si una aplicación sigue sin funcionar, revisá ese servicio con un monitor HTTP o TCP."
            ]
        status = "ok"
    elif dns != "ok" and external == "ok":
        title = "Posible problema de DNS"
        summary = (
            "La prueba IP externa respondió, pero el sistema no pudo resolver example.com. "
            "La conectividad por IP existe; la resolución de nombres podría estar fallando."
        )
        next_steps = [
            "Revisá la configuración DNS de la computadora o del router.",
            "Si el problema persiste, consultá al administrador de la red antes de cambiar otros ajustes.",
        ]
        status = "warning"
    elif dns == "ok" and external != "ok":
        title = "DNS funciona, pero el ping externo no respondió"
        summary = (
            "La resolución de nombres funciona. La prueba de ping a 1.1.1.1 no respondió; "
            "algunas redes filtran ICMP, así que esto no demuestra por sí solo una caída de Internet."
        )
        next_steps = [
            "Probá abrir un sitio HTTPS desde el navegador.",
            "Si tampoco carga, revisá la conexión, la VPN y el firewall, o consultá al administrador de la red.",
        ]
        status = "warning"
    else:
        if router == "ok":
            title = "La red local responde, pero no se confirmó la salida a Internet"
            summary = (
                "El router respondió, pero fallaron la resolución DNS y el ping externo. "
                "Podría haber un problema de DNS o de conectividad de salida."
            )
        elif gateway != "ok":
            title = "No se pudo confirmar la conexión"
            summary = (
                "No se identificó la puerta de enlace y tampoco se confirmaron DNS ni conectividad IP. "
                "Un filtro de ICMP también puede afectar parte de estas pruebas."
            )
        else:
            title = "No se pudo confirmar la conectividad externa"
            summary = (
                "No respondieron DNS ni el ping externo. Puede haber una falla de red, "
                "aunque las políticas de DNS o ICMP también pueden influir."
            )
        next_steps = [
            "Confirmá que Wi-Fi o Ethernet estén conectados.",
            "Revisá si una VPN, un firewall o la configuración del router afectan la conexión.",
            "Probá abrir un sitio HTTPS; no cambies la configuración DNS solo por un resultado de ping.",
        ]
        status = "warning"

    return {"status": status, "title": title, "summary": summary, "next_steps": next_steps}


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

    addresses, dns_error = _resolve_hostname("example.com", timeout=3.0)
    if dns_error == "timeout":
        checks.append({
            "name": "Resolución DNS",
            "status": "timeout",
            "detail": "La consulta superó el límite de 3 segundos. La espera se detuvo para que el diagnóstico pueda continuar.",
        })
    elif dns_error:
        checks.append({
            "name": "Resolución DNS",
            "status": "warning",
            "detail": "El resolvedor no pudo completar la consulta de example.com. Puede ser un problema temporal o de configuración.",
        })
    else:
        checks.append({
            "name": "Resolución DNS",
            "status": "ok",
            "detail": f"example.com resolvió a {', '.join(addresses[:3])}.",
        })

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
        "assessment": build_assessment(checks),
        "checks": checks,
    }
