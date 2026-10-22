#!/usr/bin/env python3
"""Comprueba límites de dependencia en el paquete NetSentinel.

La verificación usa el AST de Python y no necesita instalar dependencias extra.
Actualizá las reglas explícitas al introducir un nuevo módulo público.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class SourceModule:
    """Un archivo Python de producción y su nombre importable."""

    name: str
    path: Path
    is_package: bool


API_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "netsentinel.api.tools": {
        "netsentinel.api.tools_dns",
        "netsentinel.api.tools_tls",
    },
    "netsentinel.api.tools_dns": {
        "netsentinel.dns_config",
        "netsentinel.dns_tools",
    },
    "netsentinel.api.tools_tls": {
        "netsentinel.tls_tools",
    },
    "netsentinel.api.security": {
        "netsentinel.api.security_headers",
    },
    "netsentinel.api.security_headers": set(),
    "netsentinel.api.error_handling": {
        "netsentinel.api.security",
        "netsentinel.api.validation_errors",
        "netsentinel.error_reporting",
    },
    "netsentinel.api.validation_errors": {
        "netsentinel.api.security_headers",
    },
    "netsentinel.api.activity": {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_deletion",
        "netsentinel.api.activity_import",
        "netsentinel.api.activity_models",
        "netsentinel.api.activity_read",
        "netsentinel.api.activity_retention",
        "netsentinel.api.activity_sessions",
    },
    "netsentinel.api.activity_models": set(),
    "netsentinel.api.activity_read": {
        "netsentinel.activity_tracking",
    },
    "netsentinel.api.geolocation": {
        "netsentinel.geolocation_service",
    },
    "netsentinel.api.activity_sessions": {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    },
    "netsentinel.api.activity_import": {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    },
    "netsentinel.api.activity_deletion": {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    },
    "netsentinel.api.activity_retention": {
        "netsentinel.activity_tracking",
        "netsentinel.api.activity_models",
    },
    "netsentinel.api.findings": {
        "netsentinel.findings_service",
    },
    "netsentinel.api.forensics": {
        "netsentinel.forensics_service",
    },
    "netsentinel.api.inventory": {
        "netsentinel.api.inventory_assets",
        "netsentinel.api.inventory_discovery",
        "netsentinel.api.inventory_exports",
    },
    "netsentinel.api.inventory_assets": {
        "netsentinel.database",
        "netsentinel.dns_tools",
    },
    "netsentinel.api.inventory_discovery": {
        "netsentinel.database",
        "netsentinel.local_discovery",
    },
    "netsentinel.api.inventory_exports": {
        "netsentinel.database",
    },
    "netsentinel.api.monitoring": {
        "netsentinel.api.diagnostics",
        "netsentinel.api.monitoring_monitors",
        "netsentinel.api.monitoring_reports",
    },
    "netsentinel.api.monitoring_monitors": {
        "netsentinel.database",
        "netsentinel.monitoring",
    },
    "netsentinel.api.monitoring_reports": {
        "netsentinel.database",
    },
    "netsentinel.api.diagnostics": {
        "netsentinel.diagnostics",
    },
}

# La fachada pública puede delegar en los repositorios especializados, pero no debe
# contener consultas. Los repositorios no pueden volver a importar esta fachada.
DATABASE_ALLOWED_INTERNAL_IMPORTS = {
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

# La infraestructura SQLite solo conoce configuración y ciclo de vida del archivo.
DATABASE_STORAGE_ALLOWED_INTERNAL_IMPORTS = {
    "netsentinel.config",
}

DATABASE_SCHEMA_ALLOWED_INTERNAL_IMPORTS = {
    "netsentinel.database_storage",
    "netsentinel.forensics_audit_integrity",
}

# La clasificación de errores delega el almacenamiento en el diario local.
ERROR_REPORTING_ALLOWED_INTERNAL_IMPORTS = {
    "netsentinel.error_journal",
}
ERROR_JOURNAL_ALLOWED_INTERNAL_IMPORTS = {
    "netsentinel.config",
}

SERVICE_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "netsentinel.activity_deletion_service": {
        "netsentinel.activity_filters",
        "netsentinel.activity_repository",
    },
    "netsentinel.activity_retention_service": {
        "netsentinel.activity_repository",
    },
    "netsentinel.activity_session_service": {
        "netsentinel.activity_catalog",
        "netsentinel.activity_event_service",
        "netsentinel.activity_repository",
        "netsentinel.activity_retention_service",
        "netsentinel.database",
    },
    "netsentinel.activity_event_service": {
        "netsentinel.activity_catalog",
        "netsentinel.activity_privacy",
    },
    "netsentinel.activity_read_service": {
        "netsentinel.activity_catalog",
        "netsentinel.activity_filters",
        "netsentinel.activity_repository",
        "netsentinel.csv_safety",
    },
    "netsentinel.activity_import_service": {
        "netsentinel.activity_repository",
    },
    "netsentinel.geolocation_service": {
        "netsentinel.config",
        "netsentinel.geolocation_repository",
    },
    "netsentinel.findings_service": {
        "netsentinel.database",
        "netsentinel.findings",
    },
    "netsentinel.forensics_service": {
        "netsentinel.config",
        "netsentinel.forensics_audit_manifest",
        "netsentinel.forensics_case_manifest",
        "netsentinel.forensics_errors",
        "netsentinel.forensics_integrity",
        "netsentinel.forensics_repository",
        "netsentinel.forensics_report",
    },
    "netsentinel.data_export_service": {
        "netsentinel.config",
        "netsentinel.csv_safety",
        "netsentinel.database_storage",
        "netsentinel.inventory_repository",
    },
    "netsentinel.monitoring_export_service": {
        "netsentinel.csv_safety",
        "netsentinel.monitoring_repository",
    },
}
# Compatibility facades may coordinate domain services, but must not grow
# direct dependencies on persistence or unrelated application domains.
FACADE_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "netsentinel.activity_tracking": {
        "netsentinel.activity_catalog",
        "netsentinel.activity_deletion_service",
        "netsentinel.activity_event_service",
        "netsentinel.activity_filters",
        "netsentinel.activity_import_service",
        "netsentinel.activity_privacy",
        "netsentinel.activity_read_service",
        "netsentinel.activity_retention_service",
        "netsentinel.activity_session_service",
    },
}
REPOSITORY_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "netsentinel.activity_repository": {
        "netsentinel.database",
        "netsentinel.activity_deletion_repository",
        "netsentinel.activity_import_repository",
        "netsentinel.activity_read_repository",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
        "netsentinel.activity_session_repository",
    },
    "netsentinel.activity_retention_repository": {
        "netsentinel.database",
    },
    "netsentinel.activity_session_repository": set(),
    "netsentinel.activity_import_repository": {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
    },
    "netsentinel.activity_deletion_repository": {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
    },
    "netsentinel.activity_read_repository": {
        "netsentinel.database",
        "netsentinel.activity_repository_support",
        "netsentinel.activity_retention_repository",
    },
    "netsentinel.geolocation_repository": {
        "netsentinel.database",
    },
    "netsentinel.inventory_repository": {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
        "netsentinel.inventory_read_repository",
        "netsentinel.inventory_repository_support",
        "netsentinel.network_models",
        "netsentinel.vendor",
    },
    "netsentinel.inventory_read_repository": {
        "netsentinel.database_storage",
        "netsentinel.inventory_repository_support",
    },
    "netsentinel.inventory_repository_support": set(),
    "netsentinel.events_repository": {
        "netsentinel.database_storage",
    },
    "netsentinel.dashboard_repository": {
        "netsentinel.database_storage",
    },
    "netsentinel.monitoring_repository": {
        "netsentinel.monitoring_analytics_repository",
        "netsentinel.monitoring_config_repository",
        "netsentinel.monitoring_notifications_repository",
        "netsentinel.monitoring_state_repository",
    },
    "netsentinel.monitoring_config_repository": {
        "netsentinel.database_storage",
    },
    "netsentinel.monitoring_analytics_repository": {
        "netsentinel.database_storage",
    },
    "netsentinel.monitoring_state_repository": {
        "netsentinel.database_storage",
        "netsentinel.events_repository",
    },
    "netsentinel.monitoring_notifications_repository": {
        "netsentinel.database_storage",
    },
    "netsentinel.forensics_repository": {
        "netsentinel.database_storage",
        "netsentinel.forensics_audit_integrity",
        "netsentinel.forensics_errors",
    },

}
# Only the composition root and API routers may import the HTTP framework.
# This rule applies automatically to new domain modules as they are added.
HTTP_FRAMEWORK_ALLOWED_MODULES = {
    "netsentinel.main",
    "netsentinel.api",
}


def discover_source_modules(root: Path) -> dict[str, SourceModule]:
    """Find package files and derive their importable module names."""
    package_root = root / "src" / "netsentinel"
    if not package_root.is_dir():
        raise FileNotFoundError(f"Expected package directory does not exist: {package_root}")

    modules: dict[str, SourceModule] = {}
    for path in sorted(package_root.rglob("*.py")):
        relative = path.relative_to(package_root)
        parts = list(relative.with_suffix("").parts)
        is_package = parts[-1] == "__init__"
        if is_package:
            parts.pop()
        name = ".".join(("netsentinel", *parts))
        modules[name] = SourceModule(name=name, path=path, is_package=is_package)

    if "netsentinel.main" not in modules:
        raise FileNotFoundError("Expected src/netsentinel/main.py was not found.")
    return modules


def absolute_import_name(
    source: SourceModule, level: int, imported_module: str | None
) -> str | None:
    """Resolve a Python absolute or relative import to its full module name."""
    if level == 0:
        return imported_module

    package = source.name if source.is_package else source.name.rpartition(".")[0]
    parts = package.split(".")
    remove_count = level - 1
    if remove_count >= len(parts):
        return None
    base = parts[: len(parts) - remove_count]
    if imported_module:
        base.extend(imported_module.split("."))
    return ".".join(base)


def collect_dependencies(
    modules: dict[str, SourceModule],
) -> dict[str, set[str]]:
    """Build the graph of source modules from Python import statements."""
    known_names = set(modules)
    graph: dict[str, set[str]] = {name: set() for name in modules}

    for source in modules.values():
        syntax = ast.parse(source.path.read_text(encoding="utf-8"), filename=str(source.path))
        for node in ast.walk(syntax):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target in known_names and target != source.name:
                        graph[source.name].add(target)
                continue

            if not isinstance(node, ast.ImportFrom):
                continue

            target = absolute_import_name(source, node.level, node.module)
            if node.module and target in known_names and target != source.name:
                graph[source.name].add(target)

            # Child modules count as dependencies; attributes such as __version__
            # do not create a module edge unless a matching module file exists.
            if target:
                for alias in node.names:
                    child = f"{target}.{alias.name}"
                    if child in known_names and child != source.name:
                        graph[source.name].add(child)

    return graph


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Find import cycles in the internal dependency graph."""
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def visit(module: str) -> None:
        state[module] = 1
        stack.append(module)
        for dependency in sorted(graph.get(module, set())):
            if state.get(dependency, 0) == 0:
                visit(dependency)
            elif state.get(dependency) == 1:
                start = stack.index(dependency)
                cycle = stack[start:] + [dependency]
                ring = cycle[:-1]
                rotations = [tuple(ring[index:] + ring[:index]) for index in range(len(ring))]
                canonical = min(rotations)
                if canonical not in seen:
                    seen.add(canonical)
                    cycles.append(cycle)
        stack.pop()
        state[module] = 2

    for module in sorted(graph):
        if state.get(module, 0) == 0:
            visit(module)
    return cycles


