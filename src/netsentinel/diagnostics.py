"""Comprobaciones de conectividad explícitas y de bajo impacto."""

from __future__ import annotations

import json
import logging
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

from .error_reporting import record_error_event


logger = logging.getLogger(__name__)


def _run_diagnostic(
    command: list[str], timeout: float = 3.0
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    """Run a local probe and preserve its failure class for user-facing diagnosis."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, errors="replace",
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except FileNotFoundError:
        return None, "command_unavailable"
    except PermissionError:
        return None, "permission_denied"
    except OSError:
        return None, "system_error"
    return (result, None) if result.returncode == 0 else (result, "nonzero_exit")


def _run(command: list[str], timeout: float = 3.0) -> subprocess.CompletedProcess[str] | None:
    """Compatibility wrapper for callers that only need the command result."""
    result, _ = _run_diagnostic(command, timeout=timeout)
    return result


def _find_default_gateway_result() -> tuple[str | None, str | None]:
    """Return gateway plus a stable local failure class without command-output leaks."""
    system = platform.system()
    if system == "Darwin":
        command, pattern = ["route", "-n", "get", "default"], r"(?m)^\s*gateway:\s*(\S+)"
    elif system == "Linux":
        command, pattern = ["ip", "route", "show", "default"], r"(?m)^default via (\S+)"
    elif system == "Windows":
        command = ["route", "print", "-4"]
        pattern = r"(?m)^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d{1,3}(?:\.\d{1,3}){3})"
    else:
        return None, "unsupported_platform"

    result, failure = _run_diagnostic(command, timeout=3.0)
    if failure == "nonzero_exit":
        return None, "route_command_failed"
    if failure:
        return None, failure
    if result is None:
        return None, "system_error"
    match = re.search(pattern, result.stdout)
    return (match.group(1), None) if match else (None, "not_detected")


def find_default_gateway() -> str | None:
    """Return the default gateway when the current OS route command can identify it."""
    gateway, _ = _find_default_gateway_result()
    return gateway



def _resolve_hostname(hostname: str, timeout: float = 3.0) -> tuple[list[str], str | None]:
    """Resolve a host in a killable child process and classify failures safely."""
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
    command = [sys.executable, "-c", resolver_script, hostname]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, errors="replace",
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return [], "timeout"
    except FileNotFoundError:
        return [], "command_unavailable"
    except PermissionError:
        return [], "permission_denied"
    except OSError:
        return [], "system_error"

    try:
        payload = json.loads(result.stdout.strip())
    except (json.JSONDecodeError, TypeError):
        return [], "invalid_response"
    if result.returncode != 0:
        if isinstance(payload, dict) and payload.get("error") == "gaierror":
            return [], "name_resolution_failed"
        return [], "resolver_failed"
    if not isinstance(payload, list) or not all(isinstance(address, str) for address in payload):
        return [], "invalid_response"
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


_DIAGNOSTIC_FAILURE_SUFFIXES = {
    "command_unavailable": "001",
    "permission_denied": "002",
    "timeout": "003",
    "system_error": "004",
    "nonzero_exit": "005",
    "not_detected": "006",
    "name_resolution_failed": "007",
    "invalid_response": "008",
    "resolver_failed": "009",
    "unsupported_platform": "010",
    "route_command_failed": "011",
}


def _failure_check(
    name: str, component: str, failure: str, detail: str, *,
    status: str = "warning", request_id: str | None = None,
) -> dict[str, Any]:
    """Build a diagnostic result with its root-cause class and logging policy."""
    suffix = _DIAGNOSTIC_FAILURE_SUFFIXES.get(failure, "999")
    code = f"NS-DIAG-{component}-{suffix}"
    should_log = failure in {
        "command_unavailable", "permission_denied", "system_error",
        "invalid_response", "resolver_failed", "route_command_failed",
    } or (failure == "timeout" and component in {"ROUTE", "ROUTER", "EXT"})
    logged = False
    if should_log:
        logged = record_error_event({
            "error_code": code,
            "request_id": request_id or "",
            "category": "diagnostic",
            "severity": "warning",
            "reason": "Diagnostic command execution failure",
            "component": component,
            "failure": failure,
            "platform": platform.system(),
        })
        logger.warning(
            "Diagnostic operational failure code=%s request_id=%s component=%s failure=%s platform=%s persisted=%s",
            code, request_id or "-", component, failure, platform.system(), logged,
        )
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "error_code": code,
        "should_log": should_log,
        "logged": logged,
    }


def _command_failure_detail(failure: str, operation: str) -> str:
    """Translate operating-system command failures without exposing stdout/stderr."""
    if failure == "command_unavailable":
        return f"No se encontró el comando que NetSentinel necesita para {operation}."
    if failure == "permission_denied":
        return f"El sistema operativo no permitió ejecutar la comprobación para {operation}."
    if failure == "timeout":
        return f"La comprobación para {operation} superó el tiempo de espera y se detuvo."
    if failure == "system_error":
        return f"No se pudo ejecutar la comprobación para {operation} por un error del sistema."
    if failure == "route_command_failed":
        return "El comando de rutas no pudo consultar la ruta predeterminada."
    if failure == "unsupported_platform":
        return "La detección automática de puerta de enlace no está implementada para este sistema operativo."
    if failure == "not_detected":
        return "El comando terminó, pero no se reconoció una puerta de enlace en su salida."
    if failure == "name_resolution_failed":
        return "El resolvedor del sistema no pudo traducir example.com a una dirección."
    if failure == "invalid_response":
        return "La comprobación local devolvió una respuesta que NetSentinel no pudo interpretar."
    if failure == "resolver_failed":
        return "El proceso aislado de DNS falló y no pudo completar la consulta."
    return f"La comprobación no pudo completar la operación para {operation}."


def run_diagnostics(request_id: str | None = None) -> dict[str, Any]:
    """Run explicitly requested, bounded probes and classify each failed check."""
    checks: list[dict[str, Any]] = []
    gateway, gateway_error = _find_default_gateway_result()
    if gateway:
        checks.append({
            "name": "Puerta de enlace",
            "status": "ok",
            "detail": gateway,
        })
    else:
        failure = gateway_error or "not_detected"
        checks.append(_failure_check(
            "Puerta de enlace", "ROUTE", failure,
            _command_failure_detail(failure, "detectar la puerta de enlace"),
            request_id=request_id,
            status="error" if failure in {
                "command_unavailable", "permission_denied", "system_error",
                "invalid_response", "route_command_failed",
            } else "warning",
        ))

    if gateway:
        result, failure = _run_diagnostic(_ping_command(gateway), timeout=3.5)
        if failure is None and result is not None:
            checks.append({
                "name": "Respuesta del router",
                "status": "ok",
                "detail": "La puerta de enlace respondió al ping.",
            })
        elif failure == "nonzero_exit":
            checks.append(_failure_check(
                "Respuesta del router", "ROUTER", failure,
                "No hubo respuesta al ping; algunos routers bloquean ICMP, así que esto no confirma una avería.",
                request_id=request_id,
            ))
        else:
            failure = failure or "system_error"
            checks.append(_failure_check(
                "Respuesta del router", "ROUTER", failure,
                _command_failure_detail(failure, "probar la puerta de enlace"),
                request_id=request_id,
                status="timeout" if failure == "timeout" else "error",
            ))
    else:
        checks.append({
            "name": "Respuesta del router",
            "status": "skipped",
            "detail": "No se pudo probar el router porque no se identificó la puerta de enlace.",
        })

    addresses, dns_error = _resolve_hostname("example.com", timeout=3.0)
    if dns_error is None:
        checks.append({
            "name": "Resolución DNS",
            "status": "ok",
            "detail": f"example.com resolvió a {', '.join(addresses[:3])}.",
        })
    else:
        if dns_error == "timeout":
            detail = "La consulta DNS superó el límite de 3 segundos; se detuvo para que el diagnóstico pudiera continuar."
            status = "timeout"
        elif dns_error == "name_resolution_failed":
            detail = _command_failure_detail(dns_error, "resolver example.com")
            status = "warning"
        else:
            detail = _command_failure_detail(dns_error, "resolver example.com")
            status = "error"
        checks.append(_failure_check("Resolución DNS", "DNS", dns_error, detail, status=status, request_id=request_id))

    result, failure = _run_diagnostic(_ping_command("1.1.1.1"), timeout=3.5)
    if failure is None and result is not None:
        checks.append({
            "name": "Conectividad IP externa",
            "status": "ok",
            "detail": "1.1.1.1 respondió al ping.",
        })
    elif failure == "nonzero_exit":
        checks.append(_failure_check(
            "Conectividad IP externa", "EXT", failure,
            "No hubo respuesta de 1.1.1.1; ICMP puede estar filtrado por la red. Esto no demuestra por sí solo una caída de Internet.",
            request_id=request_id,
        ))
    else:
        failure = failure or "system_error"
        checks.append(_failure_check(
            "Conectividad IP externa", "EXT", failure,
            _command_failure_detail(failure, "probar conectividad IP externa"),
            request_id=request_id,
            status="timeout" if failure == "timeout" else "error",
        ))

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request_id": request_id,
        "notice": "Las pruebas DNS y ping generan tráfico de salida. Una falta de respuesta puede ser de red/ICMP; fallos de ejecución local se registran con su código.",
        "assessment": build_assessment(checks),
        "checks": checks,
    }
