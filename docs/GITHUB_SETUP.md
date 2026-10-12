# Mantenimiento del repositorio

## Publicar una versión

1. Actualizá la versión en `pyproject.toml` y `src/netsentinel/__init__.py`.
2. Agregá los cambios al principio de `CHANGELOG.md`.
3. Ejecutá `python -m pip install -e ".[test]"` y `pytest`.
4. Comprobá el flujo de GitHub Actions en Windows, macOS y Ubuntu.
5. Creá una etiqueta de versión solo cuando las pruebas estén aprobadas.

## Artefactos y procedencia de versiones

El workflow `.github/workflows/supply-chain.yml` genera el wheel, el SBOM CycloneDX y `SHA256SUMS` como artefacto descargable. Antes de distribuir un artefacto, comprobá el manifiesto:

```bash
sha256sum --check SHA256SUMS
```

Para una versión publicada mediante una etiqueta `v*`, verificá la procedencia con GitHub CLI (además de comprobar el checksum):

```bash
gh attestation verify netsentinel-<version>-py3-none-any.whl --repo JavierGrecco/NetSentinel
gh attestation verify netsentinel-sbom.cdx.json --repo JavierGrecco/NetSentinel
```

El workflow también ejecuta Gitleaks con el historial completo para detectar secretos comprometidos. Si una credencial real se detecta o se publica accidentalmente, revocala/rotala inmediatamente; borrar el texto en un commit posterior no vuelve segura la credencial.

## Estructura básica

- `src/netsentinel/`: código de la aplicación.
- `src/netsentinel/static/`: paneles HTML y hojas CSS.
- `tests/`: pruebas automatizadas.
- `docs/`: arquitectura, seguridad, monitorización y planificación.
- `.github/workflows/ci.yml`: matriz de pruebas multiplataforma.

No agregues bases de datos locales, exportaciones reales, secretos ni credenciales al repositorio.
