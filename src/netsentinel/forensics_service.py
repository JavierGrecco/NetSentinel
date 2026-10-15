"""Reglas de uso para registrar casos y evidencia, sin depender de HTTP.

El nombre del operador es un dato declarado por la persona usuaria; todavía no es una
identidad autenticada. Este servicio registra metadatos y no abre ni copia archivos.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from . import __version__, forensics_repository
from .forensics_integrity import ForensicIntegrityError, calculate_sha256


_ALLOWED_SOURCE_TYPES = frozenset({
    "disk_image", "file_copy", "browser_export", "email_export", "network_log", "other"
})
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_CASE_NUMBER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$")

class ForensicHashCheckError(ValueError):
    """Error de lectura seguro para la API, con código y mensaje sin rutas."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code



def _required_text(value: str, field_name: str, max_length: int) -> str:
    """Quita espacios exteriores y rechaza texto vacío o controles invisibles."""
    if not isinstance(value, str):
        raise ValueError(f"El campo {field_name} debe ser texto.")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"Completá el campo {field_name}.")
    if len(cleaned) > max_length:
        raise ValueError(f"El campo {field_name} supera el máximo de {max_length} caracteres.")
    if any(ord(char) < 32 and char not in "\n\t" for char in cleaned):
        raise ValueError(f"El campo {field_name} contiene caracteres no permitidos.")
    return cleaned


