"""Rutas HTTP de consulta y exportación de actividad."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response

from .. import activity_tracking

router = APIRouter(tags=["activity"])


@router.get("/api/activity")
def get_family_activity(
    device_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None, max_length=32),
    from_date: str | None = Query(default=None, min_length=10, max_length=10),
    to_date: str | None = Query(default=None, min_length=10, max_length=10),
    source_event_id: str | None = Query(default=None, max_length=180),
    import_format: str | None = Query(default=None, max_length=32),
) -> dict:
    """Devuelve sesiones y metadatos, aplicando filtros solo a la lista de eventos."""
    try:
        return activity_tracking.get_activity(
            device_id=device_id, limit=limit, event_type=event_type, source=source,
            from_date=from_date, to_date=to_date, source_event_id=source_event_id,
            import_format=import_format,
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
    source_event_id: str | None = Query(default=None, max_length=180),
    import_format: str | None = Query(default=None, max_length=32),
) -> Response:
    """Exporta metadatos filtrados sin fórmulas activas en texto CSV."""
    try:
        content = activity_tracking.export_activity_csv(
            device_id=device_id, event_type=event_type, source=source,
            from_date=from_date, to_date=to_date, limit=limit,
            source_event_id=source_event_id,
            import_format=import_format,
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
