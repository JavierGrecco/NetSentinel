"""Rutas HTTP para consultar y exportar hallazgos con evidencia."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..findings_service import collect_findings_report

router = APIRouter(tags=["findings"])


def _report_or_http_error(state: str, limit: int) -> dict:
    """Convierte errores de entrada del servicio en respuestas HTTP estables."""
    try:
        return collect_findings_report(state, limit)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/findings")
def get_findings(
    state: str = Query(default="active", max_length=20),
    limit: int = Query(default=100, ge=1, le=200),
) -> dict:
    """Devuelve una vista unificada y acotada de hallazgos y su evidencia."""
    return _report_or_http_error(state, limit)


@router.get("/api/export/findings.json")
def export_findings_json(
    state: str = Query(default="active", max_length=20),
    limit: int = Query(default=100, ge=1, le=200),
) -> JSONResponse:
    """Exporta hallazgos sin modificar el historial."""
    report = _report_or_http_error(state, limit)
    return JSONResponse(
        content=report,
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-findings.json"',
            "Cache-Control": "no-store",
        },
    )
