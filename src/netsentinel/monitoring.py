"""Comprobaciones de disponibilidad seguras y acotadas para objetivos configurados."""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from ipaddress import ip_address
from threading import Event, Thread
from typing import Any
from urllib.parse import urlsplit

from . import __version__, database

logger = logging.getLogger(__name__)

MIN_INTERVAL_SECONDS = 15
MAX_INTERVAL_SECONDS = 86_400
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 10
SUPPORTED_KINDS = {"ping", "tcp", "http"}
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_LATENCY = re.compile(r"(?:time|tiempo)\s*[=<]\s*([\d.,]+)\s*ms", re.IGNORECASE)

DEFAULT_MONITOR_HISTORY_DAYS = 90
MAX_MONITOR_HISTORY_DAYS = 3650
HISTORY_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60
# Give Python startup a small grace period, while keeping the complete network
# operation bounded even if the operating-system DNS resolver stalls.
_PROBE_PROCESS_STARTUP_GRACE_SECONDS = 1.0
_WEBHOOK_TOTAL_TIMEOUT_SECONDS = 5.0


def monitor_history_retention_days() -> int | None:
    """Return configured retention days; None explicitly disables automatic pruning."""
    raw = os.environ.get("NETSENTINEL_MONITOR_HISTORY_DAYS", str(DEFAULT_MONITOR_HISTORY_DAYS)).strip().lower()
    if not raw:
        return DEFAULT_MONITOR_HISTORY_DAYS
    if raw in {"0", "off", "disabled", "none", "never"}:
        return None
    try:
        days = int(raw)
    except ValueError:
        logger.warning(
            "NETSENTINEL_MONITOR_HISTORY_DAYS no es un entero válido; se conserva el historial sin limpieza automática."
        )
        return None
    if not 1 <= days <= MAX_MONITOR_HISTORY_DAYS:
        logger.warning(
            "NETSENTINEL_MONITOR_HISTORY_DAYS debe estar entre 1 y %s; se conserva el historial sin limpieza automática.",
            MAX_MONITOR_HISTORY_DAYS,
        )
        return None
    return days



def valid_host(host: str) -> bool:
    host = host.strip().rstrip(".")
    if not host or len(host) > 253 or any(ch.isspace() for ch in host):
        return False
    try:
        ip_address(host.split("%", 1)[0])
        return True
    except ValueError:
        pass
    return all(_HOST_LABEL.fullmatch(label) for label in host.split("."))


def validate_spec(kind: str, target: str, interval_seconds: int, timeout_seconds: int) -> tuple[str, str, int, int]:
    kind = kind.strip().lower()
    target = target.strip()
    if kind not in SUPPORTED_KINDS:
        raise ValueError("Tipo de comprobación no admitido.")
    if not target or len(target) > 500 or any(ord(ch) < 32 for ch in target):
        raise ValueError("El objetivo está vacío o tiene un formato inválido.")
    if not MIN_INTERVAL_SECONDS <= int(interval_seconds) <= MAX_INTERVAL_SECONDS:
        raise ValueError(f"El intervalo debe estar entre {MIN_INTERVAL_SECONDS} y {MAX_INTERVAL_SECONDS} segundos.")
    if not MIN_TIMEOUT_SECONDS <= int(timeout_seconds) <= MAX_TIMEOUT_SECONDS:
        raise ValueError(f"El tiempo límite debe estar entre {MIN_TIMEOUT_SECONDS} y {MAX_TIMEOUT_SECONDS} segundos.")

    if kind == "ping":
        if not valid_host(target) or target.startswith("-"):
            raise ValueError("Para ping usá una IP o un nombre de host válido, sin argumentos adicionales.")
    elif kind == "tcp":
        if target.startswith("["):
            closing = target.find("]")
            if closing < 0 or target[closing + 1:closing + 2] != ":":
                raise ValueError("Para IPv6 usá el formato [dirección]:puerto.")
            host, port_text = target[1:closing], target[closing + 2:]
        else:
            if target.count(":") != 1:
                raise ValueError("Para TCP usá host:puerto; las direcciones IPv6 deben ir entre corchetes.")
            host, port_text = target.rsplit(":", 1)
        if not valid_host(host) or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            raise ValueError("El objetivo TCP debe ser host:puerto con un puerto entre 1 y 65535.")
    else:
        parsed = urlsplit(target)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Para HTTP usá una URL http:// o https:// sin credenciales incrustadas.")
        if not valid_host(parsed.hostname):
            raise ValueError("El host de la URL no es válido.")
        if parsed.query or parsed.fragment:
            raise ValueError("Por seguridad, la URL de monitorización no debe incluir query strings ni fragmentos; no coloques tokens en la dirección.")
        try:
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError("El puerto HTTP no es válido.")
        except ValueError as exc:
            raise ValueError("El puerto HTTP no es válido.") from exc
    return kind, target, int(interval_seconds), int(timeout_seconds)


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



