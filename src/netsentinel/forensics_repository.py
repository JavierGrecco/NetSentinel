"""Persistencia de casos, evidencia y auditoría de NetSentinel Forense.

Este repositorio registra metadatos. No adquiere discos ni interpreta artefactos.
El historial de auditoría solo admite nuevas filas; las operaciones no borran evidencia.
"""
from __future__ import annotations

import json
import sqlite3
from collections import deque
import uuid
from typing import Any

from .database_storage import connect, utc_now
from .forensics_audit_integrity import audit_event_hash
from .forensics_audit_manifest import build_audit_manifest
from .forensics_errors import ForensicConflictError


def _append_audit(
    db: sqlite3.Connection,
    *,
    case_id: str,
    actor: str,
    action: str,
    result: str,
    evidence_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Agrega el evento y su huella encadenada en la misma transacción."""
    occurred_at = utc_now()
    details_json = json.dumps(details or {}, ensure_ascii=False, sort_keys=True)
    cursor = db.execute(
        """INSERT INTO forensic_audit
           (case_id, evidence_id, occurred_at, actor, action, result, details_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (case_id, evidence_id, occurred_at, actor, action, result, details_json),
    )
    audit_id = cursor.lastrowid
    # Usá la auditoría como fuente de verdad: case_id también figura en la tabla
    # de la cadena, pero esa copia redundante puede quedar inconsistente.
    latest = db.execute(
        """SELECT c.event_hash
           FROM forensic_audit_chain AS c
           JOIN forensic_audit AS a ON a.id = c.audit_id
           WHERE a.case_id = ? ORDER BY a.id DESC LIMIT 1""",
        (case_id,),
    ).fetchone()
    previous_hash = latest["event_hash"] if latest else None
    event_hash = audit_event_hash(
        case_id=case_id,
        evidence_id=evidence_id,
        occurred_at=occurred_at,
        actor=actor,
        action=action,
        result=result,
        details_json=details_json,
        previous_hash=previous_hash,
    )
    db.execute(
        """INSERT INTO forensic_audit_chain
           (audit_id, case_id, previous_hash, event_hash)
           VALUES (?, ?, ?, ?)""",
        (audit_id, case_id, previous_hash, event_hash),
    )


def _case_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "case_number": row["case_number"],
        "title": row["title"],
        "authority_reference": row["authority_reference"],
        "objective": row["objective"],
        "scope": row["scope"],
        "examiner": row["examiner"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "evidence_count": row["evidence_count"] if "evidence_count" in row.keys() else 0,
    }


def _evidence_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "evidence_number": row["evidence_number"],
        "label": row["label"],
        "source_type": row["source_type"],
        "original_name": row["original_name"],
        "source_description": row["source_description"],
        "received_from": row["received_from"],
        "received_at_original": row["received_at_original"],
        "received_timezone": row["received_timezone"],
        "size_bytes": row["size_bytes"],
        "reported_sha256": row["reported_sha256"],
        "hash_source": row["hash_source"],
        "created_at": row["created_at"],
        "hash_status": "reported" if row["reported_sha256"] else "not_provided",
        "last_integrity_check_status": (
            row["last_integrity_check_status"]
            if "last_integrity_check_status" in row.keys()
            else None
        ),
        "last_integrity_check_at": (
            row["last_integrity_check_at"]
            if "last_integrity_check_at" in row.keys()
            else None
        ),
        "last_calculated_sha256": (
            row["last_calculated_sha256"]
            if "last_calculated_sha256" in row.keys()
            else None
        ),
    }


def _get_case_row(db: sqlite3.Connection, case_id: str) -> sqlite3.Row | None:
    return db.execute(
        """SELECT c.*, (SELECT COUNT(*) FROM forensic_evidence e WHERE e.case_id = c.id)
           AS evidence_count
           FROM forensic_cases c WHERE c.id = ?""",
        (case_id,),
    ).fetchone()


