"""Comprueba que las fronteras iniciales de la API modular se mantienen claras."""
from __future__ import annotations

from pathlib import Path

from netsentinel.api import activity, findings, inventory, monitoring, pages, tools
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
    assert graph["netsentinel.api.findings"] == {"netsentinel.findings_service"}
    assert graph["netsentinel.findings_service"] == {"netsentinel.database", "netsentinel.findings"}
    assert graph["netsentinel.activity_repository"] == {"netsentinel.database"}
    assert "netsentinel.activity_repository" in graph["netsentinel.activity_tracking"]
    assert "netsentinel.activity_import_service" in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_import_service"] == {"netsentinel.activity_repository"}
    assert "netsentinel.activity_privacy" in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_privacy"] == set()
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
        "activity_import_service.py",
        "activity_privacy.py",
        "activity_repository.py",
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


def test_findings_endpoints_belong_to_findings_router() -> None:
    """Las rutas de hallazgos viven en su capacidad funcional, no en main.py."""
    paths = {route.path for route in findings.router.routes}
    assert {"/api/findings", "/api/export/findings.json"} <= paths


def _write_minimal_package(root: Path) -> Path:
    """Crea un paquete pequeño para probar que las reglas cubren módulos nuevos."""
    package = root / "src" / "netsentinel"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "main.py").write_text(
        '"""Punto de composición de prueba."""\n', encoding="utf-8"
    )
    return package


def test_new_domain_module_is_checked_for_http_framework_imports(tmp_path: Path) -> None:
    package = _write_minimal_package(tmp_path)
    (package / "future_service.py").write_text(
        "from fastapi import FastAPI\n", encoding="utf-8"
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.future_service imports the HTTP framework" in violation
        for violation in violations
    )


def test_new_service_must_declare_its_internal_dependencies(tmp_path: Path) -> None:
    package = _write_minimal_package(tmp_path)
    (package / "network_models.py").write_text("Neighbor = object\n", encoding="utf-8")
    (package / "future_service.py").write_text(
        "from . import network_models\n", encoding="utf-8"
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.future_service has internal dependencies but no explicit service allow-list"
        in violation
        for violation in violations
    )


def test_database_cannot_import_a_new_domain_module_by_default(tmp_path: Path) -> None:
    package = _write_minimal_package(tmp_path)
    (package / "network_models.py").write_text("Neighbor = object\n", encoding="utf-8")
    (package / "future_domain.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "database.py").write_text(
        "from . import future_domain\n", encoding="utf-8"
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.database imports netsentinel.future_domain, which is not an allowed persistence dependency"
        in violation
        for violation in violations
    )


def test_new_repository_must_declare_its_internal_dependencies(tmp_path: Path) -> None:
    package = _write_minimal_package(tmp_path)
    (package / "network_models.py").write_text("Neighbor = object\n", encoding="utf-8")
    (package / "future_repository.py").write_text(
        "from . import network_models\n", encoding="utf-8"
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.future_repository has internal dependencies but no explicit repository allow-list"
        in violation
        for violation in violations
    )


def test_inventory_endpoints_belong_to_inventory_router() -> None:
    """Las rutas de inventario se registran desde el módulo funcional propio."""
    paths = {route.path for route in inventory.router.routes}
    assert {
        "/api/health",
        "/api/summary",
        "/api/devices",
        "/api/events",
        "/api/scans",
        "/api/devices/{device_id}/history",
        "/api/devices/{device_id}/addresses",
        "/api/scan",
        "/api/devices/{device_id}/dns-reverse",
        "/api/devices/{device_id}",
        "/api/events/{event_id}",
        "/api/export/devices.csv",
        "/api/export/backup.sqlite3",
        "/api/export/data.json",
    } <= paths
    assert len(paths) == 14


def test_inventory_router_has_only_declared_internal_dependencies() -> None:
    """El router no obtiene acceso implícito a otros dominios."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.inventory"] == {
        "netsentinel.database",
        "netsentinel.local_discovery",
        "netsentinel.dns_tools",
    }



def test_monitoring_endpoints_belong_to_monitoring_router() -> None:
    """Las rutas de monitores, incidentes y diagnóstico viven en su router."""
    routes = monitoring.router.routes
    paths = {route.path for route in routes}
    assert {
        "/api/monitors",
        "/api/monitoring/summary",
        "/api/export/monitoring.csv",
        "/api/export/incidents.csv",
        "/api/monitors/{monitor_id}/latency",
        "/api/export/monitor-latency.csv",
        "/api/monitors/{monitor_id}",
        "/api/monitors/{monitor_id}/check",
        "/api/monitors/{monitor_id}/checks",
        "/api/incidents",
        "/api/notifications",
        "/api/diagnostics",
    } <= paths
    assert len(routes) == 14
    # Two paths intentionally serve more than one HTTP method.
    assert len(paths) == 12


def test_monitoring_router_has_only_declared_internal_dependencies() -> None:
    """El router de monitorización se limita a persistencia y servicios de dominio."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.monitoring"] == {
        "netsentinel.database",
        "netsentinel.diagnostics",
        "netsentinel.monitoring",
    }



def test_html_pages_belong_to_pages_router() -> None:
    """Las cinco páginas HTML se sirven desde su router dedicado."""
    paths = {route.path for route in pages.router.routes}
    assert paths == {"/", "/monitors", "/activity", "/findings", "/tools"}
    assert all(not route.include_in_schema for route in pages.router.routes)


def test_pages_router_has_no_internal_domain_dependencies() -> None:
    """El router de páginas solo selecciona recursos HTML empaquetados."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\\n".join(violations)
    assert graph["netsentinel.api.pages"] == set()
