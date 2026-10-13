# Matriz de validación manual

Esta matriz almacena evidencia para la Fase 0 del [roadmap](ROADMAP.md). En la revisión inicial todas las pruebas manuales se consideran **pendientes de registrar**: no se infieren resultados manuales a partir de CI. Actualizarla en el PR que complete un recorrido y adjuntar enlaces a issues si hubo fallos.

## Datos de cada sesión de pruebas

- Fecha y zona horaria:
- Persona que prueba:
- Versión de NetSentinel:
- Commit exacto:
- Sistema operativo y versión:
- Versión de Python:
- Navegador y versión (si aplica):
- Tipo de instalación: descarga limpia / wheel / actualización:
- Resultado global: pendiente / aprobado / bloqueado:
- Enlaces a logs, capturas sanitizadas, CI o issues:

No adjuntar inventarios reales, IP públicas del cliente, cookies, tokens, credenciales, correos ni URLs privadas sin saneamiento. Los datos de ejemplo publicados deben ser sintéticos.

## Recorridos críticos por sistema operativo

Marcar cada tarea solo después de completar el recorrido en ese sistema y registrar fecha, versión/commit y evidencia en el registro de sesiones.

### Windows

- [ ] REL-01 — Instalación limpia, primer inicio y actualización/reinicio.
- [ ] REL-02 — Inventario y descubrimiento LAN autorizado; interfaces/subredes y límites.
- [ ] REL-03 — Checks Ping/TCP/HTTP(S), incidentes, recuperación, timeouts y retención.
- [ ] REL-04 — DNS válido/inválido/timeout; TLS válido, vencido/no confiable, hostname incorrecto y puerto no TLS.
- [ ] REL-05 — Exportación y respaldo SQLite; restaurar en entorno seguro y verificar integridad.
- [ ] REL-06 — Importación CSV, previsualización, deduplicación, filtros, fórmulas y borrado selectivo.
- [ ] REL-07 — Importación de metadatos de auditoría de correo autorizados, rechazo de cuerpos/adjuntos y retención.

**Evidencia Windows:**
- Fecha/versión/commit:
- Resultado y observaciones:
- Issue/CI/capturas sanitizadas:

### macOS

- [ ] REL-01 — Instalación limpia, primer inicio y actualización/reinicio.
- [ ] REL-02 — Inventario y descubrimiento LAN autorizado; interfaces/subredes y límites.
- [ ] REL-03 — Checks Ping/TCP/HTTP(S), incidentes, recuperación, timeouts y retención.
- [ ] REL-04 — DNS válido/inválido/timeout; TLS válido, vencido/no confiable, hostname incorrecto y puerto no TLS.
- [ ] REL-05 — Exportación y respaldo SQLite; restaurar en entorno seguro y verificar integridad.
- [ ] REL-06 — Importación CSV, previsualización, deduplicación, filtros, fórmulas y borrado selectivo.
- [ ] REL-07 — Importación de metadatos de auditoría de correo autorizados, rechazo de cuerpos/adjuntos y retención.

**Evidencia macOS:**
- Fecha/versión/commit:
- Resultado y observaciones:
- Issue/CI/capturas sanitizadas:

### Linux

- [ ] REL-01 — Instalación limpia, primer inicio y actualización/reinicio.
- [ ] REL-02 — Inventario y descubrimiento LAN autorizado; interfaces/subredes y límites.
- [ ] REL-03 — Checks Ping/TCP/HTTP(S), incidentes, recuperación, timeouts y retención.
- [ ] REL-04 — DNS válido/inválido/timeout; TLS válido, vencido/no confiable, hostname incorrecto y puerto no TLS.
- [ ] REL-05 — Exportación y respaldo SQLite; restaurar en entorno seguro y verificar integridad.
- [ ] REL-06 — Importación CSV, previsualización, deduplicación, filtros, fórmulas y borrado selectivo.
- [ ] REL-07 — Importación de metadatos de auditoría de correo autorizados, rechazo de cuerpos/adjuntos y retención.

**Evidencia Linux:**
- Fecha/versión/commit:
- Resultado y observaciones:
- Issue/CI/capturas sanitizadas:

Si un caso no aplica, anotar N/A y justificarlo en vez de dejarlo ambiguo. Si falla, abrir/vincular un issue y dejar la tarea sin marcar.

## Extensión Chromium: Chrome y Edge

Usar páginas y cuentas de prueba; no capturar credenciales ni datos privados. El saneamiento de URL es heurístico y no puede reconocer todos los identificadores personalizados que un sitio coloque en rutas/parámetros desconocidos.

### Chrome

- [ ] EXT-01 — Instalada apagada por defecto y sin registrar hasta activar.
- [ ] EXT-02 — Activación, pausa y desactivación.
- [ ] EXT-03 — Navegación normal, SPA y cambios de URL.
- [ ] EXT-04 — Exclusiones, navegación privada/subframes y límites de retención.
- [ ] EXT-05 — CSV con BOM, comas, comillas, saltos de línea y fórmulas.
- [ ] EXT-06 — Previsualización, duplicados y rechazo de lote inválido sin escrituras parciales.
- [ ] EXT-07 — Saneamiento de URLs y evaluación de falsos positivos/negativos.

**Evidencia Chrome:**
- Fecha/versión/commit:
- Versión navegador / SO:
- Resultado y observaciones:
- Issue/CI/capturas sanitizadas:

### Edge

- [ ] EXT-01 — Instalada apagada por defecto y sin registrar hasta activar.
- [ ] EXT-02 — Activación, pausa y desactivación.
- [ ] EXT-03 — Navegación normal, SPA y cambios de URL.
- [ ] EXT-04 — Exclusiones, navegación privada/subframes y límites de retención.
- [ ] EXT-05 — CSV con BOM, comas, comillas, saltos de línea y fórmulas.
- [ ] EXT-06 — Previsualización, duplicados y rechazo de lote inválido sin escrituras parciales.
- [ ] EXT-07 — Saneamiento de URLs y evaluación de falsos positivos/negativos.

**Evidencia Edge:**
- Fecha/versión/commit:
- Versión navegador / SO:
- Resultado y observaciones:
- Issue/CI/capturas sanitizadas:

## Comprobaciones finales antes de la release

- [ ] La matriz vigente de CI está verde sobre el commit candidato.
- [ ] CodeQL y auditoría de dependencias vigentes están verdes y los hallazgos relevantes tienen resolución documentada.
- [ ] El wheel se instala en un entorno limpio y contiene los HTML/CSS requeridos.
- [ ] El paquete declara la misma versión prerelease/estable que el código.
- [ ] Los backups se pueden restaurar y las exportaciones no filtran tokens.
- [ ] La comprobación SHA-256 funciona y la procedencia del artefacto publicado se verifica cuando existe atestación.
- [ ] La protección de main se verificó en Settings; ver [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
- [ ] Se revisaron individualmente los PRs de Dependabot abiertos y todos los cambios incorporados tienen checks actuales.
- [ ] La lista de limitaciones conocidas y los cambios de la release están actualizados.

## Registro de sesiones

Añadir una fila por sesión; si falla, dejarlo como bloqueado y abrir/vincular un issue.

| Fecha | Versión/commit | OS / navegador | IDs ejecutados | Resultado | Issue / evidencia |
|---|---|---|---|---|---|
| — | — | — | — | Pendiente de primera ejecución | — |
