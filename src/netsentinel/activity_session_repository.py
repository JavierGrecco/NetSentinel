"""Operaciones SQLite para sesiones autorizadas y eventos recibidos.

El servicio de sesiones valida la autorización y los datos. Este módulo se limita a
guardar y recuperar filas dentro de la conexión que le entrega el servicio.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from typing import Any


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
            source_ip, source_port, destination_ip, destination_port, protocol,
            bytes_sent, bytes_received, packets_sent, packets_received, network_interface, source_event_id,
            app_name, page_url, search_engine, search_terms, email_provider, email_from, email_to, email_subject, blocked)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id, device_id, event["observed_at"], received_at, event["event_type"], event["source"],
            event["domain"], event.get("source_ip"), event.get("source_port"),
            event["destination_ip"], event["destination_port"], event["protocol"],
            event.get("bytes_sent"), event.get("bytes_received"), event.get("packets_sent"),
            event.get("packets_received"), event.get("network_interface"), event.get("source_event_id"),
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