_PROBE_CHILD_SCRIPT = """
import json
import sys
from netsentinel.monitoring import _probe_direct

try:
    payload = json.load(sys.stdin)
    result = _probe_direct(payload["kind"], payload["target"], int(payload["timeout_seconds"]))
    print(json.dumps(result, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({
        "status": "down",
        "latency_ms": None,
        "detail": "No se pudo completar la comprobación aislada (" + type(exc).__name__ + ")."
    }, ensure_ascii=False))
"""


def probe(kind: str, target: str, timeout_seconds: int) -> dict[str, Any]:
    """Bound TCP/HTTP probes even when libc or the OS DNS resolver hangs."""
    if kind == "ping":
        # ping is already a separately terminated subprocess; keep its native
        # platform-specific timeout and avoid an unnecessary extra process.
        return _probe_direct(kind, target, timeout_seconds)

    started = time.monotonic()
    payload = json.dumps(
        {"kind": kind, "target": target, "timeout_seconds": int(timeout_seconds)},
        ensure_ascii=False,
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _PROBE_CHILD_SCRIPT],
            input=payload,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=float(timeout_seconds) + _PROBE_PROCESS_STARTUP_GRACE_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = round((time.monotonic() - started) * 1000, 2)
        return {
            "status": "down",
            "latency_ms": None,
            "detail": "La comprobación superó el límite total, incluida la resolución del nombre.",
            "elapsed_ms": elapsed,
        }
    except OSError as exc:
        elapsed = round((time.monotonic() - started) * 1000, 2)
        return {
            "status": "down",
            "latency_ms": None,
            "detail": f"No se pudo iniciar el proceso aislado ({type(exc).__name__}).",
            "elapsed_ms": elapsed,
        }

    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        result = None
    if (
        completed.returncode != 0
        or not isinstance(result, dict)
        or result.get("status") not in {"up", "down"}
        or not isinstance(result.get("detail"), str)
    ):
        elapsed = round((time.monotonic() - started) * 1000, 2)
        return {
            "status": "down",
            "latency_ms": None,
            "detail": "La comprobación aislada no devolvió un resultado válido.",
            "elapsed_ms": elapsed,
        }

    latency = result.get("latency_ms")
    if isinstance(latency, bool) or (latency is not None and not isinstance(latency, (int, float))):
        latency = None
    output = {
        "status": result["status"],
        "latency_ms": latency,
        "detail": result["detail"][:500],
    }
    elapsed_child = result.get("elapsed_ms")
    if isinstance(elapsed_child, (int, float)) and not isinstance(elapsed_child, bool):
        output["elapsed_ms"] = max(0.0, min(float(elapsed_child), 600_000.0))
    return output


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



_WEBHOOK_CHILD_SCRIPT = """
import json
import sys
from netsentinel.monitoring import _send_webhook_direct

try:
    transition = json.load(sys.stdin)
    success, detail = _send_webhook_direct(transition)
    print(json.dumps({"ok": bool(success), "detail": str(detail)[:160]}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({
        "ok": False,
        "detail": "Error de entrega: " + type(exc).__name__
    }, ensure_ascii=False))
"""


