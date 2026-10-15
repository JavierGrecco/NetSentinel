"""Rutas HTTP para iniciar sesiones e ingresar metadatos autorizados."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import activity_tracking
from .activity_models import ActivityEventIngest, ActivitySessionCreate

router = APIRouter(tags=["activity"])


@router.post("/api/activity/sessions")
def start_family_activity(body: ActivitySessionCreate) -> dict:
    """Abre una ventana temporal explícita para la fuente de metadatos elegida."""
    try:
        return activity_tracking.start_session(body.device_id, body.duration_minutes, body.source_mode)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/activity/sessions/{session_id}/stop")
def stop_family_activity(session_id: int) -> dict:
    """Cierra una sesión y devuelve 404 si no existe."""
    result = activity_tracking.stop_session(session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró la sesión.")
    return result


@router.post("/api/activity/ingest")
def ingest_family_activity(body: ActivityEventIngest) -> dict:
    """Guarda metadatos limitados solo durante una sesión activa."""
    try:
        return activity_tracking.ingest_event(
            body.session_id, body.device_id, body.collector_token, body.model_dump(exclude={"collector_token"})
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except activity_tracking.InvalidCollectorToken as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
