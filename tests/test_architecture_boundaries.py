"""Comprueba que las fronteras iniciales de la API modular se mantienen claras."""
from __future__ import annotations

from pathlib import Path

from netsentinel.api import activity, findings, inventory, monitoring, pages, tools
from netsentinel.discovery import Neighbor as DiscoveryNeighbor
from netsentinel.network_models import Neighbor
from netsentinel import database
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
        "netsentinel.api.security",
        "netsentinel.dns_config",
        "netsentinel.dns_tools",
        "netsentinel.tls_tools",
    }
    assert graph["netsentinel.api.security"] == set()
    assert graph["netsentinel.api.error_handling"] == {
        "netsentinel.api.security",
        "netsentinel.error_reporting",
    }
    assert graph["netsentinel.api.activity"] == {"netsentinel.activity_tracking"}
    assert graph["netsentinel.api.findings"] == {"netsentinel.findings_service"}
    assert graph["netsentinel.findings_service"] == {"netsentinel.database", "netsentinel.findings"}
    assert graph["netsentinel.activity_repository"] == {
        "netsentinel.database",
        "netsentinel.activity_deletion_repository",
        "netsentinel.activity_import_repository",
        "netsentinel.activity_read_repository",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
        "netsentinel.activity_session_repository",
    }
    assert graph["netsentinel.activity_repository_support"] == {"netsentinel.database"}
    assert graph["netsentinel.activity_retention_repository"] == {"netsentinel.database"}
    assert graph["netsentinel.activity_session_repository"] == set()
    assert graph["netsentinel.activity_import_repository"] == {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
    }
    assert graph["netsentinel.activity_deletion_repository"] == {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
    }
    assert graph["netsentinel.activity_read_repository"] == {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
    }
    assert "netsentinel.activity_repository" not in graph["netsentinel.activity_tracking"]
    assert "netsentinel.database" not in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_retention_service"] == {"netsentinel.activity_repository"}
    assert "netsentinel.activity_event_service" in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_event_service"] == {
        "netsentinel.activity_catalog",
        "netsentinel.activity_privacy",
    }
    assert "netsentinel.activity_deletion_service" in graph["netsentinel.activity_tracking"]
    assert "netsentinel.activity_session_service" in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_deletion_service"] == {
        "netsentinel.activity_filters",
        "netsentinel.activity_repository",
    }
    assert graph["netsentinel.activity_session_service"] == {
        "netsentinel.activity_catalog",
        "netsentinel.activity_event_service",
        "netsentinel.activity_repository",
        "netsentinel.activity_retention_service",
        "netsentinel.database",
    }
    assert "netsentinel.activity_import_service" in graph["netsentinel.activity_tracking"]
    assert "netsentinel.activity_read_service" in graph["netsentinel.activity_tracking"]
    assert graph["netsentinel.activity_catalog"] == set()
    assert graph["netsentinel.activity_filters"] == {"netsentinel.activity_catalog"}
    assert graph["netsentinel.activity_read_service"] == {
        "netsentinel.activity_catalog",
        "netsentinel.activity_filters",
        "netsentinel.activity_repository",
        "netsentinel.csv_safety",
    }
    assert graph["netsentinel.activity_import_service"] == {"netsentinel.activity_repository"}
    assert graph["netsentinel.activity_event_service"] == {
        "netsentinel.activity_catalog",
        "netsentinel.activity_privacy",
    }
    assert graph["netsentinel.activity_privacy"] == set()
    assert graph["netsentinel.database"] == {
        "netsentinel.config",
        "netsentinel.database_storage",
        "netsentinel.database_schema",
        "netsentinel.network_models",
        "netsentinel.events_repository",
        "netsentinel.inventory_repository",
        "netsentinel.dashboard_repository",
        "netsentinel.data_export_service",
        "netsentinel.monitoring_repository",
        "netsentinel.monitoring_export_service",
    }
    assert graph["netsentinel.database_storage"] == {"netsentinel.config"}
    assert graph["netsentinel.database_schema"] == {"netsentinel.database_storage"}
    assert graph["netsentinel.inventory_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
        "netsentinel.network_models",
        "netsentinel.vendor",
    }
    assert graph["netsentinel.events_repository"] == {"netsentinel.database_storage"}
    assert graph["netsentinel.dashboard_repository"] == {"netsentinel.database_storage"}
    assert graph["netsentinel.monitoring_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
    }
    assert graph["netsentinel.data_export_service"] == {
        "netsentinel.config",
        "netsentinel.csv_safety",
        "netsentinel.database_storage",
        "netsentinel.inventory_repository",
    }
    assert graph["netsentinel.monitoring_export_service"] == {
        "netsentinel.csv_safety",
        "netsentinel.monitoring_repository",
    }
    assert "netsentinel.discovery" not in graph["netsentinel.database"]



def test_monitoring_is_split_into_validation_probe_and_notification_adapters() -> None:
    """La validación pura no importa SQLite ni los adaptadores que producen efectos."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\\n".join(violations)
    assert graph["netsentinel.monitoring"] >= {
        "netsentinel.monitoring_validation",
        "netsentinel.monitoring_probe",
        "netsentinel.monitoring_notifications",
    }
    assert graph["netsentinel.monitoring_validation"] == set()
    assert graph["netsentinel.monitoring_notifications"] == {"netsentinel.monitoring_probe"}
    assert "netsentinel.database" not in graph["netsentinel.monitoring_validation"]
    assert "netsentinel.database" not in graph["netsentinel.monitoring_probe"]

def test_database_facade_keeps_existing_public_operations() -> None:
    """La API interna histórica sigue disponible tras dividir los repositorios."""
    for operation in (
        "connect", "initialize", "list_devices", "get_device_history",
        "record_scan", "get_events", "get_summary", "export_json",
        "export_csv", "export_sqlite_backup", "create_monitor",
        "record_monitor_check", "get_monitor_latency_trend", "get_incidents",
        "export_monitoring_csv",
    ):
        assert callable(getattr(database, operation, None)), operation

def test_neighbor_type_is_shared_but_old_import_path_still_works() -> None:
    """El tipo compartido conserva compatibilidad con el módulo de descubrimiento."""
    assert DiscoveryNeighbor is Neighbor


def test_domain_and_persistence_modules_do_not_import_http_frameworks() -> None:
    """Los módulos que contienen reglas/datos no dependen de FastAPI o Starlette."""
    package_root = Path(__file__).resolve().parents[1] / "src" / "netsentinel"
    expected = {
        "database.py",
        "database_storage.py",
        "database_schema.py",
        "inventory_repository.py",
        "events_repository.py",
        "dashboard_repository.py",
        "monitoring_repository.py",
        "monitoring_validation.py",
        "monitoring_probe.py",
        "monitoring_notifications.py",
        "data_export_service.py",
        "monitoring_export_service.py",
        "discovery.py",
        "findings.py",
        "monitoring.py",
        "activity_tracking.py",
        "activity_deletion_service.py",
        "activity_session_service.py",
        "activity_retention_service.py",
        "activity_event_service.py",
        "activity_import_service.py",
        "activity_privacy.py",
        "activity_catalog.py",
        "activity_filters.py",
        "activity_read_service.py",
        "activity_repository.py",
        "activity_repository_support.py",
        "activity_retention_repository.py",
        "activity_session_repository.py",
        "activity_import_repository.py",
        "activity_deletion_repository.py",
        "activity_read_repository.py",
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
