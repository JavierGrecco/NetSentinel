# Mantenimiento del repositorio

## Fuente de verdad del plan

- [ROADMAP.md](ROADMAP.md) es la fuente única para prioridades, estado y puertas de finalización.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) describe el enfoque técnico y las pruebas.
- [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) conserva evidencia de pruebas manuales.
- Al cerrar una tarea, actualizá su casilla y adjuntá en el mismo PR los enlaces a tests/CI/evidencia. No marcar como completa una prueba manual a partir de CI.

## Proteger la rama principal

**Última lectura verificada: 27/11/2026.** El ruleset de repositorio `rules` (ID `25281660`) aparece como **Active**, pero su configuración actual no demuestra que proteja `main`:

- `conditions.ref_name.include = []` y `exclude = []`. La condición requiere que al menos un patrón de inclusión coincida; con la lista vacía no hay un alcance explícito para `main`.
- `required_status_checks = []`: no exige ningún contexto de CI o seguridad.
- `required_approving_review_count = 0`: no exige aprobación.
- Están presentes las reglas de PR, bloqueo de borrado y bloqueo de force-push, pero las reglas solo se aplican a refs que coinciden con las condiciones.
- La API clásica de branch protection devolvió 403 para esta integración, por lo que no se afirma que exista una protección clásica adicional.

