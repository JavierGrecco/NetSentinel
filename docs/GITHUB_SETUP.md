# Mantenimiento del repositorio

## Fuente de verdad del plan

- [ROADMAP.md](ROADMAP.md) es la fuente única para prioridades, estado y puertas de finalización.
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) describe el enfoque técnico y las pruebas.
- [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) conserva evidencia de pruebas manuales.
- Al cerrar una tarea, actualizá su casilla y adjuntá en el mismo PR los enlaces a tests/CI/evidencia. No marcar como completa una prueba manual a partir de CI.

## Proteger la rama principal

La política escrita no configura GitHub por sí sola. En la revisión del 16/10/2026, la API de ramas devolvió `protected: false` para `main`; esa respuesta no muestra una protección tradicional aplicada. Revisá también **Settings → Rules → Rulesets** por si el repositorio usa reglasets. El seguimiento sigue pendiente hasta comprobar una regla activa en la configuración real: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).

1. Abrí Settings → Branches o Rules → Rulesets y creá una regla que aplique exactamente a main.
2. Exigí pull request antes de merge. Si existe un segundo revisor, exigí aprobación y descartá aprobaciones obsoletas; si solo hay un mantenedor, no configures un requisito de aprobación imposible de cumplir.
3. Exigí las comprobaciones de estado de la CI vigente. La configuración documentada actualmente contempla la matriz Python 3.10–3.14 en Ubuntu/Windows/macOS, dependencias mínimas y metadata/recursos del wheel.
4. Exigí además CodeQL, auditoría de dependencias, detección de secretos y build de wheel/SBOM/manifiesto. Seleccioná los contextos por el nombre de job que GitHub muestre en las ejecuciones recientes.
5. No exijas el job de atestación de release en PR normales: se ejecuta al publicar etiquetas de versión.
6. Bloqueá force-push y borrado de main. Revisá si conviene impedir bypass administrativo de acuerdo con el modelo de mantenimiento.
7. Después de guardar, verificá que la regla se vea activa y que no se pueda fusionar un cambio con un check obligatorio fallido.

Si cambian los nombres de jobs o workflows, actualizá los checks requeridos. No declares la protección como activa hasta verificarlo en la configuración real.

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
