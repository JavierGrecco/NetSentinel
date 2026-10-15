"""Descargas de inventario, copia SQLite y exportación de datos."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from .. import database

router = APIRouter()


@router.get("/api/export/devices.csv")
def export_devices_csv() -> Response:
    return Response(
        content=database.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-devices.csv"', "Cache-Control": "no-store"},
    )


@router.get("/api/export/backup.sqlite3")
def export_sqlite_backup() -> Response:
    return Response(
        content=database.export_sqlite_backup(),
        media_type="application/vnd.sqlite3",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-backup.sqlite3"', "Cache-Control": "no-store"},
    )


@router.get("/api/export/data.json")
def export_data_json() -> Response:
    return Response(
        content=database.export_json(),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-export.json"', "Cache-Control": "no-store"},
    )
