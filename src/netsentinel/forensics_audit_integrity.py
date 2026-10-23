"""Cálculo y verificación de huellas encadenadas para la auditoría forense.

La cadena detecta cambios o faltantes frente a los hashes guardados, pero no
sustituye una copia externa firmada: alguien con control de SQLite podría
reconstruir tanto los registros como la cadena.
"""
from __future__ import annotations

import hashlib
import json


def audit_event_hash(
    *,
    case_id: str,
    evidence_id: str | None,
    occurred_at: str,
    actor: str,
    action: str,
    result: str,
    details_json: str,
    previous_hash: str | None,
) -> str:
    """Calcula una huella estable a partir de todos los datos del evento."""
    payload = {
        "format": "netsentinel-forensic-audit-v1",
        "case_id": case_id,
        "evidence_id": evidence_id,
        "occurred_at": occurred_at,
        "actor": actor,
        "action": action,
        "result": result,
        "details_json": details_json,
        "previous_hash": previous_hash,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
