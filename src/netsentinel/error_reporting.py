"""Catálogo seguro y estable de errores operativos de NetSentinel.

Los detalles técnicos se usan únicamente para clasificar el fallo; nunca se
devuelven al cliente ni se copian sin filtrar a los registros.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import subprocess
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


@dataclass(frozen=True)
class ErrorDescription:
    """Contrato de error seguro para una respuesta y su registro local."""

    code: str
    category: str
    message: str
    next_action: str
    log_level: str
    log_reason: str


def describe_unhandled_exception(exc: Exception) -> ErrorDescription:
    """Mapea fallos inesperados a códigos, mensajes y acciones sin exponer detalles."""
    if isinstance(exc, sqlite3.OperationalError):
        # Inspect internally for classification only; do not return/log the raw text.
        reason = str(exc).casefold()
        if "locked" in reason or "busy" in reason:
            return ErrorDescription(
                "NS-DB-002", "database_busy",
                "La base de datos local está ocupada por otra operación.",
                "Esperá unos segundos y reintentá. Si continúa, cerrá otras instancias de NetSentinel.",
                "warning", "SQLite database busy or locked",
            )
        if "full" in reason or "disk is full" in reason:
            return ErrorDescription(
                "NS-DB-003", "database_storage_full",
                "No hay espacio suficiente para completar la operación en la base local.",
                "Liberá espacio en el disco y revisá que la carpeta de datos tenga espacio disponible antes de reintentar.",
                "error", "SQLite storage full",
            )
        if "disk i/o" in reason or "disk io" in reason:
            return ErrorDescription(
                "NS-DB-007", "database_io",
                "La base de datos local devolvió un error de lectura o escritura.",
                "No repitas una operación destructiva. Conservá una copia del archivo de datos y comprobá el estado del disco antes de volver a intentar.",
                "error", "SQLite disk I/O failure",
            )
        if "readonly" in reason or "read-only" in reason or "permission denied" in reason or "unable to open database file" in reason:
            return ErrorDescription(
                "NS-DB-004", "database_access",
                "NetSentinel no pudo abrir o escribir en la base de datos local.",
                "Comprobá los permisos de la carpeta de datos y que el archivo no esté en una ubicación de solo lectura.",
                "error", "SQLite database access denied or unavailable",
            )
        if "malformed" in reason or "not a database" in reason or "no such table" in reason or "no such column" in reason:
            return ErrorDescription(
                "NS-DB-005", "database_integrity_or_schema",
                "La base local no tiene la estructura esperada o no pudo leerse correctamente.",
                "No borres ni reemplaces el archivo de datos. Conservá una copia de seguridad y consultá el diagnóstico con el código indicado.",
                "error", "SQLite database integrity or schema issue",
            )

    if isinstance(exc, sqlite3.IntegrityError):
        return ErrorDescription(
            "NS-DB-006", "database_integrity",
            "La operación no pudo guardarse porque los datos no cumplen una regla de integridad.",
            "No des por guardado el cambio. Actualizá la vista y, si vuelve a ocurrir, informá el código de seguimiento.",
            "error", "SQLite integrity constraint failure",
        )
    if isinstance(exc, sqlite3.Error):
        return ErrorDescription(
            "NS-DB-001", "database",
            "NetSentinel no pudo completar una operación de lectura o escritura en la base local.",
            "Reintentá una vez. Si el problema persiste, revisá los permisos y conservá una copia de seguridad antes de reparar datos.",
            "error", "SQLite operation failure",
        )
    if isinstance(exc, subprocess.TimeoutExpired) or isinstance(exc, TimeoutError):
        return ErrorDescription(
            "NS-SYS-002", "operation_timeout",
            "Una operación del sistema superó el tiempo de espera permitido.",
            "Volvé a intentarlo. Si ocurre repetidamente, comprobá la carga del equipo y la conectividad.",
            "warning", "System operation timeout",
        )
    if isinstance(exc, PermissionError):
        return ErrorDescription(
            "NS-FS-001", "permission_denied",
            "El sistema operativo no permitió acceder a un archivo o recurso necesario.",
            "Comprobá los permisos de NetSentinel y de su carpeta de datos; no cambies permisos de todo el sistema.",
            "error", "Operating system permission denied",
        )
    if isinstance(exc, OSError):
        return ErrorDescription(
            "NS-SYS-001", "operating_system",
            "NetSentinel no pudo acceder a un recurso del sistema necesario para completar la operación.",
            "Comprobá el estado del recurso y los permisos. Si el error continúa, informá el código de seguimiento.",
            "error", "Operating system resource unavailable",
        )
    return ErrorDescription(
        "NS-500-001", "unexpected",
        "NetSentinel no pudo completar la operación por un error interno.",
        "No des por guardado un cambio que haya fallado. Reintentá una vez y comunicá el código de error y la referencia de seguimiento.",
        "error", "Unhandled application exception",
    )


def describe_http_error(status_code: int) -> tuple[str, str]:
    """Devuelve un código estable y una acción prudente para errores HTTP esperados."""
    details = {
        400: ("NS-HTTP-400", "Revisá la dirección o los datos de la solicitud e intentá de nuevo."),
        401: ("NS-HTTP-401", "Volvé a autenticarte si la función lo requiere."),
        403: ("NS-HTTP-403", "La operación fue bloqueada por una regla de seguridad. Confirmá que se inició desde el panel local."),
        404: ("NS-HTTP-404", "Actualizá la vista y comprobá que el recurso todavía exista."),
        409: ("NS-HTTP-409", "El estado actual impide la operación. Actualizá la vista y revisá los cambios recientes."),
        422: ("NS-HTTP-422", "Corregí los campos indicados y volvé a enviar la solicitud."),
        429: ("NS-HTTP-429", "Esperá antes de repetir la solicitud."),
        502: ("NS-HTTP-502", "La comprobación externa no pudo completarse. Revisá la red o el servicio de destino."),
        503: ("NS-HTTP-503", "El servicio todavía no está disponible. Esperá unos segundos y reintentá."),
    }
    if status_code in details:
        return details[status_code]
    if 500 <= status_code <= 599:
        return "NS-HTTP-5XX", "El servidor no pudo completar la solicitud. Comunicá la referencia de seguimiento."
    return f"NS-HTTP-{status_code}", "Revisá la solicitud y volvé a intentarlo."

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Mapping

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


def _rotate_error_log(path: Path) -> None:
    """Rotate the private, bounded error journal without reading prior records."""
    for index in range(_ERROR_LOG_BACKUPS, 0, -1):
        source = path if index == 1 else Path(f"{path}.{index - 1}")
        destination = Path(f"{path}.{index}")
        if source.exists() or source.is_symlink():
            os.replace(source, destination)


def record_error_event(event: Mapping[str, object]) -> bool:
    """Persist only allow-listed diagnostic metadata to a size-bounded local journal.

    Exception text, raw request bodies, query strings, hostnames, tokens and arbitrary
    caller-supplied fields are intentionally excluded. Failure is best-effort and
    reported to the caller so the UI never claims persistence that did not occur.
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
\n