"""Consultas y operaciones SQLite propias del dominio de actividad.

El módulo recibe conexiones existentes cuando debe compartir una transacción y abre
su propia conexión solo para operaciones completas, como actualizar la retención.
No importa FastAPI ni contiene contratos HTTP.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

from . import database

DEFAULT_RETENTION_DAYS = 7
MAX_RETENTION_DAYS = 90


def _utc_iso(value: datetime) -> str:
    """Serializa una fecha en UTC con la precisión usada por la base existente."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def get_retention_days(db: sqlite3.Connection) -> int:
    """Lee la política actual, manteniendo el valor histórico por defecto."""
    row = db.execute(
        "SELECT retention_days FROM activity_settings WHERE id = 1"
    ).fetchone()
    return int(row["retention_days"]) if row else DEFAULT_RETENTION_DAYS


def cleanup(db: sqlite3.Connection, *, now: datetime) -> int:
    """Aplica retención y vence sesiones sin cambiar el esquema ni sus datos válidos."""
    now_utc = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    now_text = _utc_iso(now_utc)
    retention_cutoff = _utc_iso(
        now_utc - timedelta(days=get_retention_days(db))
    )
    stale_session_cutoff = _utc_iso(now_utc - timedelta(days=MAX_RETENTION_DAYS))

    deleted_events = db.execute(
        "DELETE FROM activity_events WHERE observed_at < ?",
        (retention_cutoff,),
    )
    db.execute(
        "UPDATE activity_sessions SET status = 'expired' "
        "WHERE status = 'active' AND ends_at <= ?",
        (now_text,),
    )
    db.execute(
        "DELETE FROM activity_sessions WHERE status != 'active' AND ends_at < ?",
        (stale_session_cutoff,),
    )
    return int(deleted_events.rowcount)


def update_retention(retention_days: int, *, now: datetime) -> dict[str, int]:
    """Actualiza el ajuste y aplica la nueva retención dentro de una transacción."""
    days = int(retention_days)
    if not 1 <= days <= MAX_RETENTION_DAYS:
        raise ValueError("La retención debe ser de 1 a 90 días.")

    with database.connect() as db:
        # Restore the singleton row if an older or repaired database lacks it.
        # Otherwise, UPDATE would silently keep the default while reporting success.
        db.execute(
            """INSERT INTO activity_settings (id, retention_days) VALUES (1, ?)
               ON CONFLICT(id) DO UPDATE SET retention_days = excluded.retention_days""",
            (days,),
        )
        deleted_events = cleanup(db, now=now)
        effective_days = get_retention_days(db)

    return {
        "retention_days": effective_days,
        "deleted_events": deleted_events,
    }

