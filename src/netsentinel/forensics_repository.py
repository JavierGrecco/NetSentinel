"""Persistencia de casos, evidencia y auditoría de NetSentinel Forense.

Este repositorio registra metadatos. No adquiere discos ni interpreta artefactos.
El historial de auditoría solo admite nuevas filas; las operaciones no borran evidencia.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from .database_storage import connect, utc_now


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
    """Agrega un evento de auditoría sin guardar contenido de archivos ni secretos."""
    db.execute(
        """INSERT INTO forensic_audit
           (case_id, evidence_id, occurred_at, actor, action, result, details_json)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            case_id,
            evidence_id,
            utc_now(),
            actor,
            action,
            result,
            json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
        ),
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
            raise ValueError("Ya existe un caso con ese identificador.") from exc
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
            raise ValueError("El caso está cerrado. No se puede agregar evidencia.")
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
            raise ValueError("El caso está cerrado. No se pueden registrar nuevas comprobaciones.")

        expected = evidence["reported_sha256"]
        if not expected:
            raise ValueError("No hay un SHA-256 de referencia informado para comparar.")
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


def list_audit_events(*, case_id: str, limit: int = 100) -> list[dict[str, Any]] | None:
    """Devuelve operaciones recientes del caso, sin datos originales del archivo."""
    with connect() as db:
        if _get_case_row(db, case_id) is None:
            return None
        rows = db.execute(
            """SELECT id, case_id, evidence_id, occurred_at, actor, action, result, details_json
               FROM forensic_audit WHERE case_id = ?
               ORDER BY id DESC LIMIT ?""",
            (case_id, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "case_id": row["case_id"],
            "evidence_id": row["evidence_id"],
            "occurred_at": row["occurred_at"],
            "actor": row["actor"],
            "action": row["action"],
            "result": row["result"],
            "details": json.loads(row["details_json"]),
        }
        for row in rows
    ]
