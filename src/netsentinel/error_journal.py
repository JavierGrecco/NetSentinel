"""Diario local de errores operativos de NetSentinel.

Solo guarda metadatos aprobados, con límites de tamaño y rotación. No escribe
mensajes crudos de excepción ni cuerpos de solicitud, y falla de forma segura
si el registro no se puede guardar.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import threading

from .config import data_dir


_ERROR_LOG_NAME = "netsentinel-errors.jsonl"
_ERROR_LOG_MAX_BYTES = 512 * 1024
_ERROR_LOG_BACKUPS = 3
_ERROR_LOG_LOCK = threading.Lock()
_ERROR_LOG_FIELDS = {
    "error_code": 64,
    "request_id": 16,
    "category": 80,
    "severity": 16,
    "exception_type": 96,
    "method": 12,
    "path": 220,
    "reason": 120,
    "frames": 1200,
    "component": 40,
    "failure": 64,
    "platform": 40,
}

def _restrict_error_log_file(path: Path) -> None:
    """Restrict a regular log file without following symbolic links."""
    if os.name != "posix":
        return

    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None and path.is_symlink():
        return
    flags = os.O_RDONLY | (nofollow or 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return

    try:
        if stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.fchmod(descriptor, 0o600)
    except OSError:
        # Logging must never interrupt the application because of a chmod failure.
        pass
    finally:
        os.close(descriptor)


def _rotate_error_log(path: Path) -> None:
    """Rotate the private, bounded error journal without reading prior records."""
    for index in range(_ERROR_LOG_BACKUPS, 0, -1):
        source = path if index == 1 else Path(f"{path}.{index - 1}")
        destination = Path(f"{path}.{index}")
        if source.exists() or source.is_symlink():
            os.replace(source, destination)
            _restrict_error_log_file(destination)


def record_error_event(event: Mapping[str, object]) -> bool:
    """Persist only allow-listed diagnostic metadata to a size-bounded local journal.

    Only approved fields are copied. Raw request bodies and full exception messages are
    not written. Failure is best-effort and reported so the UI does not claim that a
    record was saved when persistence failed.
    """
    record: dict[str, str] = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    for field, max_length in _ERROR_LOG_FIELDS.items():
        value = event.get(field)
        if not isinstance(value, str):
            continue
        cleaned = "".join(
            char for char in value
            if ord(char) >= 32 and ord(char) != 127
        ).strip()
        if cleaned:
            record[field] = cleaned[:max_length]

    if not record.get("error_code"):
        return False

    try:
        serialized = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        encoded_size = len(serialized.encode("utf-8"))
        path = data_dir() / _ERROR_LOG_NAME
        with _ERROR_LOG_LOCK:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            # Never follow a pre-existing symlink at the error-log path.
            if path.is_symlink():
                return False
            if path.exists() and path.stat().st_size + encoded_size > _ERROR_LOG_MAX_BYTES:
                _rotate_error_log(path)

            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            flags |= getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags, 0o600)
            try:
                if os.name == "posix":
                    os.fchmod(descriptor, 0o600)
                with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                    descriptor = -1
                    stream.write(serialized)
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        return True
    except (OSError, ValueError, TypeError):
        return False
