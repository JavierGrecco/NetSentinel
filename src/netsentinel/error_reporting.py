"""Catálogo de errores operativos con mensajes seguros y códigos estables.

Este módulo clasifica fallos. La escritura del diario local se mantiene en
error_journal.py; record_error_event sigue disponible aquí por compatibilidad.
"""
from __future__ import annotations

from dataclasses import dataclass
import sqlite3
import subprocess

from .error_journal import record_error_event


@dataclass(frozen=True)
class ErrorDescription:
    """Contrato de error seguro para una respuesta y su registro local."""

    code: str
    category: str
    message: str
    next_action: str
    log_level: str
    log_reason: str


def _sqlite_failure_reason(exc: sqlite3.Error) -> str:
    """Return a safe internal hint using native SQLite codes when available.

    Python 3.11+ exposes sqlite_errorcode on errors raised by SQLite. Mask
    extended result codes to their primary code; on older runtimes, retain the
    previous message-based fallback for OperationalError. Raw text is never
    returned to a response or persisted in the error catalog.
    """
    raw_code = getattr(exc, "sqlite_errorcode", None)
    if type(raw_code) is int:
        primary_code = raw_code & 0xFF
        if primary_code in (
            getattr(sqlite3, "SQLITE_BUSY", 5),
            getattr(sqlite3, "SQLITE_LOCKED", 6),
        ):
            return "database is locked"
        if primary_code == getattr(sqlite3, "SQLITE_FULL", 13):
            return "database or disk is full"
        if primary_code == getattr(sqlite3, "SQLITE_IOERR", 10):
            return "disk i/o error"
        if primary_code in (
            getattr(sqlite3, "SQLITE_READONLY", 8),
            getattr(sqlite3, "SQLITE_CANTOPEN", 14),
        ):
            return "readonly database"
        if primary_code in (
            getattr(sqlite3, "SQLITE_CORRUPT", 11),
            getattr(sqlite3, "SQLITE_NOTADB", 26),
            getattr(sqlite3, "SQLITE_SCHEMA", 17),
        ):
            return "database disk image is malformed"

    if type(raw_code) is int:
        # If SQLite did provide a native code, an unrecognized code must not be
        # reclassified from its message. Message matching is only a fallback on
        # runtimes where the native code is unavailable.
        return ""

    if isinstance(exc, sqlite3.OperationalError):
        return str(exc).casefold()
    return ""


def describe_unhandled_exception(exc: Exception) -> ErrorDescription:
    """Mapea fallos inesperados a códigos, mensajes y acciones sin exponer detalles."""
    if isinstance(exc, sqlite3.IntegrityError):
        return ErrorDescription(
            "NS-DB-006", "database_integrity",
            "La operación no pudo guardarse porque los datos no cumplen una regla de integridad.",
            "No des por guardado el cambio. Actualizá la vista y, si vuelve a ocurrir, informá el código de seguimiento.",
            "error", "SQLite integrity constraint failure",
        )

    if isinstance(exc, sqlite3.Error):
        reason = _sqlite_failure_reason(exc)
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
