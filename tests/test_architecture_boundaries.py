"""Comprueba que las fronteras iniciales de la API modular se mantienen claras."""
from __future__ import annotations

from pathlib import Path

from netsentinel.api import activity, tools
from netsentinel.discovery import Neighbor as DiscoveryNeighbor
from netsentinel.network_models import Neighbor
from scripts.check_architecture_boundaries import check_architecture


def test_dns_tls_endpoints_belong_to_tools_router() -> None:
    """La composición debe registrar estos endpoints desde su módulo funcional."""
    paths = {route.path for route in tools.router.routes}
    assert {
        "/api/tools/tls/inspect",
        "/api/tools/dns/configuration",
        "/api/tools/dns/lookup",
        "/api/tools/dns/reverse",
    } <= paths


def test_architecture_policy_passes_without_coupling_violations() -> None:
    """La política completa se ejecuta también como parte de las pruebas."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.tools"] == {
        "netsentinel.dns_config",
        "netsentinel.dns_tools",
        "netsentinel.tls_tools",
    }
    assert graph["netsentinel.api.activity"] == {"netsentinel.activity_tracking"}
    assert "netsentinel.network_models" in graph["netsentinel.database"]
    assert "netsentinel.discovery" not in graph["netsentinel.database"]


def test_neighbor_type_is_shared_but_old_import_path_still_works() -> None:
    """El tipo compartido conserva compatibilidad con el módulo de descubrimiento."""
    assert DiscoveryNeighbor is Neighbor


def test_domain_and_persistence_modules_do_not_import_http_frameworks() -> None:
    """Los módulos que contienen reglas/datos no dependen de FastAPI o Starlette."""
    package_root = Path(__file__).resolve().parents[1] / "src" / "netsentinel"
    expected = {
        "database.py",
        "discovery.py",
        "findings.py",
        "monitoring.py",
        "activity_tracking.py",
        "network_models.py",
    }
    for name in expected:
        source = (package_root / name).read_text(encoding="utf-8")
        assert "from fastapi " not in source
        assert "import fastapi" not in source
        assert "from starlette " not in source
        assert "import starlette" not in source


def test_activity_endpoints_belong_to_activity_router() -> None:
    """La capacidad de actividad expone su API desde el módulo correspondiente."""
    paths = {route.path for route in activity.router.routes}
    assert {
        "/api/activity",
        "/api/activity/export.csv",
        "/api/activity/sessions",
        "/api/activity/sessions/{session_id}/stop",
        "/api/activity/ingest",
        "/api/activity/import/preview",
        "/api/activity/import",
        "/api/activity/delete/preview",
        "/api/activity/delete",
        "/api/activity/retention",
    } <= paths
