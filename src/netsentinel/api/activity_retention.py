"""Ruta HTTP para configurar la retención de actividad."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import activity_tracking
from .activity_models import ActivityRetentionUpdate

router = APIRouter(tags=["activity"])


@router.put("/api/activity/retention")
def set_family_activity_retention(body: ActivityRetentionUpdate) -> dict:
    """Actualiza la política local de retención."""
    try:
        return activity_tracking.update_retention(body.retention_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
