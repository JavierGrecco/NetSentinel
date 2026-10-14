"""Consultas y borrado de actividad con alcance limitado.

Solo se aceptan filtros conocidos. El borrado vuelve a contar dentro de una
transacción de escritura antes de comprobar la confirmación del usuario.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from . import database
from .activity_repository_support import _require_device


_ALLOWED_ACTIVITY_SCOPE_CLAUSES = frozenset({
    "device_id = ?",
    "event_type = ?",
    "source = ?",
    "observed_at >= ?",
    "observed_at < ?",
})


def _require_bounded_scope(where_sql: str) -> None:
    """Limita el SQL de alcance a predicados generados por los filtros permitidos."""
    if (
        not isinstance(where_sql, str)
        or not where_sql.startswith(" WHERE ")
    ):
        raise ValueError("El repositorio requiere un alcance explícito de actividad.")
    clauses = where_sql[7:].strip().split(" AND ")
    if (
        not clauses
        or any(clause not in _ALLOWED_ACTIVITY_SCOPE_CLAUSES for clause in clauses)
        or len(set(clauses)) != len(clauses)
    ):
        raise ValueError("El repositorio requiere un alcance explícito de actividad.")


def count_activity_scope(
    where_sql: str,
    params: tuple[Any, ...],
    *,
    device_id: int | None = None,
) -> int:
    """Cuenta eventos de una selección ya validada por la capa de actividad.

    `where_sql` solo puede construirse desde los filtros permitidos por
    activity_tracking; los valores siempre viajan como parámetros SQL.
    """
    _require_bounded_scope(where_sql)
    with database.connect() as db:
        _require_device(db, device_id)
        row = db.execute(
            "SELECT COUNT(*) FROM activity_events" + where_sql, params
        ).fetchone()
        return int(row[0])


def delete_activity_scope(
    where_sql: str,
    params: tuple[Any, ...],
    *,
    device_id: int | None,
    confirmation: str,
) -> int:
    """Borra una selección confirmada dentro de una transacción de escritura.

    El bloqueo se toma antes de volver a contar: otra escritura no puede cambiar
    el número entre la verificación de la confirmación y el DELETE.
    """
    _require_bounded_scope(where_sql)
    if not isinstance(confirmation, str) or len(confirmation) > 40:
        raise PermissionError("La frase de confirmación no es válida.")

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        _require_device(db, device_id)
        row = db.execute(
            "SELECT COUNT(*) FROM activity_events" + where_sql, params
        ).fetchone()
        count = int(row[0])
        expected = f"BORRAR {count}"
        if confirmation != expected:
            raise PermissionError(
                f"No se borró nada: la selección contiene {count} evento(s). "
                f"Escribí exactamente «{expected}» para confirmar."
            )
        cursor = db.execute("DELETE FROM activity_events" + where_sql, params)
        return int(cursor.rowcount)