def check_architecture(root: Path) -> tuple[list[str], dict[str, set[str]]]:
    """Return architecture violations and the internal dependency graph."""
    modules = discover_source_modules(root)
    graph = collect_dependencies(modules)
    violations: list[str] = []

    # Dos definiciones de nivel superior con el mismo nombre se pisan en Python.
    # Detectarlas evita que quede código muerto oculto detrás de otra función/clase.
    for source, module in sorted(modules.items()):
        syntax = ast.parse(module.path.read_text(encoding="utf-8"), filename=str(module.path))
        names: set[str] = set()
        for node in syntax.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name in names:
                violations.append(
                    f"{source} defines top-level {node.name} more than once; "
                    "a later definition shadows the earlier one."
                )
            names.add(node.name)

    # The FastAPI composition root can import other modules; they must not
    # import the composition root back.
    for source, dependencies in sorted(graph.items()):
        if source != "netsentinel.main" and "netsentinel.main" in dependencies:
            violations.append(
                f"{source} imports netsentinel.main; the composition root is not an internal API."
            )

    for source in sorted(graph):
        if not source.startswith("netsentinel.api."):
            continue
        allowed = API_ALLOWED_INTERNAL_IMPORTS.get(source)
        if allowed is None and graph[source]:
            violations.append(f"{source} has internal dependencies but no explicit allow-list.")
            continue
        for dependency in sorted(graph[source]):
            if dependency == "netsentinel.api":
                continue
            if dependency not in (allowed or set()):
                violations.append(
                    f"{source} imports {dependency}, which is not an allowed public dependency."
                )

    # Every service with internal dependencies needs a declared allow-list.
    # New modules cannot silently skip this policy by not being registered above.
    for source, dependencies in sorted(graph.items()):
        if not source.endswith("_service"):
            continue
        allowed = SERVICE_ALLOWED_INTERNAL_IMPORTS.get(source)
        if allowed is None and dependencies:
            violations.append(
                f"{source} has internal dependencies but no explicit service allow-list."
            )
            continue
        for dependency in sorted(dependencies):
            if dependency not in (allowed or set()):
                violations.append(
                    f"{source} imports {dependency}, which is not an allowed service dependency."
                )

    # Keep compatibility facades thin and prevent them from importing storage directly.
    for source, allowed in sorted(FACADE_ALLOWED_INTERNAL_IMPORTS.items()):
        if source not in graph:
            violations.append(f"{source} is missing but still has an explicit facade allow-list.")
            continue
        for dependency in sorted(graph[source]):
            if dependency not in allowed:
                violations.append(
                    f"{source} imports {dependency}, which is not an allowed facade dependency."
                )

    # Apply the same rule to persistence adapters.
    for source, dependencies in sorted(graph.items()):
        if not source.endswith("_repository"):
            continue
        allowed = REPOSITORY_ALLOWED_INTERNAL_IMPORTS.get(source)
        if allowed is None and dependencies:
            violations.append(
                f"{source} has internal dependencies but no explicit repository allow-list."
            )
            continue
        for dependency in sorted(dependencies):
            if dependency not in (allowed or set()):
                violations.append(
                    f"{source} imports {dependency}, which is not an allowed repository dependency."
                )

    database_dependencies = graph.get("netsentinel.database", set())
    for dependency in sorted(database_dependencies - DATABASE_ALLOWED_INTERNAL_IMPORTS):
        violations.append(
            f"netsentinel.database imports {dependency}, which is not an allowed persistence dependency; "
            "keep query implementation in an explicitly owned module."
        )

    storage_dependencies = graph.get("netsentinel.database_storage", set())
    for dependency in sorted(storage_dependencies - DATABASE_STORAGE_ALLOWED_INTERNAL_IMPORTS):
        violations.append(
            f"netsentinel.database_storage imports {dependency}, which is not an allowed infrastructure dependency."
        )

    schema_dependencies = graph.get("netsentinel.database_schema", set())
    for dependency in sorted(schema_dependencies - DATABASE_SCHEMA_ALLOWED_INTERNAL_IMPORTS):
        violations.append(
            f"netsentinel.database_schema imports {dependency}, which is not an allowed schema dependency."
        )

    error_reporting_dependencies = graph.get("netsentinel.error_reporting", set())
    if "netsentinel.error_reporting" in graph:
        if "netsentinel.error_journal" not in error_reporting_dependencies:
            violations.append(
                "netsentinel.error_reporting must delegate journal persistence to netsentinel.error_journal."
            )
        for dependency in sorted(
            error_reporting_dependencies - ERROR_REPORTING_ALLOWED_INTERNAL_IMPORTS
        ):
            violations.append(
                f"netsentinel.error_reporting imports {dependency}, which is not an allowed error-catalog dependency."
            )

    error_journal_dependencies = graph.get("netsentinel.error_journal", set())
    for dependency in sorted(
        error_journal_dependencies - ERROR_JOURNAL_ALLOWED_INTERNAL_IMPORTS
    ):
        violations.append(
            f"netsentinel.error_journal imports {dependency}, which is not an allowed journal dependency."
        )

    for source, module in sorted(modules.items()):
        if source in HTTP_FRAMEWORK_ALLOWED_MODULES or source.startswith("netsentinel.api."):
            continue
        syntax = ast.parse(module.path.read_text(encoding="utf-8"), filename=str(module.path))
        for node in ast.walk(syntax):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            if any(
                name == "fastapi" or name.startswith("fastapi.")
                or name == "starlette" or name.startswith("starlette.")
                for name in imported
            ):
                violations.append(
                    f"{source} imports the HTTP framework; domain and infrastructure modules "
                    "must not depend on FastAPI/Starlette."
                )
                break

    for cycle in find_cycles(graph):
        violations.append("Import cycle: " + " -> ".join(cycle))

    return violations, graph


def main() -> int:
    """Run the policy check and return a CI-friendly exit status."""
    root = Path(__file__).resolve().parents[1]
    try:
        violations, graph = check_architecture(root)
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"Could not check architecture: {exc}", file=sys.stderr)
        return 2

    if violations:
        print("Architecture boundary violations found:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    edge_count = sum(len(dependencies) for dependencies in graph.values())
    print(
        "Architecture boundaries verified: "
        f"{len(graph)} Python modules, {edge_count} internal dependencies; "
        "no cycles or forbidden dependencies."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
