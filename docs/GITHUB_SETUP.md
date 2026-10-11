# Mantenimiento del repositorio

## Publicar una versión

1. Actualizá la versión en `pyproject.toml` y `src/netsentinel/__init__.py`.
2. Agregá los cambios al principio de `CHANGELOG.md`.
3. Ejecutá `python -m pip install -e ".[test]"` y `pytest`.
4. Comprobá el flujo de GitHub Actions en Windows, macOS y Ubuntu.
5. Creá una etiqueta de versión solo cuando las pruebas estén aprobadas.

## Estructura básica

- `src/netsentinel/`: código de la aplicación.
- `src/netsentinel/static/`: paneles HTML y hojas CSS.
- `tests/`: pruebas automatizadas.
- `docs/`: arquitectura, seguridad, monitorización y planificación.
- `.github/workflows/ci.yml`: matriz de pruebas multiplataforma.

No agregues bases de datos locales, exportaciones reales, secretos ni credenciales al repositorio.