def _optional_text(value: str | None, field_name: str, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise ValueError(f"El campo {field_name} supera el máximo de {max_length} caracteres.")
    if any(ord(char) < 32 and char not in "\n\t" for char in cleaned):
        raise ValueError(f"El campo {field_name} contiene caracteres no permitidos.")
    return cleaned


def _validate_iso_timestamp(value: str) -> str:
    """Exige fecha ISO-8601 con zona u offset y conserva el texto introducido."""
    timestamp = _required_text(value, "fecha de recepción", 64)
    normalized = timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("La fecha de recepción debe tener formato ISO-8601.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("La fecha de recepción debe incluir una zona horaria o un offset.")
    return timestamp


def list_cases(*, limit: int = 100) -> list[dict[str, Any]]:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("El límite debe estar entre 1 y 500.")
    return forensics_repository.list_cases(limit=limit)


def get_case(case_id: str) -> dict[str, Any] | None:
    return forensics_repository.get_case(case_id)


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
    """Abre un caso si se documenta la autoridad y el alcance de trabajo."""
    number = _required_text(case_number, "identificador del caso", 64)
    if not _CASE_NUMBER_RE.fullmatch(number):
        raise ValueError("Usá letras, números, punto, guion, guion bajo o barra en el identificador.")
    return forensics_repository.create_case(
        case_number=number,
        title=_required_text(title, "nombre del caso", 160),
        authority_reference=_required_text(authority_reference, "referencia de autorización", 240),
        objective=_required_text(objective, "objetivo", 1000),
        scope=_required_text(scope, "alcance autorizado", 2000),
        examiner=_required_text(examiner, "examinador responsable", 120),
        actor=_required_text(actor, "operador", 120),
    )


def close_case(*, case_id: str, actor: str) -> dict[str, Any] | None:
    return forensics_repository.close_case(
        case_id=case_id,
        actor=_required_text(actor, "operador", 120),
    )


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
    """Registra datos de recepción y, si corresponde, un hash declarado por la fuente."""
    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise ValueError("Elegí un tipo de fuente permitido.")
    if size_bytes is not None and (
        isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0
    ):
        raise ValueError("El tamaño debe ser un número entero igual o mayor que cero.")
    reported_hash = _optional_text(reported_sha256, "hash informado", 64)
    normalized_hash_source = _optional_text(hash_source, "origen del hash", 240)
    if reported_hash is not None:
        if not _SHA256_RE.fullmatch(reported_hash):
            raise ValueError("El hash informado debe tener 64 caracteres hexadecimales SHA-256.")
        reported_hash = reported_hash.lower()
    if reported_hash and not normalized_hash_source:
        raise ValueError("Indicá quién o qué herramienta informó el hash.")
    clean_original_name = _optional_text(original_name, "nombre original", 255)
    if clean_original_name is not None and (
        "/" in clean_original_name
        or "\\" in clean_original_name
        or clean_original_name in {".", ".."}
    ):
        raise ValueError("Indicá solo el nombre del archivo, sin carpetas ni ruta completa.")

    return forensics_repository.add_evidence(
        case_id=case_id,
        label=_required_text(label, "descripción breve", 160),
        source_type=source_type,
        original_name=clean_original_name,
        source_description=_required_text(source_description, "procedencia", 2000),
        received_from=_required_text(received_from, "persona o fuente que entrega", 160),
        received_at_original=_validate_iso_timestamp(received_at_original),
        received_timezone=_required_text(received_timezone, "zona horaria", 80),
        size_bytes=size_bytes,
        reported_sha256=reported_hash,
        hash_source=normalized_hash_source,
        actor=_required_text(actor, "operador", 120),
    )


def verify_evidence_copy(
    *,
    case_id: str,
    evidence_id: str,
    source_path: str,
    actor: str,
    confirm_working_copy: bool,
) -> dict[str, Any] | None:
    """Compara una copia local elegida expresamente contra el hash declarado.

    La ruta se usa solo para abrir el archivo durante esta operación: no se guarda,
    no se devuelve y no se agrega al historial. Leer puede cambiar metadatos de acceso,
    así que la persona debe confirmar que seleccionó una copia autorizada, no el original.
    """
    operator = _required_text(actor, "operador", 120)
    if confirm_working_copy is not True:
        raise ValueError(
            "Confirmá que el archivo elegido es una copia de trabajo autorizada, no el soporte original."
        )
    path = _required_text(source_path, "ruta local de la copia", 4096)
    case = forensics_repository.get_case(case_id)
    if case is None:
        return None
    if case["status"] != "open":
        raise ValueError("El caso está cerrado. No se pueden iniciar nuevas comprobaciones.")
    evidence = forensics_repository.get_evidence(case_id=case_id, evidence_id=evidence_id)
    if evidence is None:
        return None
    expected_hash = evidence["reported_sha256"]
    if not expected_hash:
        raise ValueError("No hay un SHA-256 de referencia informado para comparar.")

    # Solo conservamos el nombre del archivo; la ruta puede contener datos personales.
    source_name = re.split(r"[\\/]", path)[-1] or "archivo-sin-nombre"
    try:
        calculated = calculate_sha256(path)
    except ForensicIntegrityError as exc:
        forensics_repository.record_integrity_check(
            case_id=case_id,
            evidence_id=evidence_id,
            actor=operator,
            source_name=source_name,
            calculated_sha256=None,
            size_bytes=None,
            tool_version=__version__,
            error_code=exc.code,
            error_message=str(exc),
        )
        raise ForensicHashCheckError(exc.code, str(exc)) from exc

    return forensics_repository.record_integrity_check(
        case_id=case_id,
        evidence_id=evidence_id,
        actor=operator,
        source_name=source_name,
        calculated_sha256=calculated.sha256,
        size_bytes=calculated.size_bytes,
        tool_version=__version__,
    )


def list_integrity_checks(
    *, case_id: str, evidence_id: str
) -> list[dict[str, Any]] | None:
    """Consulta las comparaciones y los intentos fallidos de un elemento."""
    return forensics_repository.list_integrity_checks(case_id=case_id, evidence_id=evidence_id)


def list_evidence(case_id: str) -> list[dict[str, Any]] | None:
    return forensics_repository.list_evidence(case_id)


def list_audit_events(*, case_id: str, limit: int = 100) -> list[dict[str, Any]] | None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("El límite debe estar entre 1 y 500.")
    return forensics_repository.list_audit_events(case_id=case_id, limit=limit)