def list_cases(*, limit: int = 100) -> list[dict[str, Any]]:
    """Devuelve los casos más recientes, sin contenido de evidencia."""
    with connect() as db:
        rows = db.execute(
            """SELECT c.*, (SELECT COUNT(*) FROM forensic_evidence e WHERE e.case_id = c.id)
               AS evidence_count
               FROM forensic_cases c
               ORDER BY c.updated_at DESC, c.case_number ASC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [_case_dict(row) for row in rows]


def get_case(case_id: str) -> dict[str, Any] | None:
    """Busca un caso por su identificador estable."""
    with connect() as db:
        row = _get_case_row(db, case_id)
    return _case_dict(row) if row else None


def create_case(
    *,
    case_number: str,
    title: str,
    authority_reference: str,
    objective: str,
    scope: str,
    examiner: str,
    actor: str,
) -> dict[str, Any]:
    """Crea un caso y registra la apertura en la misma transacción."""
    case_id = str(uuid.uuid4())
    now = utc_now()
    with connect() as db:
        try:
            db.execute(
                """INSERT INTO forensic_cases
                   (id, case_number, title, authority_reference, objective, scope,
                    examiner, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)""",
                (
                    case_id, case_number, title, authority_reference, objective, scope,
                    examiner, now, now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ForensicConflictError("Ya existe un caso con ese identificador.") from exc
        _append_audit(
            db,
            case_id=case_id,
            actor=actor,
            action="case_opened",
            result="success",
            details={"case_number": case_number, "status": "open"},
        )
        row = _get_case_row(db, case_id)
    if row is None:
        raise RuntimeError("El caso se creó, pero no pudo volver a leerse.")
    return _case_dict(row)


def close_case(*, case_id: str, actor: str) -> dict[str, Any] | None:
    """Cierra un caso sin borrar evidencia ni historial."""
    with connect() as db:
        # Serializá el cierre con la recepción de evidencia y la verificación de hashes.
        db.execute("BEGIN IMMEDIATE")
        row = _get_case_row(db, case_id)
        if row is None:
            return None
        if row["status"] == "closed":
            return _case_dict(row)
        now = utc_now()
        db.execute(
            "UPDATE forensic_cases SET status = 'closed', updated_at = ? WHERE id = ?",
            (now, case_id),
        )
        _append_audit(
            db,
            case_id=case_id,
            actor=actor,
            action="case_closed",
            result="success",
            details={"status": "closed"},
        )
        updated = _get_case_row(db, case_id)
    return _case_dict(updated) if updated else None


def add_evidence(
    *,
    case_id: str,
    label: str,
    source_type: str,
    original_name: str | None,
    source_description: str,
    received_from: str,
    received_at_original: str,
    received_timezone: str,
    size_bytes: int | None,
    reported_sha256: str | None,
    hash_source: str | None,
    actor: str,
) -> dict[str, Any] | None:
    """Registra metadatos de un elemento recibido; no copia ni abre el archivo."""
    evidence_id = str(uuid.uuid4())
    now = utc_now()
    with connect() as db:
        # Reservá la escritura antes de calcular el siguiente número: dos solicitudes
        # concurrentes no deben recibir el mismo identificador E-0001, E-0002, etc.
        db.execute("BEGIN IMMEDIATE")
        case = _get_case_row(db, case_id)
        if case is None:
            return None
        if case["status"] != "open":
            raise ForensicConflictError("El caso está cerrado. No se puede agregar evidencia.")
        existing = db.execute(
            "SELECT COUNT(*) FROM forensic_evidence WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        evidence_number = f"E-{existing + 1:04d}"
        db.execute(
            """INSERT INTO forensic_evidence
               (id, case_id, evidence_number, label, source_type, original_name,
                source_description, received_from, received_at_original, received_timezone,
                size_bytes, reported_sha256, hash_source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evidence_id, case_id, evidence_number, label, source_type, original_name,
                source_description, received_from, received_at_original, received_timezone,
                size_bytes, reported_sha256, hash_source, now,
            ),
        )
        db.execute(
            "UPDATE forensic_cases SET updated_at = ? WHERE id = ?",
            (now, case_id),
        )
        _append_audit(
            db,
            case_id=case_id,
            evidence_id=evidence_id,
            actor=actor,
            action="evidence_registered",
            result="success",
            details={
                "evidence_number": evidence_number,
                "source_type": source_type,
                "reported_hash_present": bool(reported_sha256),
                "size_bytes": size_bytes,
            },
        )
        row = db.execute("SELECT * FROM forensic_evidence WHERE id = ?", (evidence_id,)).fetchone()
    if row is None:
        raise RuntimeError("La evidencia se registró, pero no pudo volver a leerse.")
    return _evidence_dict(row)


