"""Rutas HTTP para previsualizar e importar CSV de actividad."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import activity_tracking
from .activity_models import ActivityCSVImport

router = APIRouter(tags=["activity"])


@router.post("/api/activity/import/preview")
def preview_family_activity(body: ActivityCSVImport) -> dict:
    """Valida y devuelve una muestra CSV sin guardar los eventos."""
    try:
        return activity_tracking.preview_csv(body.device_id, body.csv_data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/activity/import")
def import_family_activity(body: ActivityCSVImport) -> dict:
    """Importa explícitamente un CSV de metadatos desde el equipo local."""
    try:
        return activity_tracking.import_csv(body.device_id, body.csv_data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
