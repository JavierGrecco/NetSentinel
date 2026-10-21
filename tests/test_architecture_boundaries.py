"""Comprueba que las fronteras iniciales de la API modular se mantienen claras."""
from __future__ import annotations

from pathlib import Path

from netsentinel.api import (
    activity,
    activity_deletion as activity_deletion_api,
    activity_import as activity_import_api,
    activity_models,
    activity_read as activity_read_api,
    activity_retention as activity_retention_api,
    activity_sessions as activity_sessions_api,
    diagnostics as diagnostics_api,
    error_handling as error_handling_api,
    validation_errors,
    findings,
    forensics,
    inventory,
    inventory_assets,
    inventory_discovery,
    inventory_exports,
    monitoring,
    monitoring_monitors,
    monitoring_reports,
    pages,
    security as security_api,
    security_headers,
    tools,
    tools_dns,
    tools_tls,
)
from netsentinel.discovery import Neighbor as DiscoveryNeighbor
from netsentinel.network_models import Neighbor
from netsentinel import (
    database,
    inventory_read_repository,
    inventory_repository as inventory_repository_compat,
    inventory_repository_support,
    monitoring_analytics_repository,
    monitoring_config_repository,
    monitoring_notifications_repository,
    monitoring_repository as monitoring_repository_compat,
    monitoring_state_repository,
)
from scripts.check_architecture_boundaries import check_architecture


def test_dns_tls_endpoints_belong_to_their_capability_routers() -> None:
    """Cada grupo de rutas tiene un módulo dueño y conserva sus rutas públicas."""
    dns_paths = {route.path for route in tools_dns.router.routes}
    assert dns_paths == {
        "/api/tools/dns/configuration",
        "/api/tools/dns/lookup",
        "/api/tools/dns/reverse",
    }
    tls_paths = {route.path for route in tools_tls.router.routes}
    assert tls_paths == {"/api/tools/tls/inspect"}


def test_architecture_policy_passes_without_coupling_violations() -> None:
    """La política completa se ejecuta también como parte de las pruebas."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.tools"] == {
        "netsentinel.api.tools_dns",
        "netsentinel.api.tools_tls",
    }
    assert graph["netsentinel.api.tools_dns"] == {
        "netsentinel.dns_config",
        "netsentinel.dns_tools",
    }
    assert graph["netsentinel.api.tools_tls"] == {"netsentinel.tls_tools"}
    assert graph["netsentinel.api.security"] == {"netsentinel.api.security_headers"}
    assert graph["netsentinel.api.security_headers"] == set()
    assert graph["netsentinel.api.error_handling"] == {
        "netsentinel.api.security",
        "netsentinel.api.validation_errors",
        "netsentinel.error_reporting",
    }
    assert graph["netsentinel.api.validation_errors"] == {
        "netsentinel.api.security_headers",
    }
    assert graph["netsentinel.api.activity"] == {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_deletion",
        "netsentinel.api.activity_import",
        "netsentinel.api.activity_models",
        "netsentinel.api.activity_read",
        "netsentinel.api.activity_retention",
        "netsentinel.api.activity_sessions",
    }
    assert graph["netsentinel.api.activity_models"] == set()
    assert graph["netsentinel.api.activity_read"] == {"netsentinel.activity_tracking"}
    assert graph["netsentinel.api.activity_sessions"] == {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    }
    assert graph["netsentinel.api.activity_import"] == {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    }
    assert graph["netsentinel.api.activity_deletion"] == {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    }
    assert graph["netsentinel.api.activity_retention"] == {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    }
    assert graph["netsentinel.api.findings"] == {"netsentinel.findings_service"}
    assert graph["netsentinel.api.forensics"] == {"netsentinel.forensics_service"}
    assert graph["netsentinel.forensics_service"] == {
        "netsentinel.config",
        "netsentinel.forensics_audit_manifest",
        "netsentinel.forensics_case_manifest",
        "netsentinel.forensics_errors",
        "netsentinel.forensics_integrity",
        "netsentinel.forensics_repository",
    }
    assert graph["netsentinel.forensics_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.forensics_audit_integrity",
        "netsentinel.forensics_audit_manifest",
        "netsentinel.forensics_errors",
    }
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
    assert graph["netsentinel.activity_tracking"] == {
        "netsentinel.activity_catalog",
        "netsentinel.activity_deletion_service",
        "netsentinel.activity_event_service",
        "netsentinel.activity_filters",
        "netsentinel.activity_import_service",
        "netsentinel.activity_privacy",
        "netsentinel.activity_read_service",
        "netsentinel.activity_retention_service",
        "netsentinel.activity_session_service",
    }
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
    assert graph["netsentinel.database_schema"] == {"netsentinel.database_storage", "netsentinel.forensics_audit_integrity"}
    assert graph["netsentinel.inventory_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
        "netsentinel.inventory_read_repository",
        "netsentinel.inventory_repository_support",
        "netsentinel.network_models",
        "netsentinel.vendor",
    }
    assert graph["netsentinel.inventory_read_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.inventory_repository_support",
    }
    assert graph["netsentinel.inventory_repository_support"] == set()
    assert graph["netsentinel.events_repository"] == {"netsentinel.database_storage"}
    assert graph["netsentinel.dashboard_repository"] == {"netsentinel.database_storage"}
    assert graph["netsentinel.monitoring_repository"] == {
        "netsentinel.monitoring_analytics_repository",
        "netsentinel.monitoring_config_repository",
        "netsentinel.monitoring_notifications_repository",
        "netsentinel.monitoring_state_repository",
    }
    assert graph["netsentinel.monitoring_config_repository"] == {
        "netsentinel.database_storage",
    }
    assert graph["netsentinel.monitoring_analytics_repository"] == {
        "netsentinel.database_storage",
    }
    assert graph["netsentinel.monitoring_state_repository"] == {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
    }
    assert graph["netsentinel.monitoring_notifications_repository"] == {
        "netsentinel.database_storage",
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

def test_diagnostic_assessment_is_pure_and_separated_from_os_commands() -> None:
    """El resumen del diagnóstico no depende de comandos ni de persistencia."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\\n".join(violations)
    assert graph["netsentinel.diagnostics_assessment"] == set()
    assert graph["netsentinel.diagnostics"] == {
        "netsentinel.diagnostics_assessment",
        "netsentinel.error_reporting",
    }
    assert graph["netsentinel.error_reporting"] == {"netsentinel.error_journal"}
    assert graph["netsentinel.error_journal"] == {"netsentinel.config"}

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
        "diagnostics.py",
        "diagnostics_assessment.py",
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
        "error_reporting.py",
        "error_journal.py",
        "forensics_integrity.py",
        "forensics_service.py",
        "forensics_repository.py",
        "forensics_audit_integrity.py",
        "forensics_case_manifest.py",
    }
    for name in expected:
        source = (package_root / name).read_text(encoding="utf-8")
        assert "from fastapi " not in source
        assert "import fastapi" not in source
        assert "from starlette " not in source
        assert "import starlette" not in source


