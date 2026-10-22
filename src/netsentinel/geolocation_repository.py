"""Lecturas acotadas de IP de destino presentes en eventos ya guardados.

Este repositorio no consulta DNS, no captura tráfico y no llama a servicios externos.
Solo devuelve metadatos que una fuente local o una importación ya dejó en SQLite.
"""
from __future__ import annotations

from typing import Any

from . import database


def get_destination_ip_observations(*, limit: int = 250) -> dict[str, Any]:
    """Resume IP de destino observadas, más recientes primero, sin traer URLs completas."""
    bounded_limit = max(1, min(int(limit), 500))
    with database.connect() as db:
        total_events = int(
            db.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0]
        )
        events_with_ip = int(
            db.execute(
                """SELECT COUNT(*) FROM activity_events
                   WHERE destination_ip IS NOT NULL AND TRIM(destination_ip) <> ''"""
            ).fetchone()[0]
        )
        events_without_ip = total_events - events_with_ip
        unique_ips = int(
            db.execute(
                """SELECT COUNT(DISTINCT TRIM(destination_ip)) FROM activity_events
                   WHERE destination_ip IS NOT NULL AND TRIM(destination_ip) <> ''"""
            ).fetchone()[0]
        )
        rows = db.execute(
            """SELECT TRIM(e.destination_ip) AS ip,
                      COUNT(*) AS event_count,
                      MAX(e.observed_at) AS last_seen,
                      (SELECT NULLIF(TRIM(recent.domain), '')
                       FROM activity_events recent
                       WHERE TRIM(recent.destination_ip) = TRIM(e.destination_ip)
                       ORDER BY recent.observed_at DESC, recent.id DESC
                       LIMIT 1) AS sample_domain
               FROM activity_events e
               WHERE e.destination_ip IS NOT NULL AND TRIM(e.destination_ip) <> ''
               GROUP BY TRIM(e.destination_ip)
               ORDER BY MAX(e.observed_at) DESC, TRIM(e.destination_ip) ASC
               LIMIT ?""",
            (bounded_limit,),
        ).fetchall()

    return {
        "total_events": total_events,
        "events_with_destination_ip": events_with_ip,
        "events_without_destination_ip": events_without_ip,
        "unique_destination_ips": unique_ips,
        "destination_ips": [dict(row) for row in rows],
        "limited": unique_ips > len(rows),
    }
