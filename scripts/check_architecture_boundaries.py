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
        "netsentinel.dns_config",
        "netsentinel.dns_tools",
        "netsentinel.tls_tools",
    },
    "netsentinel.api.activity": {
        "netsentinel.activity_tracking",
    },
    "netsentinel.api.findings": {
        "netsentinel.findings_service",
    },
    "netsentinel.api.inventory": {
        "netsentinel.database",
        "netsentinel.local_discovery",
        "netsentinel.dns_tools",
    },
}

# SQLite may use a small set of shared infrastructure helpers and neutral contracts.
# All other internal dependencies require a deliberate architecture change.
DATABASE_ALLOWED_INTERNAL_IMPORTS = {
    "netsentinel.config",       # Ubicación del archivo de datos.
    "netsentinel.csv_safety",   # Exportaciones CSV seguras.
    "netsentinel.network_models",  # Contrato de vecinos compartido.
    "netsentinel.vendor",       # Consulta OUI local, sin acceso a red.
}

SERVICE_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    # El servicio coordina evidencia y llama al formateador puro. No depende del transporte.
    "netsentinel.findings_service": {
        "netsentinel.database",
        "netsentinel.findings",
    },
}

REPOSITORY_ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    # El repositorio de actividad solo usa la fábrica SQLite compartida.
    "netsentinel.activity_repository": {
        "netsentinel.database",
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
            "keep shared contracts in neutral modules."
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
