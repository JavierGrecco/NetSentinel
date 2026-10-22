"""Rutas locales para administrar casos y registrar metadatos de evidencia."""
from __future__ import annotations

from typing import Literal
from uuid import UUID

import json

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from .. import forensics_service

router = APIRouter(tags=["forensics"])


class CaseCreateRequest(BaseModel):
    """Datos mínimos para abrir un caso con autorización y alcance documentados."""

    model_config = ConfigDict(extra="forbid")

    case_number: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    authority_reference: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=1000)
    scope: str = Field(min_length=1, max_length=2000)
    examiner: str = Field(min_length=1, max_length=120)
    actor: str = Field(min_length=1, max_length=120)


class OperatorActionRequest(BaseModel):
    """Nombre declarado de la persona que solicita el cambio, sin autenticación de cuenta."""

    model_config = ConfigDict(extra="forbid")

    actor: str = Field(min_length=1, max_length=120)


class EvidenceCreateRequest(BaseModel):
    """Metadatos de recepción. No adjunta, abre ni copia archivos del equipo."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=160)
    source_type: Literal[
        "disk_image", "file_copy", "browser_export", "email_export", "network_log", "other"
    ]
    original_name: str | None = Field(default=None, max_length=255)
    source_description: str = Field(min_length=1, max_length=2000)
    received_from: str = Field(min_length=1, max_length=160)
    received_at_original: str = Field(min_length=1, max_length=64)
    received_timezone: str = Field(min_length=1, max_length=80)
    size_bytes: int | None = Field(default=None, ge=0, strict=True)
    reported_sha256: str | None = Field(default=None, max_length=64)
    hash_source: str | None = Field(default=None, max_length=240)
    actor: str = Field(min_length=1, max_length=120)


class EvidenceHashCheckRequest(BaseModel):
    """Orden explícita para comparar una copia elegida con un hash de referencia."""

    model_config = ConfigDict(extra="forbid")

    # Dejá que el servicio registre nombres malformados de tamaño acotado con
    # un marcador genérico; el límite portable de 255 caracteres se aplica allí.
    source_name: str = Field(max_length=4096)
    actor: str = Field(min_length=1, max_length=120)
    confirm_working_copy: bool = Field(strict=True)


class CustodyTransferRequest(BaseModel):
    """Datos declarados para registrar la entrega de un elemento entre custodios."""

    model_config = ConfigDict(extra="forbid")

    from_custodian: str = Field(min_length=1, max_length=160)
    to_custodian: str = Field(min_length=1, max_length=160)
    transferred_at_original: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=1, max_length=500)
    delivery_method: str = Field(min_length=1, max_length=160)
    condition_notes: str | None = Field(default=None, max_length=500)
    seal_identifier: str | None = Field(default=None, max_length=120)
    actor: str = Field(min_length=1, max_length=120)


def _case_or_404(case_id: UUID) -> dict:
    """Busca un caso sin reflejar en el error datos enviados por el cliente."""
    case = forensics_service.get_case(str(case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    return case


@router.get("/api/forensics/cases")
def get_forensic_cases(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Lista los casos locales, empezando por los actualizados más recientemente."""
    try:
        return {"items": forensics_service.list_cases(limit=limit), "limit": limit}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/forensics/cases", status_code=status.HTTP_201_CREATED)
def create_forensic_case(body: CaseCreateRequest) -> dict:
    """Abre un caso y deja constancia de la operación en la auditoría."""
    try:
        return forensics_service.create_case(**body.model_dump())
    except forensics_service.ForensicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/forensics/cases/{case_id}")
def get_forensic_case(case_id: UUID) -> dict:
    """Devuelve los datos de un caso sin exponer archivos ni secretos."""
    return _case_or_404(case_id)


