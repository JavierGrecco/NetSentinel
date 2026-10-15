"""Rutas HTTP para previsualizar y confirmar el borrado selectivo."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import activity_tracking
from .activity_models import ActivityDeleteRequest, ActivityDeleteSelection

router = APIRouter(tags=["activity"])


@router.post("/api/activity/delete/preview")
def preview_family_activity_delete(body: ActivityDeleteSelection) -> dict:
    """Cuenta el alcance elegido sin borrar registros."""
    try:
        return activity_tracking.preview_delete_activity(**body.model_dump())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/activity/delete")
def delete_family_activity(body: ActivityDeleteRequest) -> dict:
    """Borra exclusivamente el alcance acotado y confirmado por el operador."""
    try:
        return activity_tracking.delete_activity(
            device_id=body.device_id,
            event_type=body.event_type,
            from_date=body.from_date,
            to_date=body.to_date,
            confirmation=body.confirmation,
            source=body.source,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
