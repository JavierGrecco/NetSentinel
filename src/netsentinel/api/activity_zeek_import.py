"""Rutas HTTP para previsualizar e importar un archivo Zeek conn.log."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import activity_tracking
from .activity_models import ActivityZeekImport

router = APIRouter(tags=["activity"])


@router.post("/api/activity/import/zeek/preview")
def preview_zeek_activity(body: ActivityZeekImport) -> dict:
    """Valida un archivo Zeek y estima duplicados sin guardar eventos."""
    try:
        return activity_tracking.preview_zeek_log(body.device_id, body.log_data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/activity/import/zeek")
def import_zeek_activity(body: ActivityZeekImport) -> dict:
    """Importa explícitamente metadatos de conexión exportados desde Zeek."""
    try:
        return activity_tracking.import_zeek_log(body.device_id, body.log_data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