@router.post("/api/forensics/cases/{case_id}/close")
def close_forensic_case(case_id: UUID, body: OperatorActionRequest) -> dict:
    """Cierra el caso sin borrar la evidencia ni el historial."""
    _case_or_404(case_id)
    try:
        case = forensics_service.close_case(case_id=str(case_id), actor=body.actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if case is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    return case


@router.get("/api/forensics/cases/{case_id}/evidence")
def get_forensic_evidence(case_id: UUID) -> dict:
    """Lista los elementos recibidos para un caso existente."""
    items = forensics_service.list_evidence(str(case_id))
    if items is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    return {"items": items}


@router.post(
    "/api/forensics/cases/{case_id}/evidence",
    status_code=status.HTTP_201_CREATED,
)
def register_forensic_evidence(case_id: UUID, body: EvidenceCreateRequest) -> dict:
    """Registra información de recepción; no lee ni altera el archivo de origen."""
    _case_or_404(case_id)
    try:
        evidence = forensics_service.add_evidence(case_id=str(case_id), **body.model_dump())
    except forensics_service.ForensicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if evidence is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    return evidence


@router.post(
    "/api/forensics/cases/{case_id}/evidence/{evidence_id}/custody-transfers",
    status_code=status.HTTP_201_CREATED,
)
def register_forensic_custody_transfer(
    case_id: UUID,
    evidence_id: UUID,
    body: CustodyTransferRequest,
) -> dict:
    """Registra una transferencia como evento inmutable y encadenado de auditoría."""
    _case_or_404(case_id)
    try:
        event = forensics_service.record_custody_transfer(
            case_id=str(case_id),
            evidence_id=str(evidence_id),
            **body.model_dump(),
        )
    except forensics_service.ForensicConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if event is None:
        raise HTTPException(status_code=404, detail="No se encontró el elemento de evidencia del caso.")
    return event


@router.post("/api/forensics/cases/{case_id}/evidence/{evidence_id}/verify-hash")
def verify_forensic_evidence_hash(
    case_id: UUID,
    evidence_id: UUID,
    body: EvidenceHashCheckRequest,
) -> dict:
    """Compara SHA-256 de una copia de trabajo con el valor declarado por la fuente."""
    _case_or_404(case_id)
    try:
        result = forensics_service.verify_evidence_copy(
            case_id=str(case_id),
            evidence_id=str(evidence_id),
            source_name=body.source_name,
            actor=body.actor,
            confirm_working_copy=body.confirm_working_copy,
        )
    except forensics_service.ForensicConflictError as exc:
        # El estado de la operación determina el conflicto; el texto solo explica el motivo.
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except forensics_service.ForensicHashCheckError as exc:
        # El servicio registra el intento fallido sin persistir la ruta completa.
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el elemento de evidencia del caso.")
    return result


@router.get("/api/forensics/cases/{case_id}/evidence/{evidence_id}/integrity-checks")
def get_forensic_integrity_checks(case_id: UUID, evidence_id: UUID) -> dict:
    """Lista verificaciones de integridad anteriores sin mostrar rutas completas."""
    _case_or_404(case_id)
    items = forensics_service.list_integrity_checks(
        case_id=str(case_id),
        evidence_id=str(evidence_id),
    )
    if items is None:
        raise HTTPException(status_code=404, detail="No se encontró el elemento de evidencia del caso.")
    return {"items": items}


@router.get("/api/forensics/cases/{case_id}/audit")
def get_forensic_audit(
    case_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """Devuelve el historial de operaciones, más reciente primero."""
    _case_or_404(case_id)
    try:
        items = forensics_service.list_audit_events(case_id=str(case_id), limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if items is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    return {"items": items, "limit": limit}


@router.get("/api/forensics/cases/{case_id}/audit/manifest")
def export_forensic_audit_manifest(case_id: UUID) -> Response:
    """Descarga la auditoría completa como manifiesto JSON conservable fuera de SQLite."""
    manifest = forensics_service.export_audit_manifest(case_id=str(case_id))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    body = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-forensic-audit-manifest.json"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/api/forensics/cases/{case_id}/manifest")
def export_forensic_case_manifest(case_id: UUID) -> Response:
    """Descarga un expediente consolidado con metadatos, checks y auditoría."""
    manifest = forensics_service.export_case_manifest(case_id=str(case_id))
    if manifest is None:
        raise HTTPException(status_code=404, detail="No se encontró el caso solicitado.")
    body = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-forensic-case-manifest.json"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
