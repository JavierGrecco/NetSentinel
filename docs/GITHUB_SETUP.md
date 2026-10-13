# Mantenimiento del repositorio

## Proteger la rama principal

La configuración de GitHub no está incluida en los archivos del repositorio. En esta revisión no se pudo confirmar que `main` esté protegida: la lista consultable de rulesets está vacía y el acceso disponible no permitió verificar la protección clásica de la rama. Confirmá el estado desde Settings antes de dar por aplicada la política; documentarla no la activa automáticamente. Para impedir que una actualización aprobada se pierda o que un cambio entre sin validar:

1. Abrí **Settings → Branches** (o **Rules → Rulesets**) del repositorio y creá una regla que apunte exactamente a `main`.
2. Activá **Require a pull request before merging**. Si sos el único mantenedor, podés exigir PR sin requerir una aprobación imposible de obtener de otro usuario; si hay un segundo revisor, pedí al menos una aprobación y descartá aprobaciones obsoletas tras cambios nuevos.
3. Activá **Require status checks to pass before merging** y seleccioná las comprobaciones de la última ejecución de una PR. Como base, exigí los 17 jobs de `CI`: las 15 combinaciones `Python 3.10–3.14 / ubuntu-latest, windows-latest y macos-latest`, más `Minimum declared dependencies (Python 3.10 / Ubuntu)` y `Wheel metadata and static assets`. El job de dependencias mínimas es obligatorio: comprueba que se puedan instalar las cotas inferiores declaradas y que la suite completa pase con ellas.
4. Exigí además `CodeQL static analysis (Python)`, `Audit Python dependencies`, `Detect committed secrets` y `Build wheel, SBOM, and integrity manifest`. Elegí estos contextos por sus nombres de job, después de que GitHub los muestre en la lista de checks recientes.
5. No exijas `Sign release artifact provenance` para PR normales: está condicionado a etiquetas de versión `v*` y correctamente se omite en el trabajo habitual.
6. No permitas force-push ni borrado de `main`. Para una protección fuerte, activá **Do not allow bypassing the above settings** cuando tu flujo de trabajo y permisos lo permitan. Conservá una vía administrativa de recuperación y comprobá después que la regla aparece activa.

La regla de rama es una configuración de GitHub, no un archivo de código. Después de guardarla, volvé a consultar la protección de `main` y verificá que el merge de prueba no puede avanzar con un check obligatorio fallido. Los nombres concretos de checks pueden cambiar al modificar workflows; actualizá la regla si se renombran.

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
