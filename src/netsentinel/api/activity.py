"""Rutas HTTP para las sesiones y los metadatos de actividad autorizada.

Este módulo define esquemas de entrada y traduce errores del servicio a respuestas
HTTP. Las reglas de privacidad, normalización, retención y almacenamiento viven en
activity_tracking; este router no accede a SQLite directamente.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from .. import activity_tracking

router = APIRouter(tags=["activity"])


class ActivitySessionCreate(BaseModel):
    device_id: int = Field(ge=1)
    duration_minutes: int = Field(default=60, ge=5, le=720)
    source_mode: str = Field(min_length=1, max_length=32)


class ActivityEventIngest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: int = Field(ge=1)
    collector_token: str = Field(min_length=32, max_length=128)
    device_id: int = Field(ge=1)
    event_type: str = Field(min_length=1, max_length=32)
    source: str = Field(min_length=1, max_length=32)
    observed_at: str | None = Field(default=None, max_length=64)
    domain: str | None = Field(default=None, max_length=253)
    destination_ip: str | None = Field(default=None, max_length=64)
    destination_port: int | None = Field(default=None, ge=1, le=65535, strict=True)
    protocol: str | None = Field(default=None, max_length=16)
    app_name: str | None = Field(default=None, max_length=100)
    page_url: str | None = Field(default=None, max_length=4096)
    search_engine: str | None = Field(default=None, max_length=40)
    search_terms: str | None = Field(default=None, max_length=500)
    email_provider: str | None = Field(default=None, max_length=60)
    email_from: str | None = Field(default=None, max_length=1500)
    email_to: str | None = Field(default=None, max_length=1500)
    email_subject: str | None = Field(default=None, max_length=200)
    blocked: bool = False


class ActivityCSVImport(BaseModel):
    device_id: int = Field(ge=1)
    csv_data: str = Field(min_length=1, max_length=1_000_000)


class ActivityRetentionUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=90, strict=True)


class ActivityDeleteSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: int | None = Field(default=None, ge=1)
    event_type: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, max_length=32)
    from_date: str | None = Field(default=None, min_length=10, max_length=10)
    to_date: str | None = Field(default=None, min_length=10, max_length=10)


class ActivityDeleteRequest(ActivityDeleteSelection):
    confirmation: str = Field(min_length=1, max_length=40)


@router.get("/api/activity")
def get_family_activity(
    device_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=32),
    from_date: str | None = Query(default=None, min_length=10, max_length=10),
    to_date: str | None = Query(default=None, min_length=10, max_length=10),
) -> dict:
    """Devuelve sesiones y metadatos, aplicando filtros solo a la lista de eventos."""
    try:
        return activity_tracking.get_activity(
            device_id=device_id, limit=limit, event_type=event_type, source=source,
            from_date=from_date, to_date=to_date,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/activity/export.csv")
def export_family_activity_csv(
    device_id: int | None = Query(default=None, ge=1),
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=32),
    from_date: str | None = Query(default=None, min_length=10, max_length=10),
    to_date: str | None = Query(default=None, min_length=10, max_length=10),
    limit: int = Query(default=10000, ge=1, le=10000),
) -> Response:
    """Exporta metadatos filtrados sin fórmulas activas en texto CSV."""
    try:
        content = activity_tracking.export_activity_csv(
            device_id=device_id, event_type=event_type, source=source,
            from_date=from_date, to_date=to_date, limit=limit,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-activity.csv"',
            "Cache-Control": "no-store",
        },
    )


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


@router.put("/api/activity/retention")
def set_family_activity_retention(body: ActivityRetentionUpdate) -> dict:
    try:
        return activity_tracking.update_retention(body.retention_days)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