La documentación de GitHub especifica que una condición de ref debe incluir al menos un patrón y permite `~DEFAULT_BRANCH` o `refs/heads/main` para seleccionar la rama principal ([documentación de rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository); [API de reglas](https://docs.github.com/en/rest/repos/rules)). Una persona con permisos de administración debe corregir y verificar este punto en Settings. El conector de trabajo utilizado aquí puede consultar el ruleset, pero no modificarlo.

### Configuración que debe quedar en el Ruleset

1. Abrí **Settings → Rules → Rulesets** y editá el ruleset `rules`.
2. En **Target branches**, añadí `~DEFAULT_BRANCH` o `refs/heads/main` y revisá la vista previa para confirmar que incluya `main`.
3. Mantené activados **Restrict deletions** y **Block force pushes**.
4. Activá **Require a pull request before merging**. Con un único mantenedor no exijas una aprobación imposible de obtener; documentá esa limitación.
5. Activá **Require status checks to pass** y añadí los contextos enumerados abajo. No uses el nombre genérico del workflow cuando GitHub muestre los jobs individuales.
6. Recomiendo exigir que la rama esté actualizada con `main`, siempre que el coste operativo de actualizar PRs sea aceptable.
7. Revisá los permisos de bypass y dejalos vacíos salvo una excepción deliberada y documentada.
8. Guardá como **Active** y volvé a consultar el ruleset para comprobar el patrón y los checks.

### Checks obligatorios recomendados para Pull Requests

La matriz vigente tiene **23 contextos aplicables**: 19 de CI, 2 de Security Analysis y 2 de Supply Chain. Confirmá los nombres en una PR reciente antes de guardarlos, ya que pueden cambiar en futuras actualizaciones.

**CI — 19 checks**

Matriz Python (15 combinaciones):

- `Python 3.10 / ubuntu-latest`
- `Python 3.10 / windows-latest`
- `Python 3.10 / macos-latest`
- `Python 3.11 / ubuntu-latest`
- `Python 3.11 / windows-latest`
- `Python 3.11 / macos-latest`
- `Python 3.12 / ubuntu-latest`
- `Python 3.12 / windows-latest`
- `Python 3.12 / macos-latest`
- `Python 3.13 / ubuntu-latest`
- `Python 3.13 / windows-latest`
- `Python 3.13 / macos-latest`
- `Python 3.14 / ubuntu-latest`
- `Python 3.14 / windows-latest`
- `Python 3.14 / macos-latest`

Otras verificaciones de CI:

- `Minimum declared dependencies (Python 3.10 / Ubuntu)`
- `Wheel metadata and static assets`
- `Browser extension tests (Node 24)`
- `Responsive UI / Chromium`

**Seguridad — 2 checks**

- `CodeQL static analysis (Python, JavaScript and GitHub Actions)`
- `Audit Python dependencies`

CodeQL publica además resultados en GitHub Code Scanning; ese resultado de análisis no debe contarse como un tercer job de Actions.

**Cadena de suministro — 2 checks**

- `Detect committed secrets`
- `Build wheel, SBOM, and integrity manifest`

No añadas `Sign release artifact provenance` como requisito de PR: se ejecuta únicamente al publicar una etiqueta `v*` y se omite en PR normales.

### Cómo verificar que realmente protege

- Confirmá que el ruleset esté **Active** y que incluya explícitamente `main`.
- Abrí una PR de prueba: GitHub debe bloquear el merge cuando falte un check obligatorio o alguno falle.
- Comprobá que un push directo a `main` sea rechazado para una identidad sin bypass.
- No marques una prueba manual como aprobada solo porque CI esté verde. Registrá esa evidencia en `VALIDATION_MATRIX.md`.

## Eliminar ramas fusionadas sin acumular ramas activas

El workflow `.github/workflows/delete-merged-head-branch.yml` elimina automáticamente la rama fuente cuando una PR se fusiona a `main`, siempre que:

- la PR esté realmente fusionada (no solo cerrada);
- la rama fuente pertenezca a este mismo repositorio;
- no sea `main`;
- ninguna otra PR abierta use la misma rama;
- el SHA remoto siga siendo idéntico al SHA de la PR fusionada.

El job usa `pull_request_target` solo para el evento `closed`, ejecuta el código del repositorio base, nunca hace checkout del código de la PR y elimina la referencia mediante `--force-with-lease`. Si la rama cambió o sigue siendo utilizada, se conserva. Las ramas de PR abiertas —por ejemplo #200 y #222— no se eliminan.

También conviene activar **Settings → General → Pull Requests → Automatically delete head branches** como respaldo nativo de GitHub. La automatización del repositorio proporciona además la comprobación de SHA y de otras PR abiertas.

La limpieza histórica del 27/11/2026 fue auditada y quedó cerrada en [issue #221](https://github.com/JavierGrecco/NetSentinel/issues/221). El inventario remoto final de ese corte quedó reducido a `main`, #200 y #222. No borrar por prefijo, antigüedad ni nombre.

## Política de versiones

La versión se define en src/netsentinel/__init__.py. pyproject.toml la obtiene mediante metadatos dinámicos y no debe mantener una segunda versión manual.

- Mientras 0.10.0 esté en desarrollo, usar la versión PEP 440 0.10.0.dev0 y mantener el changelog claramente marcado como en desarrollo.
- Para publicar 0.10.0, completar la puerta de release en ROADMAP.md, cambiar la versión de desarrollo a 0.10.0, actualizar CHANGELOG.md, ejecutar CI sobre el candidato y comprobar que los metadatos del wheel coinciden.
- Publicar la etiqueta v0.10.0 solo sobre el commit aprobado; generar y verificar los artefactos de ese commit.
- Inmediatamente después de una release, preparar la siguiente versión de desarrollo con sufijo .dev0 y un encabezado de changelog que la identifique como futura. No etiquetar una versión no validada como estable.

## Artefactos y procedencia

El workflow .github/workflows/supply-chain.yml genera un wheel, SBOM CycloneDX y SHA256SUMS como artefactos. Comprueba el checksum desde la carpeta del manifiesto con:

    sha256sum --check SHA256SUMS

El repositorio incluye scripts/verify-sha256-manifest.sh para validar manifiestos. La comprobación del hash detecta corrupción, pero por sí sola no autentica al autor del artefacto. Para versiones publicadas con atestación, comprobar también la procedencia con GitHub CLI:

    gh attestation verify netsentinel-<version>-py3-none-any.whl --repo JavierGrecco/NetSentinel
    gh attestation verify netsentinel-sbom.cdx.json --repo JavierGrecco/NetSentinel

Usá los nombres de los ficheros realmente descargados. Estos comandos son opcionales y requieren GitHub CLI; no necesitás instalar `gh` para iniciar NetSentinel, desarrollar, ejecutar las pruebas locales ni completar el laboratorio de aceptación. Si se expone una credencial real, revocala/rotala de inmediato: borrar el texto en un commit posterior no vuelve segura la credencial.

## Dependencias y workflows

Las acciones externas se fijan a SHA completos. Dependabot puede proponer actualizaciones semanales: revisar cada PR individualmente, especialmente cambios de SHA de acciones, compatibilidad runtime, constraints mínimas y tests. No fusionar un lote únicamente porque los checks históricos estén verdes: confirmar el resultado sobre el head SHA actual y considerar el diff.

Antes de añadir una dependencia, justificar la función que aporta, mantenimiento, licencia, permisos/red, superficie de ataque y alternativa estándar. La CI debe verificar comportamiento, no solo instalar herramientas como decoración.

## Estructura básica

- src/netsentinel/: aplicación y módulos de dominio.
- src/netsentinel/static/: paneles HTML/CSS.
- tests/: pruebas Python.
- browser-extension/: extensión y tests Node.
- docs/: arquitectura, seguridad, uso y planificación.
- .github/workflows/ci.yml: matriz de pruebas.
- .github/workflows/security.yml: análisis estático y auditoría de dependencias.
- .github/workflows/supply-chain.yml: artefactos, SBOM, manifiesto y procedencia.

No agregar bases de datos locales, exportaciones reales, inventarios de clientes, tokens, credenciales ni URLs privadas al repositorio.
