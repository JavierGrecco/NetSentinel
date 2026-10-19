"""Servicio de consulta de topología sobre las lecturas guardadas.

Reutiliza la fachada de persistencia existente y deja la construcción del modelo
en una función pura. No crea lecturas ni ejecuta descubrimientos.
"""
from __future__ import annotations

from pathlib import Path

from . import database
from .topology_model import TopologyModel, build_topology_model


def load_topology_for_scan(
    scan_id: int,
    path: Path | None = None,
) -> TopologyModel:
    """Carga una lectura concreta y proyecta únicamente su evidencia guardada.

    El argumento path se usa en pruebas y herramientas locales que necesitan
    una base explícita. En la aplicación normal, la fachada de base de datos
    resuelve la ubicación configurada por NetSentinel.
    """
    if isinstance(scan_id, bool) or not isinstance(scan_id, int) or scan_id < 1:
        return build_topology_model(None, None)

    scan = database.get_scan_by_id(scan_id, path=path)
    if scan is None:
        return TopologyModel(
            scan_id=None,
            captured_at=None,
            evidence_available=False,
            warnings=("No se encontró la lectura solicitada.",),
        )

    observations = database.get_scan_observations(scan_id, path=path)
    return build_topology_model(scan, observations)