def list_evidence(case_id: str) -> list[dict[str, Any]] | None:
    """Lista los elementos de un caso; devuelve None si el caso no existe."""
    with connect() as db:
        if _get_case_row(db, case_id) is None:
            return None
        rows = db.execute(
            """SELECT e.*,
                      (SELECT status FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_integrity_check_status,
                      (SELECT checked_at FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_integrity_check_at,
                      (SELECT calculated_sha256 FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_calculated_sha256
               FROM forensic_evidence e
               WHERE e.case_id = ? ORDER BY e.created_at ASC, e.evidence_number ASC""",
            (case_id,),
        ).fetchall()
    return [_evidence_dict(row) for row in rows]


def get_evidence(*, case_id: str, evidence_id: str) -> dict[str, Any] | None:
    """Devuelve evidencia solo si pertenece al caso indicado."""
    with connect() as db:
        row = db.execute(
            "SELECT * FROM forensic_evidence WHERE case_id = ? AND id = ?",
            (case_id, evidence_id),
        ).fetchone()
    return _evidence_dict(row) if row else None


def _integrity_check_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Devuelve el resultado de una comparación sin incluir rutas completas."""
    return {
        "id": row["id"],
        "case_id": row["case_id"],
        "evidence_id": row["evidence_id"],
        "checked_at": row["checked_at"],
        "actor": row["actor"],
        "copy_confirmed": bool(row["copy_confirmed"]),
        "algorithm": row["algorithm"],
        "source_name": row["source_name"],
        "expected_sha256": row["expected_sha256"],
        "calculated_sha256": row["calculated_sha256"],
        "size_bytes": row["size_bytes"],
        "status": row["status"],
        "tool_version": row["tool_version"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
    }


def record_integrity_check(
    *,
    case_id: str,
    evidence_id: str,
    actor: str,
    source_name: str,
    calculated_sha256: str | None,
    size_bytes: int | None,
    tool_version: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any] | None:
    """Guarda cada intento y su resultado; nunca conserva la ruta completa."""
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        case = _get_case_row(db, case_id)
        evidence = db.execute(
            "SELECT * FROM forensic_evidence WHERE case_id = ? AND id = ?",
            (case_id, evidence_id),
        ).fetchone()
        if case is None or evidence is None:
            return None
        if case["status"] != "open":
            raise ForensicConflictError("El caso está cerrado. No se pueden registrar nuevas comprobaciones.")

        expected = evidence["reported_sha256"]
        if not expected:
            raise ForensicConflictError("No hay un SHA-256 de referencia informado para comparar.")
        if error_code:
            result = "failed"
            calculated_sha256 = None
            size_bytes = None
        else:
            if not calculated_sha256 or size_bytes is None:
                raise ValueError("La comprobación no devolvió un hash y un tamaño válidos.")
            result = "match" if calculated_sha256.lower() == expected.lower() else "mismatch"

        checked_at = utc_now()
        cursor = db.execute(
            """INSERT INTO forensic_integrity_checks
               (case_id, evidence_id, checked_at, actor, copy_confirmed, algorithm, source_name,
                expected_sha256, calculated_sha256, size_bytes, status, tool_version,
                error_code, error_message)
               VALUES (?, ?, ?, ?, 1, 'SHA-256', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                case_id, evidence_id, checked_at, actor, source_name, expected,
                calculated_sha256, size_bytes, result, tool_version, error_code, error_message,
            ),
        )
        check_id = cursor.lastrowid
        details = {
            "check_id": check_id,
            "source_name": source_name,
            "algorithm": "SHA-256",
            "copy_confirmed": True,
            "expected_sha256": expected,
            "calculated_sha256": calculated_sha256,
            "size_bytes": size_bytes,
            "tool_version": tool_version,
            "status": result,
        }
        if error_code:
            details["error_code"] = error_code
            details["error_message"] = error_message
        _append_audit(
            db,
            case_id=case_id,
            evidence_id=evidence_id,
            actor=actor,
            action="evidence_hash_compared" if result in {"match", "mismatch"} else "evidence_hash_check_failed",
            result=result,
            details=details,
        )
        db.execute(
            "UPDATE forensic_cases SET updated_at = ? WHERE id = ?",
            (checked_at, case_id),
        )
        row = db.execute(
            "SELECT * FROM forensic_integrity_checks WHERE id = ?",
            (check_id,),
        ).fetchone()
    return _integrity_check_dict(row) if row else None