def start_session(
    db: sqlite3.Connection,
    *,
    device_id: int,
    source_mode: str,
    started_at: str,
    ends_at: str,
    token_hash: str,
) -> dict[str, Any]:
    """Reemplaza sesiones activas del dispositivo y crea la nueva sesión."""
    device = db.execute(
        "SELECT id FROM devices WHERE id = ?", (device_id,)
    ).fetchone()
    if device is None:
        raise LookupError("No se encontró el dispositivo.")

    db.execute(
        "UPDATE activity_sessions SET status = 'stopped', stopped_at = ?, ends_at = ? "
        "WHERE device_id = ? AND status = 'active'",
        (started_at, started_at, device_id),
    )
    cursor = db.execute(
        """INSERT INTO activity_sessions
           (device_id, source_mode, started_at, ends_at, status, collector_token_hash)
           VALUES (?, ?, ?, ?, 'active', ?)""",
        (device_id, source_mode, started_at, ends_at, token_hash),
    )
    row = db.execute(
        """SELECT s.id, s.device_id, s.source_mode, s.started_at, s.ends_at, s.stopped_at, s.status,
                  d.display_name, d.ip_address, d.mac_address
           FROM activity_sessions s JOIN devices d ON d.id=s.device_id WHERE s.id=?""",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:
        raise RuntimeError("No se pudo recuperar la sesión recién creada.")
    return dict(row)


def get_session_for_device(
    db: sqlite3.Connection, session_id: int, device_id: int
) -> dict[str, Any] | None:
    """Obtiene una sesión con alcance de dispositivo para validar la ingesta."""
    row = db.execute(
        "SELECT * FROM activity_sessions WHERE id = ? AND device_id = ?",
        (session_id, device_id),
    ).fetchone()
    return dict(row) if row is not None else None


def stop_session(
    db: sqlite3.Connection, session_id: int, *, now: str
) -> dict[str, Any] | None:
    """Detiene una sesión activa; repetir la operación conserva el primer cierre."""
    current = db.execute(
        "SELECT id, status FROM activity_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if current is None:
        return None
    if current["status"] == "active":
        db.execute(
            "UPDATE activity_sessions SET status='stopped', stopped_at=?, ends_at=? WHERE id=?",
            (now, now, session_id),
        )
    row = db.execute(
        """SELECT id, device_id, source_mode, started_at, ends_at, stopped_at, status
           FROM activity_sessions WHERE id=?""",
        (session_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def insert_event(
    db: sqlite3.Connection,
    session_id: int,
    device_id: int,
    event: Mapping[str, Any],
    *,
    received_at: str,
) -> dict[str, Any]:
    """Persiste un evento previamente validado por la capa de actividad."""
    cursor = db.execute(
        """INSERT INTO activity_events
           (session_id, device_id, observed_at, received_at, event_type, source, domain,
            destination_ip, destination_port, protocol, app_name, page_url, search_engine, search_terms,
            email_provider, email_from, email_to, email_subject, blocked)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, device_id, event["observed_at"], received_at, event["event_type"], event["source"],
            event["domain"], event["destination_ip"], event["destination_port"], event["protocol"],
            event["app_name"], event["page_url"], event["search_engine"], event["search_terms"],
            event["email_provider"], event["email_from"], event["email_to"], event["email_subject"], event["blocked"],
        ),
    )
    row = db.execute(
        "SELECT * FROM activity_events WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    if row is None:
        raise RuntimeError("No se pudo recuperar el evento recién guardado.")
    return dict(row)


def _require_device(db: sqlite3.Connection, device_id: int | None) -> None:
    """Valida la existencia del dispositivo cuando el alcance está acotado por ID."""
    if device_id is not None and db.execute(
        "SELECT 1 FROM devices WHERE id = ?", (device_id,)
    ).fetchone() is None:
        raise LookupError("No se encontró el dispositivo.")


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



def require_device_exists(device_id: int) -> None:
    """Comprueba un dispositivo antes de hacer trabajo costoso sobre el CSV."""
    with database.connect() as db:
        _require_device(db, device_id)


_MANUAL_IMPORT_DEDUP_FIELDS = (
    "observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "page_url", "search_engine", "search_terms",
    "email_provider", "email_from", "email_to", "email_subject", "blocked",
)


def import_manual_events(
    device_id: int,
    events: list[Mapping[str, Any]],
    source_line_numbers: list[int],
    *,
    now: datetime,
    preview: bool,
) -> dict[str, Any]:
    """Valida retención y deduplica/guarda eventos manuales de forma atómica.

    La vista previa es de solo lectura. La importación toma el bloqueo de escritura
    antes de comprobar la retención y los duplicados para evitar carreras con otra
    importación o un cambio de política de retención.
    """
    if len(events) != len(source_line_numbers):
        raise ValueError("La importación recibió filas y números de línea incompatibles.")

    imported_count = 0
    skipped_duplicates = 0
    preview_dispositions: list[str] = []
    seen_in_batch: set[tuple[Any, ...]] = set()

    with database.connect() as db:
        if not preview:
            db.execute("BEGIN IMMEDIATE")
        _require_device(db, device_id)

        retention_days = get_retention_days(db)
        cutoff = _utc_iso(now - timedelta(days=retention_days))

        # Rechazar el lote completo antes de limpiar o escribir evita importaciones
        # parciales cuando alguna fila queda fuera del período conservado.
        for line, item in zip(source_line_numbers, events):
            if item["observed_at"] < cutoff:
                raise ValueError(
                    f"Fila {line}: la fecha queda fuera de la retención configurada "
                    f"de {retention_days} día(s). Aumentá la retención antes de importar "
                    "ese período y volvé a previsualizar el CSV."
                )

        duplicate_sql = (
            "SELECT 1 FROM activity_events "
            "WHERE device_id = ? AND source = 'manual_import' AND "
            + " AND ".join(f"{field} IS ?" for field in _MANUAL_IMPORT_DEDUP_FIELDS)
            + " LIMIT 1"
        )
        if preview:
            # La vista previa compara solo con eventos que aún deberían conservarse.
            duplicate_sql = duplicate_sql.replace(
                "source = 'manual_import' AND",
                "source = 'manual_import' AND observed_at >= ? AND",
            )
        else:
            cleanup(db, now=now)

        now_text = _utc_iso(now)
        for item in events:
            values = tuple(item[field] for field in _MANUAL_IMPORT_DEDUP_FIELDS)
            disposition = "new"
            if values in seen_in_batch:
                skipped_duplicates += 1
                disposition = "duplicate"
            else:
                seen_in_batch.add(values)
                params = (device_id, cutoff, *values) if preview else (device_id, *values)
                duplicate = db.execute(duplicate_sql, params).fetchone()
                if duplicate:
                    skipped_duplicates += 1
                    disposition = "duplicate"
                else:
                    if not preview:
                        db.execute(
                            """INSERT INTO activity_events
                               (session_id, device_id, observed_at, received_at, event_type, source, domain,
                                destination_ip, destination_port, protocol, app_name, page_url, search_engine, search_terms,
                                email_provider, email_from, email_to, email_subject, blocked)
                               VALUES (NULL, ?, ?, ?, ?, 'manual_import', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                device_id, item["observed_at"], now_text, item["event_type"], item["domain"],
                                item["destination_ip"], item["destination_port"], item["protocol"], item["app_name"],
                                item["page_url"], item["search_engine"], item["search_terms"],
                                item["email_provider"], item["email_from"], item["email_to"], item["email_subject"], item["blocked"],
                            ),
                        )
                    imported_count += 1

            if preview and len(preview_dispositions) < 10:
                preview_dispositions.append(disposition)

    return {
        "imported": imported_count,
        "skipped_duplicates": skipped_duplicates,
        "preview_dispositions": preview_dispositions,
    }


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

_ACTIVITY_READ_FILTER_CLAUSES = frozenset({
    "e.device_id = ?",
    "event_type = ?",
    "source = ?",
    "observed_at >= ?",
    "observed_at < ?",
})


def _require_activity_read_filters(where_sql: str, params: tuple[Any, ...]) -> None:
    """Acepta solo los predicados fijos del servicio de lectura y valores enlazados."""
    normalized = where_sql.strip() if isinstance(where_sql, str) else None
    if normalized == "":
        if params:
            raise ValueError("Los filtros de lectura no coinciden con sus parámetros.")
        return
    if not normalized or not normalized.startswith("WHERE "):
        raise ValueError("Los filtros de lectura de actividad no son válidos.")
    clauses = normalized[6:].strip().split(" AND ")
    if (
        not clauses
        or any(clause not in _ACTIVITY_READ_FILTER_CLAUSES for clause in clauses)
        or len(set(clauses)) != len(clauses)
        or len(clauses) != len(params)
    ):
        raise ValueError("Los filtros de lectura de actividad no son válidos.")


def get_activity_snapshot(
    *,
    device_id: int | None,
    event_filter: str,
    event_params: tuple[Any, ...],
    limit: int,
) -> dict[str, Any]:
    """Lee eventos y resúmenes para el panel dentro de una operación consistente."""
    _require_activity_read_filters(event_filter, event_params)
    if device_id is not None and int(device_id) < 1:
        raise ValueError("device_id debe ser un entero positivo.")

    with database.connect() as db:
        cleanup(db, now=datetime.now(timezone.utc))
        _require_device(db, device_id)
        device_params: tuple[Any, ...] = () if device_id is None else (device_id,)
        session_filter = "" if device_id is None else "WHERE s.device_id = ?"
        sessions = db.execute(
            f"""SELECT s.id, s.device_id, s.source_mode, s.started_at, s.ends_at, s.stopped_at, s.status,
                       d.display_name, d.ip_address, d.mac_address
                FROM activity_sessions s JOIN devices d ON d.id=s.device_id
                {session_filter} ORDER BY s.started_at DESC, s.id DESC LIMIT 100""",
            device_params,
        ).fetchall()
        events = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address, d.mac_address
                FROM activity_events e JOIN devices d ON d.id=e.device_id
                {event_filter} ORDER BY e.observed_at DESC, e.id DESC LIMIT ?""",
            (*event_params, max(1, min(int(limit), 500))),
        ).fetchall()

        domain_filter = (
            "WHERE domain IS NOT NULL AND domain <> ''"
            if device_id is None
            else "WHERE device_id = ? AND domain IS NOT NULL AND domain <> ''"
        )
        top_domains = db.execute(
            f"""SELECT domain, COUNT(*) AS events, MAX(observed_at) AS last_seen
                FROM activity_events {domain_filter}
                GROUP BY domain ORDER BY events DESC, last_seen DESC LIMIT 15""",
            device_params,
        ).fetchall()
        blocked_filter = " WHERE blocked = 1" if device_id is None else " WHERE blocked = 1 AND device_id = ?"
        blocked_count = db.execute(
            "SELECT COUNT(*) FROM activity_events" + blocked_filter,
            device_params,
        ).fetchone()[0]
        retention_days = get_retention_days(db)
        session_count_sql = (
            "SELECT COUNT(*) FROM activity_sessions WHERE status='active'"
            + ("" if device_id is None else " AND device_id = ?")
        )
        event_count_sql = (
            "SELECT COUNT(*) FROM activity_events"
            + ("" if device_id is None else " WHERE device_id = ?")
        )
        active_count = db.execute(session_count_sql, device_params).fetchone()[0]
        event_count = db.execute(event_count_sql, device_params).fetchone()[0]
        devices = db.execute(
            "SELECT id, display_name, ip_address, mac_address FROM devices ORDER BY display_name, ip_address"
        ).fetchall()

    return {
        "sessions": [dict(row) for row in sessions],
        "events": [dict(row) for row in events],
        "top_domains": [dict(row) for row in top_domains],
        "blocked_events": int(blocked_count),
        "devices": [dict(row) for row in devices],
        "retention_days": retention_days,
        "active_sessions": int(active_count),
        "total_events": int(event_count),
    }


def get_activity_export_rows(
    *,
    where_sql: str,
    params: tuple[Any, ...],
    device_id: int | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Recupera filas para exportación aplicando solo filtros permitidos."""
    _require_activity_read_filters(where_sql, params)
    if device_id is not None and int(device_id) < 1:
        raise ValueError("device_id debe ser un entero positivo.")

    with database.connect() as db:
        cleanup(db, now=datetime.now(timezone.utc))
        _require_device(db, device_id)
        rows = db.execute(
            f"""SELECT e.*, d.display_name, d.ip_address
                FROM activity_events e
                JOIN devices d ON d.id = e.device_id
                {where_sql}
                ORDER BY e.observed_at DESC, e.id DESC
                LIMIT ?""",
            (*params, max(1, min(int(limit), 10000))),
        ).fetchall()
    return [dict(row) for row in rows]