def send_webhook(transition: dict[str, Any]) -> tuple[bool, str]:
    """Deliver optional notifications in a child with a hard total deadline."""
    if not os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip():
        return False, "Webhook no configurado"

    try:
        completed = subprocess.run(
            [sys.executable, "-c", _WEBHOOK_CHILD_SCRIPT],
            input=json.dumps(transition, ensure_ascii=False),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=_WEBHOOK_TOTAL_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "Error de entrega: se superó el límite total de 5 segundos"
    except OSError as exc:
        return False, f"Error de entrega: proceso no disponible ({type(exc).__name__})"

    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        result = None
    if completed.returncode != 0 or not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        return False, "Error de entrega: el proceso no devolvió un resultado válido"
    detail = result.get("detail")
    if not isinstance(detail, str):
        return False, "Error de entrega: el resultado no contiene detalle"
    return result["ok"], detail[:160]


def check_once(monitor: dict[str, Any], *, path=None) -> dict[str, Any]:
    result = probe(monitor["kind"], monitor["target"], int(monitor["timeout_seconds"]))
    recorded = database.record_monitor_check(
        int(monitor["id"]), result["status"], result.get("latency_ms"), result["detail"], path=path
    )
    transition = recorded.get("transition")
    if transition:
        configured = bool(os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip())
        if configured:
            notify = send_webhook(transition)
            database.record_notification(
                monitor_id=int(monitor["id"]), incident_id=transition.get("incident_id"),
                event_type=str(transition["transition"]), success=notify[0], detail=notify[1], path=path,
            )
            recorded["notification"] = {"configured": True, "success": notify[0], "detail": notify[1]}
        else:
            recorded["notification"] = {"configured": False, "success": None, "detail": "Webhook desactivado"}
    return {**recorded, "probe": result}


class MonitorSupervisor:
    """Worker periódico de fondo; se detiene limpiamente al apagar FastAPI."""
    def __init__(self, poll_seconds: float = 2.0) -> None:
        self.poll_seconds = max(0.5, poll_seconds)
        self._stop = Event()
        self._thread: Thread | None = None
        self._last_history_cleanup_monotonic = 0.0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        # The worker's first pass performs retention cleanup; don't block app startup
        # while an old, high-volume history is pruned.
        self._thread = Thread(target=self._run, name="netsentinel-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=MAX_TIMEOUT_SECONDS + 3)
        self._thread = None

    def cleanup_history_if_due(self, *, force: bool = False, now: float | None = None) -> int:
        """Prune old detailed checks at most once a day, without failing app startup."""
        current = time.monotonic() if now is None else now
        if (
            not force
            and self._last_history_cleanup_monotonic > 0
            and current - self._last_history_cleanup_monotonic < HISTORY_CLEANUP_INTERVAL_SECONDS
        ):
            return 0

        retention_days = monitor_history_retention_days()
        if retention_days is None:
            self._last_history_cleanup_monotonic = current
            return 0

        try:
            removed = database.cleanup_monitor_history(retention_days)
        except Exception:
            # Retry after roughly an hour, avoiding tight-loop logging when SQLite is busy.
            self._last_history_cleanup_monotonic = current - (HISTORY_CLEANUP_INTERVAL_SECONDS - 60 * 60)
            logger.exception("No se pudo limpiar el historial detallado de monitorización.")
            return 0

        self._last_history_cleanup_monotonic = current
        if removed:
            logger.info("Se eliminaron %s comprobaciones de monitorización anteriores a %s días.", removed, retention_days)
        return removed

    def run_due_once(self) -> int:
        self.cleanup_history_if_due()
        now = datetime.now(timezone.utc)
        executed = 0
        for monitor in database.list_monitors():
            if not monitor["enabled"]:
                continue
            last_checked = monitor.get("last_checked_at")
            due = True
            if last_checked:
                try:
                    previous = datetime.fromisoformat(last_checked)
                    if previous.tzinfo is None:
                        previous = previous.replace(tzinfo=timezone.utc)
                    due = (now - previous).total_seconds() >= int(monitor["interval_seconds"])
                except (ValueError, TypeError):
                    due = True
            if due:
                check_once(monitor)
                executed += 1
        return executed

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_due_once()
            except Exception:
                # A single monitor or storage hiccup must not kill the supervisor.
                logger.exception("Fallo inesperado al ejecutar monitores programados")
            self._stop.wait(self.poll_seconds)
