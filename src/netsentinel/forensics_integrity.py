"""Cálculo inicial de SHA-256 para adquisiciones o copias ya existentes.

Este componente solo abre un archivo en modo lectura. No escribe su contenido, pero
el sistema de archivos puede actualizar metadatos de acceso al leerlo. Usalo sobre una
copia de trabajo designada, no sobre el soporte original. No crea imágenes, no registra
casos y no demuestra que la adquisición original se haya realizado correctamente.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat


@dataclass(frozen=True)
class HashManifestEntry:
    """Resultado mínimo de una lectura de integridad reproducible."""

    algorithm: str
    sha256: str
    size_bytes: int
    verified_at_utc: str
    source_unchanged_during_read: bool


class ForensicIntegrityError(ValueError):
    """Error entendible y clasificable, sin volcar rutas ni datos de evidencia."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fingerprint(metadata: os.stat_result) -> tuple[int, ...]:
    """Metadatos comparables para detectar cambios durante la lectura.

    En Windows, st_dev/st_ino no siempre coinciden entre stat() y fstat() para la
    misma ruta abierta. Allí usamos tamaño y última modificación; en POSIX también
    comprobamos dispositivo, inode y ctime. No es una protección contra un atacante
    que pueda manipular metadatos deliberadamente.
    """
    if os.name == "nt":
        return (metadata.st_size, metadata.st_mtime_ns)
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def calculate_sha256(path: str | os.PathLike[str], *, chunk_size: int = 1024 * 1024) -> HashManifestEntry:
    """Calcula SHA-256 en bloques, sin escribir sobre el archivo elegido.

    Se rechazan enlaces simbólicos y objetos que no sean archivos regulares.
    Si el tamaño, la identidad o las fechas del archivo cambian durante la lectura,
    la operación falla en vez de devolver un hash que parezca estable. El control de
    metadatos es una defensa útil, no una prueba absoluta contra toda manipulación.
    """
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size < 1:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-001",
            "El tamaño de bloque debe ser un entero mayor que cero.",
        )
    try:
        raw_path = os.fspath(path)
    except (TypeError, ValueError, OSError) as exc:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-001",
            "Indicá una ruta válida para un archivo que ya exista.",
        ) from exc
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-001",
            "Indicá una ruta válida para un archivo que ya exista.",
        )

    source = Path(raw_path)
    try:
        before_path = source.lstat()
    except FileNotFoundError as exc:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-002",
            "No se encontró el archivo indicado. Comprobá la ubicación y volvé a intentarlo.",
        ) from exc
    except OSError as exc:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-003",
            "No se pudo consultar el archivo. Revisá la ruta y los permisos de lectura.",
        ) from exc

    if stat.S_ISLNK(before_path.st_mode):
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-004",
            "No se admiten enlaces simbólicos; elegí el archivo directamente.",
        )
    if not stat.S_ISREG(before_path.st_mode):
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-005",
            "La ruta no corresponde a un archivo regular.",
        )

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    digest = hashlib.sha256()
    bytes_read = 0

    try:
        descriptor = os.open(source, flags)
        opened_before = os.fstat(descriptor)
        if not stat.S_ISREG(opened_before.st_mode) or _fingerprint(opened_before) != _fingerprint(before_path):
            raise ForensicIntegrityError(
                "NS-FORENSIC-INT-006",
                "El archivo cambió antes de iniciar la lectura. No se generó un resultado.",
            )

        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = None
            while True:
                block = stream.read(chunk_size)
                if not block:
                    break
                digest.update(block)
                bytes_read += len(block)

            opened_after = os.fstat(stream.fileno())

        try:
            after_path = source.lstat()
        except OSError as exc:
            raise ForensicIntegrityError(
                "NS-FORENSIC-INT-007",
                "La ruta dejó de estar disponible durante la lectura. No se generó un resultado.",
            ) from exc

        if (
            stat.S_ISLNK(after_path.st_mode)
            or _fingerprint(opened_before) != _fingerprint(opened_after)
            or _fingerprint(opened_after) != _fingerprint(after_path)
            or bytes_read != opened_before.st_size
        ):
            raise ForensicIntegrityError(
                "NS-FORENSIC-INT-008",
                "El archivo cambió mientras se leía. No se generó un resultado de integridad.",
            )
    except ForensicIntegrityError:
        raise
    except PermissionError as exc:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-009",
            "No se pudo leer el archivo por falta de permisos. No se modificó su contenido.",
        ) from exc
    except OSError as exc:
        raise ForensicIntegrityError(
            "NS-FORENSIC-INT-010",
            "La lectura del archivo falló. Revisá el soporte y los permisos e intentá de nuevo.",
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    return HashManifestEntry(
        algorithm="SHA-256",
        sha256=digest.hexdigest(),
        size_bytes=bytes_read,
        verified_at_utc=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        source_unchanged_during_read=True,
    )
