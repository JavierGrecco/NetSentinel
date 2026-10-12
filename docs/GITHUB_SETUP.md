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

## Integridad de los workflows

Las acciones externas usadas por los workflows de CI, análisis de seguridad y cadena de suministro se fijan a SHA completos, no a etiquetas móviles. Dependabot tiene habilitadas actualizaciones semanales para GitHub Actions; revisá cada propuesta y su cambio de SHA antes de integrarla. La fijación reduce el riesgo de que una etiqueta se mueva de forma inesperada, pero las actualizaciones siguen requiriendo revisión y CI.

## Validación de checksums

El helper `scripts/verify-sha256-manifest.sh` comprueba un manifiesto desde la carpeta donde se generó, por lo que funciona aunque se invoque desde otra ubicación:

```bash
bash scripts/verify-sha256-manifest.sh dist/SHA256SUMS
```

La CI prueba un artefacto sintético intacto y verifica que el helper rechace el mismo archivo tras modificarlo. Para artefactos descargados sin el repositorio, ejecutá `sha256sum --check SHA256SUMS` desde la carpeta que contiene el manifiesto y todos los archivos listados. Esto comprueba integridad, pero no certifica autenticidad; verificá también la atestación de procedencia cuando exista.

## Estructura básica

- `src/netsentinel/`: código de la aplicación.
- `src/netsentinel/static/`: paneles HTML y hojas CSS.
- `tests/`: pruebas automatizadas.
- `docs/`: arquitectura, seguridad, monitorización y planificación.
- `.github/workflows/ci.yml`: matriz de pruebas multiplataforma.

No agregues bases de datos locales, exportaciones reales, secretos ni credenciales al repositorio.
