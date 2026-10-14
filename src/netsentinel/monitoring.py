"""Comprobaciones de disponibilidad seguras y acotadas para objetivos configurados."""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from threading import Event, Thread, current_thread
from typing import Any

from . import database

logger = logging.getLogger(__name__)

from .monitoring_validation import (
    MAX_INTERVAL_SECONDS,
    MAX_TIMEOUT_SECONDS,
    MIN_INTERVAL_SECONDS,
    MIN_TIMEOUT_SECONDS,
    SUPPORTED_KINDS,
    valid_host,
    validate_spec,
)
from .monitoring_probe import _NoRedirectHandler, _NO_REDIRECT_OPENER, _probe_direct
from .monitoring_notifications import _WEBHOOK_TOTAL_TIMEOUT_SECONDS, _send_webhook_direct

DEFAULT_MONITOR_HISTORY_DAYS = 90
MAX_MONITOR_HISTORY_DAYS = 3650
HISTORY_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60
# Give Python startup a small grace period, while keeping the complete network
# operation bounded even if the operating-system DNS resolver stalls.
_PROBE_PROCESS_STARTUP_GRACE_SECONDS = 1.0
# One in-flight check can spend timeout + startup grace in its probe and up to
# five seconds delivering a transition webhook. Allow a little scheduling/DB
# overhead, but never wait for a whole queue of monitors during shutdown.
_SUPERVISOR_STOP_TIMEOUT_SECONDS = (
    MAX_TIMEOUT_SECONDS
    + _PROBE_PROCESS_STARTUP_GRACE_SECONDS
    + _WEBHOOK_TOTAL_TIMEOUT_SECONDS
    + 2.0
)


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



















_PROBE_CHILD_SCRIPT = """
import json
import sys
from netsentinel.monitoring_probe import _probe_direct

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








_WEBHOOK_CHILD_SCRIPT = """
import json
import sys
from netsentinel.monitoring_notifications import _send_webhook_direct

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
        """Request a cooperative stop and retain any worker that missed its deadline."""
        self._stop.set()
        thread = self._thread
        if thread is None:
            return

        if thread.is_alive() and thread is not current_thread():
            thread.join(timeout=_SUPERVISOR_STOP_TIMEOUT_SECONDS)

        if thread.is_alive():
            # Keep the reference. Dropping it would let a later start() launch a
            # second worker while the original one can still write to SQLite.
            logger.error(
                "El supervisor de monitorización no terminó dentro de %.1f segundos; "
                "se conserva su referencia para impedir un segundo worker.",
                _SUPERVISOR_STOP_TIMEOUT_SECONDS,
            )
            return

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
        if self._stop.is_set():
            return 0

        now = datetime.now(timezone.utc)
        executed = 0
        for monitor in database.list_monitors():
            # Shutdown should finish the current bounded check, not drain every
            # due monitor in sequence after the application asked us to stop.
            if self._stop.is_set():
                break
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
                if self._stop.is_set():
                    break
                try:
                    check_once(monitor)
                except Exception:
                    # A storage error or unexpected failure for one monitor must
                    # not starve every later monitor on each supervisor cycle.
                    logger.exception(
                        "No se pudo completar la comprobación programada del monitor id=%s; "
                        "se continuará con los siguientes.",
                        monitor.get("id"),
                    )
                    continue
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
