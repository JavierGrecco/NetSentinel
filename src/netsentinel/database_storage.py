"""Conexiones, permisos del archivo y esquema SQLite de NetSentinel.

Este módulo es infraestructura compartida: no implementa consultas propias del
inventario ni de la monitorización. Las migraciones se mantienen aquí para que
cada actualización del esquema continúe siendo atómica y compatible con datos viejos.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from .config import database_path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _elapsed_seconds(start: str | None, end: str | None = None) -> int | None:
    """Calcula segundos entre marcas ISO; si falta el final usa el instante actual."""
    if not start:
        return None
    try:
        start_at = datetime.fromisoformat(start)
        end_at = datetime.fromisoformat(end) if end else datetime.now(timezone.utc)
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=timezone.utc)
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        return max(0, int((end_at - start_at).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return None


def _ensure_private_directory(directory: Path, *, enforce_existing_final: bool = False) -> None:
    """Create missing paths privately; optionally harden a known app-owned final directory."""
    # NETSENTINEL_DATA_DIR may point to a shared/system directory. Change modes
    # only on components created here, never on a pre-existing parent such as /tmp.
    if os.name != "posix":
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        return

    missing: list[Path] = []
    current = directory
    while not current.exists():
        missing.append(current)
        parent = current.parent
        if parent == current:
            break
        current = parent

    for candidate in reversed(missing):
        try:
            candidate.mkdir(mode=0o700)
        except FileExistsError:
            # A concurrent process may have created it. Don't chmod something
            # that this process did not create.
            if not candidate.is_dir():
                raise NotADirectoryError(f"El directorio de datos no es un directorio: {candidate}")
        else:
            try:
                os.chmod(candidate, 0o700)
            except OSError:
                # mkdir(mode=0o700) remains restrictive under a normal umask.
                pass

    if not directory.is_dir():
        raise NotADirectoryError(f"El directorio de datos no es un directorio: {directory}")

    # The default ~/.netsentinel directory is application-owned by convention.
    # It is safe to harden that known location even when it already exists;
    # custom NETSENTINEL_DATA_DIR paths are not assumed to be dedicated.
    if enforce_existing_final and not directory.is_symlink():
        try:
            os.chmod(directory, 0o700)
        except OSError:
            pass


def _harden_database_file(db_path: Path) -> None:
    """Restrict a regular SQLite file without changing a symlink target's mode."""
    if os.name != "posix":
        return

    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        # On POSIX systems without O_NOFOLLOW, prefer preserving a symlink target
        # to following it with chmod. Most supported macOS/Linux systems have it.
        if db_path.is_symlink():
            return
        try:
            os.chmod(db_path, 0o600)
        except OSError:
            pass
        return

    try:
        # Operate on an opened descriptor instead of chmod(path): O_NOFOLLOW
        # makes the final path component fail closed if it is a symlink.
        descriptor = os.open(db_path, os.O_RDONLY | nofollow)
    except OSError:
        # SQLite may intentionally use a symlink here. Do not silently change
        # permissions of its target; the operator must protect that target.
        return

    try:
        os.fchmod(descriptor, 0o600)
    except OSError:
        pass
    finally:
        os.close(descriptor)


@contextmanager
def connect(path: Path | None = None, *, default_path_provider: Callable[[], Path] | None = None) -> Iterator[sqlite3.Connection]:
    """Abre una conexión transaccional y asegura que se cierre al terminar."""
    db_path = path or (default_path_provider or database_path)()
    use_default_data_directory = path is None and not os.environ.get("NETSENTINEL_DATA_DIR")
    _ensure_private_directory(db_path.parent, enforce_existing_final=use_default_data_directory)
    connection = sqlite3.connect(db_path, timeout=10)
    _harden_database_file(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()