def test_activity_endpoints_belong_to_their_responsibility_routers() -> None:
    """Cada flujo de actividad tiene un router dueño y conserva las rutas públicas."""
    route_groups = (
        activity_read_api.router.routes,
        activity_sessions_api.router.routes,
        activity_import_api.router.routes,
        activity_deletion_api.router.routes,
        activity_retention_api.router.routes,
    )
    paths = {route.path for routes in route_groups for route in routes}
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
    assert sum(len(routes) for routes in route_groups) == 10
    assert len(paths) == 10


def test_activity_models_remain_available_from_the_historical_module() -> None:
    """Los imports de modelos usados por consumidores existentes siguen funcionando."""
    assert activity.ActivityEventIngest is activity_models.ActivityEventIngest
    assert activity.ActivityRetentionUpdate is activity_models.ActivityRetentionUpdate
    assert callable(activity.get_family_activity)
    assert callable(activity.ingest_family_activity)
    assert callable(activity.import_family_activity)
    assert callable(activity.delete_family_activity)


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


def test_activity_tracking_facade_cannot_import_storage_directly(tmp_path: Path) -> None:
    """Una fachada no puede saltarse sus servicios e importar la persistencia."""
    package = _write_minimal_package(tmp_path)
    (package / "database.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "activity_tracking.py").write_text(
        "from . import database\n",
        encoding="utf-8",
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.activity_tracking imports netsentinel.database, "
        "which is not an allowed facade dependency."
        in violation
        for violation in violations
    )


def test_validation_handler_keeps_the_historical_import_path() -> None:
    """El punto de composición sigue exponiendo el manejador y el catálogo antiguos."""
    assert (
        error_handling_api.handle_request_validation_error
        is validation_errors.handle_request_validation_error
    )
    assert error_handling_api._safe_validation_message is validation_errors._safe_validation_message
    assert validation_errors._safe_validation_message("unrecognized_type") == (
        "El valor no cumple el formato esperado."
    )


