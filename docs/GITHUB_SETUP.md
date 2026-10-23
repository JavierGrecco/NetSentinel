# Mantenimiento del repositorio

## Fuente de verdad del plan

- [ROADMAP.md](ROADMAP.md) es la fuente única para prioridades, estado y puertas de finalización.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) describe el enfoque técnico y las pruebas.
- [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) conserva evidencia de pruebas manuales.
- Al cerrar una tarea, actualizá su casilla y adjuntá en el mismo PR los enlaces a tests/CI/evidencia. No marcar como completa una prueba manual a partir de CI.

## Proteger la rama principal

Un Ruleset puede estar activo y aun así no exigir PR ni pruebas. La API de `/branches/main` puede devolver `protected: false` cuando no hay una regla de protección clásica; para evaluar el estado real también hay que leer los Rulesets.

**Última lectura verificada: 22/10/2026.** El ruleset `rules` (ID `25281660`) está activo y contiene las reglas `deletion`, `non_fast_forward`, `pull_request` y `required_status_checks`. Sin embargo, la lista de checks obligatorios sigue vacía (`required_status_checks: []`); el patrón de referencias se devuelve como `include: []`, `exclude: []`; exige cero aprobaciones y no tiene actores de bypass. La API de ramas devuelve `protected: false` para `main`; el endpoint alternativo de protección clásica respondió 403 a la integración de revisión.

**Bloqueo actual:** no asumir que CI, seguridad ni cadena de suministro son obligatorios para fusionar. Durante la actualización del repositorio, la integración automatizada pudo mover la referencia `main` mediante la API de refs aunque el ruleset declara la regla `pull_request`. Eso no demuestra cómo se comporta una credencial humana, pero sí obliga a verificar el efecto real en GitHub antes de afirmar que los pushes directos están bloqueados. Una persona con permisos de administración debe configurar el alcance explícito para `main`, seleccionar los checks requeridos y realizar una prueba de aceptación. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73). La [auditoría de ramas](BRANCH_AUDIT_2026-10.md) mantiene en pausa la eliminación física hasta verificar el alcance de la regla de borrado.

### Configuración que debe quedar en el Ruleset

1. Abrí **Settings → Rules → Rulesets** y editá el Ruleset existente, o creá uno nuevo si corresponde.
2. Seleccioná el objetivo **Branches** y configurá el patrón de inclusión `main`. Revisá la vista previa para confirmar que la regla se aplique a `main` y no accidentalmente a todas las ramas.
3. Mantené activadas **Restrict deletions** y **Block force pushes**.
4. Activá **Require a pull request before merging**. Si otra persona puede revisar, exigí una aprobación y descartá aprobaciones obsoletas. Si hay una sola persona mantenedora, no exijas una aprobación imposible de obtener.
5. Activá **Require status checks to pass** y añadí los nombres de check que aparecen a continuación. Seleccioná el proveedor/origen correcto que muestra GitHub; no sustituyas los checks individuales por el nombre general del workflow.
6. Recomiendo exigir que la rama esté actualizada con `main` antes de fusionar. Esto da una señal más fiable de la integración, pero significa que hay que actualizar una PR cuando cambie `main`.
7. Revisá los permisos de bypass y dejalos desactivados salvo que exista una excepción operativa deliberada, documentada y restringida.
8. Guardá y confirmá que el Ruleset esté en modo **Active**, que la vista previa apunte a `main` y que los checks aparezcan en las reglas requeridas.

### Checks obligatorios para Pull Requests

Seleccioná los siguientes **23 contextos**. Se nombran aquí por el nombre exacto de cada check, tal como aparece en las ejecuciones de Actions y en el check de GitHub Advanced Security.

**CI — 18 checks**

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
- `Responsive UI / Chromium`

**Seguridad — 3 checks**

- `CodeQL` — comprobación de GitHub Advanced Security que señala alertas nuevas en el cambio.
- `CodeQL static analysis (Python)` — job que ejecuta el análisis estático.
- `Audit Python dependencies` — revisión de dependencias contra avisos conocidos.

**Cadena de suministro — 2 checks**

- `Detect committed secrets`
- `Build wheel, SBOM, and integrity manifest`

No añadas `Sign release artifact provenance` como requisito para PR: se ejecuta solo al publicar una etiqueta `v*` y aparece omitido en PR normales. Hacerlo obligatorio bloquearía los merges que no sean publicaciones de release.

### Cómo verificar que realmente protege

- Confirmá que el Ruleset esté **Active**, no en modo Evaluate.
- Confirmá que el patrón se aplique a `main`.
- Abrí una PR de prueba: GitHub debe mostrar el merge bloqueado mientras falte un check obligatorio o alguno falle.
- La PR no debe poder fusionarse directamente si no tiene aprobación cuando esta sea obligatoria, o si no pasó todos los checks requeridos.
- No marques una prueba manual como aprobada solo porque la CI esté verde. Registrá la prueba manual en `VALIDATION_MATRIX.md`.

Si cambian los nombres de job o workflows, actualizá los contextos requeridos. Antes de completar la tarea, comprobá los nombres disponibles en una PR reciente y volvé a verificar el efecto de la regla desde GitHub.

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

Usar el nombre de los ficheros realmente descargados. Si se expone una credencial real, revocarla/rotarla de inmediato; borrar el texto en un commit posterior no vuelve segura la credencial.

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
