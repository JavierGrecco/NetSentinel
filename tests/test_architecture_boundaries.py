"""Comprueba que las fronteras iniciales de la API modular se mantienen claras."""
from __future__ import annotations

import ast
from pathlib import Path

from netsentinel.api import tools


def test_dns_tls_endpoints_belong_to_tools_router() -> None:
    """La composición debe registrar estos endpoints desde su módulo funcional."""
    paths = {route.path for route in tools.router.routes}
    assert {
        "/api/tools/tls/inspect",
        "/api/tools/dns/configuration",
        "/api/tools/dns/lookup",
        "/api/tools/dns/reverse",
    } <= paths


def test_tools_api_does_not_depend_on_app_composition_or_database() -> None:
    """Las rutas de herramientas no deben importar main.py ni consultar SQL."""
    module_path = Path(tools.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add(node.module or "")

    assert not any(
        name == "netsentinel.main"
        or name.endswith(".main")
        or name == "netsentinel.database"
        or name.endswith(".database")
        for name in imported_modules
    )
