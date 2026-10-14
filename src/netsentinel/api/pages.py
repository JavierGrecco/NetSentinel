"""Rutas que sirven las páginas HTML locales de NetSentinel.

La política CSP y las cabeceras se aplican mediante el middleware de la app,
mientras que este router solo selecciona el archivo estático correspondiente.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter()
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/monitors", include_in_schema=False)
def monitors_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "monitors.html")


@router.get("/activity", include_in_schema=False)
def activity_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "activity.html")


@router.get("/findings", include_in_schema=False)
def findings_page() -> FileResponse:
    """Muestra la bandeja local de hallazgos con evidencia."""
    return FileResponse(_STATIC_DIR / "findings.html")


@router.get("/tools", include_in_schema=False)
def tools_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "tools.html")