def list_integrity_checks(*, case_id: str, evidence_id: str) -> list[dict[str, Any]] | None:
    """Lista las comparaciones de un elemento, de la más reciente a la más antigua."""
    with connect() as db:
        evidence = db.execute(
            "SELECT id FROM forensic_evidence WHERE case_id = ? AND id = ?",
            (case_id, evidence_id),
        ).fetchone()
        if evidence is None:
            return None
        rows = db.execute(
            """SELECT * FROM forensic_integrity_checks
               WHERE case_id = ? AND evidence_id = ?
               ORDER BY id DESC""",
            (case_id, evidence_id),
        ).fetchall()
    return [_integrity_check_dict(row) for row in rows]


def record_custody_transfer(
    *,
    case_id: str,
    evidence_id: str,
    actor: str,
    from_custodian: str,
    to_custodian: str,
    transferred_at_original: str,
    purpose: str,
    delivery_method: str,
    condition_notes: str | None,
    seal_identifier: str | None,
) -> dict[str, Any] | None:
    """Registra una transferencia como evento inmutable en la auditoría encadenada."""
    with connect() as db:
        # Serializa los traspasos con el cierre y con otras operaciones del caso.
        db.execute("BEGIN IMMEDIATE")
        case = _get_case_row(db, case_id)
        evidence = db.execute(
            """SELECT evidence_number FROM forensic_evidence
               WHERE case_id = ? AND id = ?""",
            (case_id, evidence_id),
        ).fetchone()
        if case is None or evidence is None:
            return None
        if case["status"] != "open":
            raise ForensicConflictError(
                "El caso está cerrado. No se pueden registrar nuevas transferencias de custodia."
            )

        # No agregues una transferencia sobre una cadena ya rota: primero debe revisarse.
        prior_events = _audit_events_from_connection(db, case_id=case_id, limit=None)
        if any(event["integrity_status"] != "valid" for event in prior_events):
            raise ForensicConflictError(
                "La cadena de auditoría ya presenta faltantes o cambios. "
                "Revisá la integridad antes de registrar otra transferencia."
            )

        prior_transfer = db.execute(
            """SELECT details_json FROM forensic_audit
               WHERE case_id = ? AND evidence_id = ?
                 AND action = 'evidence_custody_transferred'
               ORDER BY id DESC LIMIT 1""",
            (case_id, evidence_id),
        ).fetchone()
        if prior_transfer is None:
            expected_from = db.execute(
                "SELECT received_from FROM forensic_evidence WHERE case_id = ? AND id = ?",
                (case_id, evidence_id),
            ).fetchone()["received_from"]
        else:
            try:
                expected_from = json.loads(prior_transfer["details_json"]).get("to_custodian")
            except (json.JSONDecodeError, TypeError, AttributeError):
                expected_from = None
        if (
            not expected_from
            or expected_from.strip().casefold() != from_custodian.strip().casefold()
        ):
            raise ForensicConflictError(
                "La persona que entrega no coincide con la última custodia registrada. "
                "Revisá la persona indicada o documentá primero el traspaso que falta."
            )

        now = utc_now()
        details = {
            "evidence_number": evidence["evidence_number"],
            "from_custodian": from_custodian,
            "to_custodian": to_custodian,
            "transferred_at_original": transferred_at_original,
            "purpose": purpose,
            "delivery_method": delivery_method,
            "condition_notes": condition_notes,
            "seal_identifier": seal_identifier,
        }
        _append_audit(
            db,
            case_id=case_id,
            evidence_id=evidence_id,
            actor=actor,
            action="evidence_custody_transferred",
            result="success",
            details=details,
        )
        db.execute(
            "UPDATE forensic_cases SET updated_at = ? WHERE id = ?",
            (now, case_id),
        )
        event = _audit_events_from_connection(db, case_id=case_id, limit=1)[0]
    return event