def test_security_response_helpers_have_a_single_module_owner() -> None:
    """El middleware reexporta la interfaz histórica sin duplicar la lógica de respuestas."""
    assert security_api._apply_security_headers is security_headers._apply_security_headers
    assert security_api._error_response is security_headers._error_response
    assert security_api._base_content_security_policy is security_headers._base_content_security_policy


def test_duplicate_top_level_definitions_are_rejected(tmp_path: Path) -> None:
    """Una segunda función con el mismo nombre no debe ocultar código silenciosamente."""
    package = _write_minimal_package(tmp_path)
    (package / "future.py").write_text(
        "def handler():\n    return None\n\ndef handler():\n    return True\n",
        encoding="utf-8",
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.future defines top-level handler more than once" in violation
        for violation in violations
    )


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
    """Las rutas del inventario se distribuyen por consulta, descubrimiento y exportación."""
    route_groups = (
        inventory_assets.router.routes,
        inventory_discovery.router.routes,
        inventory_exports.router.routes,
    )
    paths = {route.path for routes in route_groups for route in routes}
    assert {
        "/api/health",
        "/api/summary",
        "/api/devices",
        "/api/events",
        "/api/scans",
        "/api/scans/compare",
        "/api/scans/{scan_id}/observations",
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
    assert sum(len(routes) for routes in route_groups) == 16
    assert len(paths) == 16
def test_inventory_router_has_only_declared_internal_dependencies() -> None:
    """El router no obtiene acceso implícito a otros dominios."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.inventory"] == {
        "netsentinel.api.inventory_assets",
        "netsentinel.api.inventory_discovery",
        "netsentinel.api.inventory_exports",
    }
    assert graph["netsentinel.api.inventory_assets"] == {
        "netsentinel.database",
        "netsentinel.dns_tools",
    }
    assert graph["netsentinel.api.inventory_discovery"] == {
        "netsentinel.database",
        "netsentinel.local_discovery",
    }
    assert graph["netsentinel.api.inventory_exports"] == {"netsentinel.database"}



def test_monitoring_endpoints_belong_to_monitoring_router() -> None:
    """Las rutas públicas se reparten entre los subrouters de monitorización."""
    # Las versiones recientes de FastAPI mantienen routers incluidos como objetos
    # internos; comprobar las rutas en cada router dueño evita depender de ese detalle.
    route_groups = (
        monitoring_monitors.router.routes,
        monitoring_reports.router.routes,
        diagnostics_api.router.routes,
    )
    paths = {route.path for routes in route_groups for route in routes}
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
    assert sum(len(routes) for routes in route_groups) == 14
    assert len(paths) == 12
def test_monitoring_routes_are_grouped_by_responsibility() -> None:
    """Los endpoints mantienen su contrato y pertenecen al router de su capacidad."""
    monitor_paths = {route.path for route in monitoring_monitors.router.routes}
    assert monitor_paths == {
        "/api/monitors",
        "/api/monitors/{monitor_id}",
        "/api/monitors/{monitor_id}/check",
        "/api/monitors/{monitor_id}/checks",
        "/api/incidents",
        "/api/notifications",
    }
    assert len(monitoring_monitors.router.routes) == 8

    report_paths = {route.path for route in monitoring_reports.router.routes}
    assert report_paths == {
        "/api/monitoring/summary",
        "/api/export/monitoring.csv",
        "/api/export/incidents.csv",
        "/api/monitors/{monitor_id}/latency",
        "/api/export/monitor-latency.csv",
    }
    assert len(monitoring_reports.router.routes) == 5
    assert {route.path for route in diagnostics_api.router.routes} == {"/api/diagnostics"}

def test_monitoring_router_has_only_declared_internal_dependencies() -> None:
    """El router de monitorización se limita a persistencia y servicios de dominio."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\n".join(violations)
    assert graph["netsentinel.api.monitoring"] == {
        "netsentinel.api.diagnostics",
        "netsentinel.api.monitoring_monitors",
        "netsentinel.api.monitoring_reports",
    }
    assert graph["netsentinel.api.monitoring_monitors"] == {
        "netsentinel.database",
        "netsentinel.monitoring",
    }
    assert graph["netsentinel.api.monitoring_reports"] == {"netsentinel.database"}
    assert graph["netsentinel.api.diagnostics"] == {"netsentinel.diagnostics"}



def test_inventory_repository_facade_keeps_read_and_write_imports_compatible() -> None:
    """Los exports históricos siguen disponibles aunque las lecturas estén separadas."""
    assert inventory_repository_compat.list_devices is inventory_read_repository.list_devices
    assert inventory_repository_compat.get_device_addresses is inventory_read_repository.get_device_addresses
    assert inventory_repository_compat.get_device_history is inventory_read_repository.get_device_history
    assert inventory_repository_compat.get_scans is inventory_read_repository.get_scans
    assert inventory_repository_compat._device_dict is inventory_repository_support._device_dict
    assert inventory_repository_compat._ip_sort_key is inventory_repository_support._ip_sort_key
    assert database.list_devices is inventory_repository_compat.list_devices
    assert database.record_scan is inventory_repository_compat.record_scan


def test_monitoring_repository_facade_reexports_historical_functions() -> None:
    """La fachada y database.py siguen exponiendo las operaciones originales."""
    assert monitoring_repository_compat.create_monitor is monitoring_config_repository.create_monitor
    assert monitoring_repository_compat.list_monitors is monitoring_config_repository.list_monitors
    assert monitoring_repository_compat.update_monitor is monitoring_config_repository.update_monitor
    assert monitoring_repository_compat.delete_monitor is monitoring_config_repository.delete_monitor
    assert monitoring_repository_compat.get_monitor_checks is monitoring_analytics_repository.get_monitor_checks
    assert monitoring_repository_compat.get_monitor_analytics is monitoring_analytics_repository.get_monitor_analytics
    assert monitoring_repository_compat.get_monitor_latency_trend is monitoring_analytics_repository.get_monitor_latency_trend
    assert monitoring_repository_compat.get_incidents is monitoring_analytics_repository.get_incidents
    assert monitoring_repository_compat.cleanup_monitor_history is monitoring_state_repository.cleanup_monitor_history
    assert monitoring_repository_compat.record_monitor_check is monitoring_state_repository.record_monitor_check
    assert monitoring_repository_compat.record_notification is monitoring_notifications_repository.record_notification
    assert monitoring_repository_compat.get_notification_log is monitoring_notifications_repository.get_notification_log
    assert database.create_monitor is monitoring_repository_compat.create_monitor
    assert database.record_monitor_check is monitoring_repository_compat.record_monitor_check


def test_forensics_endpoints_belong_to_forensics_router() -> None:
    """Los endpoints de casos y evidencia viven en el router forense."""
    paths = {route.path for route in forensics.router.routes}
    assert {
        "/api/forensics/cases",
        "/api/forensics/cases/{case_id}",
        "/api/forensics/cases/{case_id}/close",
        "/api/forensics/cases/{case_id}/evidence",
        "/api/forensics/cases/{case_id}/audit",
        "/api/forensics/cases/{case_id}/evidence/{evidence_id}/verify-hash",
        "/api/forensics/cases/{case_id}/evidence/{evidence_id}/integrity-checks",
    } <= paths


def test_forensics_router_has_only_declared_internal_dependencies() -> None:
    """El router usa el servicio de dominio, no la base de datos directamente."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\\n".join(violations)
    assert graph["netsentinel.api.forensics"] == {"netsentinel.forensics_service"}


def test_html_pages_belong_to_pages_router() -> None:
    """Las seis páginas HTML se sirven desde su router dedicado."""
    paths = {route.path for route in pages.router.routes}
    assert paths == {"/", "/monitors", "/activity", "/findings", "/tools", "/forensics"}
    assert all(not route.include_in_schema for route in pages.router.routes)


def test_pages_router_has_no_internal_domain_dependencies() -> None:
    """El router de páginas solo selecciona recursos HTML empaquetados."""
    root = Path(__file__).resolve().parents[1]
    violations, graph = check_architecture(root)
    assert not violations, "\\n".join(violations)
    assert graph["netsentinel.api.pages"] == set()


def test_error_journal_cannot_import_unrelated_domains(tmp_path: Path) -> None:
    """El diario solo depende de la ubicación de datos, no del resto del programa."""
    package = _write_minimal_package(tmp_path)
    (package / "config.py").write_text("def data_dir(): return None\n", encoding="utf-8")
    (package / "database.py").write_text("VALUE = 1\n", encoding="utf-8")
    (package / "error_reporting.py").write_text(
        "from .error_journal import record_error_event\n", encoding="utf-8"
    )
    (package / "error_journal.py").write_text(
        "from . import config, database\n", encoding="utf-8"
    )

    violations, _ = check_architecture(tmp_path)

    assert any(
        "netsentinel.error_journal imports netsentinel.database, which is not an allowed journal dependency"
        in violation
        for violation in violations
    )
