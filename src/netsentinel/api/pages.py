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


@router.get("/guided-test", include_in_schema=False)
def guided_test_page() -> FileResponse:
    """Muestra el recorrido de validación manual con escenarios sintéticos."""
    return FileResponse(_STATIC_DIR / "guided-test.html")


@router.get("/world-map", include_in_schema=False)
def world_map_page() -> FileResponse:
    """Muestra el mapa mundial de IP públicas incluidas en eventos locales."""
    return FileResponse(_STATIC_DIR / "geolocation.html")


@router.get("/forensics", include_in_schema=False)
def forensics_page() -> FileResponse:
    """Muestra el punto de entrada de NetSentinel Forense."""
    return FileResponse(_STATIC_DIR / "forensics.html")