def _audit_events_from_connection(
    db: sqlite3.Connection, *, case_id: str, limit: int | None
) -> list[dict[str, Any]]:
    """Verifica la cadena completa y devuelve eventos recientes primero."""
    rows = db.execute(
        """SELECT a.id, a.case_id, a.evidence_id, a.occurred_at, a.actor,
                  a.action, a.result, a.details_json,
                  c.case_id AS chain_case_id, c.previous_hash, c.event_hash
           FROM forensic_audit a
           LEFT JOIN forensic_audit_chain c ON c.audit_id = a.id
           WHERE a.case_id = ?
           ORDER BY a.id ASC""",
        (case_id,),
    )
    recent: deque[dict[str, Any]] = deque(maxlen=limit)
    previous_event_hash: str | None = None
    chain_broken = False
    for row in rows:
        stored_hash = row["event_hash"]
        stored_previous_hash = row["previous_hash"]
        if stored_hash is None:
            integrity_status = "missing"
            chain_broken = True
        else:
            calculated_hash = audit_event_hash(
                case_id=row["case_id"],
                evidence_id=row["evidence_id"],
                occurred_at=row["occurred_at"],
                actor=row["actor"],
                action=row["action"],
                result=row["result"],
                details_json=row["details_json"],
                previous_hash=stored_previous_hash,
            )
            links_to_previous = stored_previous_hash == previous_event_hash
            matches_event = calculated_hash == stored_hash
            matches_case_id = row["chain_case_id"] == row["case_id"]
            if not chain_broken and links_to_previous and matches_event and matches_case_id:
                integrity_status = "valid"
            else:
                integrity_status = "invalid"
                chain_broken = True
            previous_event_hash = stored_hash

        try:
            details = json.loads(row["details_json"])
        except (json.JSONDecodeError, TypeError):
            details = {"_error": "El detalle almacenado no es JSON válido."}
            integrity_status = "invalid"
            chain_broken = True

        recent.append({
            "id": row["id"],
            "case_id": row["case_id"],
            "evidence_id": row["evidence_id"],
            "occurred_at": row["occurred_at"],
            "actor": row["actor"],
            "action": row["action"],
            "result": row["result"],
            "details": details,
            "previous_event_hash": stored_previous_hash,
            "event_hash": stored_hash,
            "integrity_status": integrity_status,
        })
    return list(reversed(recent))


def list_audit_events(
    *, case_id: str, limit: int | None = 100
) -> list[dict[str, Any]] | None:
    """Devuelve operaciones recientes y detecta roturas en la cadena de hashes."""
    with connect() as db:
        if _get_case_row(db, case_id) is None:
            return None
        return _audit_events_from_connection(db, case_id=case_id, limit=limit)


def export_audit_manifest(*, case_id: str) -> dict[str, Any] | None:
    """Exporta caso y auditoría desde una sola conexión para conservar una vista coherente."""
    with connect() as db:
        case_row = _get_case_row(db, case_id)
        if case_row is None:
            return None
        case = _case_dict(case_row)
        events_newest_first = _audit_events_from_connection(db, case_id=case_id, limit=None)
        return build_audit_manifest(
            case=case,
            events=list(reversed(events_newest_first)),
            exported_at=utc_now(),
        )


def export_case_manifest_data(*, case_id: str) -> dict[str, Any] | None:
    """Lee una instantánea coherente del caso, la evidencia, los checks y la auditoría.

    Devuelve metadatos únicamente: nunca lee el contenido de los archivos de evidencia
    ni serializa rutas completas. La construcción del formato exportable pertenece al
    servicio, no a la capa de persistencia.
    """
    with connect() as db:
        # Mantener las lecturas en una misma instantánea evita mezclar una actualización
        # del caso con verificaciones o eventos agregados durante la exportación.
        db.execute("BEGIN")
        case_row = _get_case_row(db, case_id)
        if case_row is None:
            return None

        case = _case_dict(case_row)
        evidence_rows = db.execute(
            """SELECT e.*,
                      (SELECT status FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_integrity_check_status,
                      (SELECT checked_at FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_integrity_check_at,
                      (SELECT calculated_sha256 FROM forensic_integrity_checks h
                       WHERE h.evidence_id = e.id ORDER BY h.id DESC LIMIT 1)
                      AS last_calculated_sha256
               FROM forensic_evidence e
               WHERE e.case_id = ? ORDER BY e.created_at ASC, e.evidence_number ASC""",
            (case_id,),
        ).fetchall()

        check_rows = db.execute(
            """SELECT * FROM forensic_integrity_checks
               WHERE case_id = ? ORDER BY id ASC""",
            (case_id,),
        ).fetchall()
        checks_by_evidence: dict[str, list[dict[str, Any]]] = {}
        for row in check_rows:
            check = _integrity_check_dict(row)
            checks_by_evidence.setdefault(check["evidence_id"], []).append(check)

        evidence = []
        for row in evidence_rows:
            item = _evidence_dict(row)
            item["integrity_checks"] = checks_by_evidence.get(item["id"], [])
            evidence.append(item)

        audit_events_newest_first = _audit_events_from_connection(
            db, case_id=case_id, limit=None
        )
        exported_at = utc_now()

    return {
        "case": case,
        "evidence": evidence,
        "audit_events": list(reversed(audit_events_newest_first)),
        "exported_at": exported_at,
    }
