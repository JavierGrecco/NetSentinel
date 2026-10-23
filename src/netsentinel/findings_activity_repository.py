"""Consultas acotadas de conexiones Zeek para contextualizar hallazgos.

Solo lee filas importadas explícitamente desde Zeek conn.log. No inicia captura,
no deduce amenazas y no modifica la base de datos.
"""
from __future__ import annotations

from typing import Any

from . import database

_MAX_CONTEXTS_PER_QUERY = 80
_MAX_ROWS_PER_CONTEXT = 5
_MAX_CONTEXTS_PER_REPORT = 400


def get_zeek_activity_contexts(
    contexts: list[dict[str, Any]],
    *,
    per_context_limit: int = _MAX_ROWS_PER_CONTEXT,
) -> list[dict[str, Any]]:
    """Busca coincidencias temporales por activo o IP exacta del objetivo.

    Cada contexto incluye una ventana ya calculada por el servicio de hallazgos.
    Las consultas se agrupan para mantener acotados los parámetros SQL y limitan
    las filas por contexto; una coincidencia no implica causalidad ni amenaza.
    """
    if isinstance(per_context_limit, bool) or not isinstance(per_context_limit, int):
        raise ValueError("El límite por contexto debe ser un entero.")
    if not 1 <= per_context_limit <= _MAX_ROWS_PER_CONTEXT:
        raise ValueError(f"El límite por contexto debe estar entre 1 y {_MAX_ROWS_PER_CONTEXT}.")
    if len(contexts) > _MAX_CONTEXTS_PER_REPORT:
        raise ValueError("La consulta supera el máximo de contextos permitidos.")
    if not contexts:
        return []

    selected: list[dict[str, Any]] = []
    for context in contexts:
        context_id = context.get("context_id")
        start_at = context.get("start_at")
        end_at = context.get("end_at")
        anchor_at = context.get("anchor_at")
        device_id = context.get("device_id")
        target_ip = context.get("target_ip")
        if not isinstance(context_id, str) or not context_id:
            raise ValueError("Cada contexto debe tener un identificador.")
        if not all(isinstance(value, str) and value for value in (start_at, end_at, anchor_at)):
            continue
        if start_at > end_at or (device_id is None and target_ip is None):
            continue
        if device_id is not None and (
            isinstance(device_id, bool) or not isinstance(device_id, int) or device_id < 1
        ):
            continue
        if target_ip is not None and (not isinstance(target_ip, str) or not target_ip):
            continue
        relation = context.get("relation")
        if not isinstance(relation, str):
            relation = "temporal_context"
        selected.append({
            "context_id": context_id,
            "device_id": device_id,
            "target_ip": target_ip,
            "anchor_at": anchor_at,
            "start_at": start_at,
            "end_at": end_at,
            "relation": relation,
        })

    if not selected:
        return []

    results: list[dict[str, Any]] = []
    for offset in range(0, len(selected), _MAX_CONTEXTS_PER_QUERY):
        batch = selected[offset : offset + _MAX_CONTEXTS_PER_QUERY]
        values_sql = ", ".join(["(?, ?, ?, ?, ?, ?, ?)"] * len(batch))
        parameters: list[Any] = []
        for context in batch:
            parameters.extend((
                context["context_id"],
                context["device_id"],
                context["target_ip"],
                context["anchor_at"],
                context["start_at"],
                context["end_at"],
                context["relation"],
            ))
        parameters.append(per_context_limit)

        with database.connect() as db:
            rows = db.execute(
                f"""
                WITH contexts(context_id, device_id, target_ip, anchor_at, start_at, end_at, relation)
                AS (VALUES {values_sql}),
                ranked AS (
                    SELECT
                        c.context_id,
                        c.relation AS correlation_relation,
                        ABS(julianday(e.observed_at) - julianday(c.anchor_at)) * 86400.0
                            AS time_delta_seconds,
                        ROW_NUMBER() OVER (
                            PARTITION BY c.context_id
                            ORDER BY ABS(julianday(e.observed_at) - julianday(c.anchor_at)) ASC,
                                     e.id DESC
                        ) AS context_rank,
                        e.id AS activity_id,
                        e.device_id,
                        d.display_name AS device_name,
                        d.ip_address AS device_ip,
                        e.observed_at,
                        e.received_at,
                        e.source_event_id,
                        e.source_ip,
                        e.source_port,
                        e.destination_ip,
                        e.destination_port,
                        e.protocol,
                        e.bytes_sent,
                        e.bytes_received,
                        e.packets_sent,
                        e.packets_received
                    FROM contexts c
                    JOIN activity_events e
                      ON e.observed_at >= c.start_at
                     AND e.observed_at <= c.end_at
                     AND (
                         (c.device_id IS NOT NULL AND e.device_id = c.device_id)
                         OR
                         (c.target_ip IS NOT NULL
                          AND (e.source_ip = c.target_ip OR e.destination_ip = c.target_ip))
                     )
                    JOIN devices d ON d.id = e.device_id
                    WHERE e.source = 'manual_import'
                      AND e.event_type = 'connection'
                      AND e.source_event_id LIKE 'zeek:%'
                )
                SELECT * FROM ranked
                WHERE context_rank <= ?
                ORDER BY context_id, context_rank
                """,
                (*parameters,),
            ).fetchall()

        results.extend(dict(row) for row in rows)

    return results
