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

| ID / Recorrido | Windows | macOS | Linux | Evidencia mínima |
|---|---|---|---|---|
| REL-01 — instalación limpia y primer inicio | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Versión OS/Python, pasos, salida y URL local |
| REL-02 — inventario y descubrimiento LAN autorizado | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Subred de laboratorio, resultado y límites observados |
| REL-03 — monitor Ping/TCP/HTTP(S), incidentes y recuperación | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Resultado de cada tipo y ciclo de incidente |
| REL-04 — DNS, timeout y diagnóstico TLS | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Casos válidos e inválidos, tiempos y errores |
| REL-05 — exportación, respaldo SQLite y restauración | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Recuento antes/después y resultado de restauración |
| REL-06 — importación CSV, filtros, deduplicación y borrado | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | Fixture sintético, recuentos, confirmación y resultado |
| REL-07 — metadatos de correo de auditoría autorizada | [ ] Pendiente | [ ] Pendiente | [ ] Pendiente | CSV sintético/permitido y columnas admitidas/rechazadas |

Marcar una celda solo cuando el recorrido se haya completado en ese OS; anotar fecha, versión y resultado en el historial de abajo o vincular un issue con la evidencia. Cuando no sea aplicable, indicar explícitamente N/A y la razón, no dejarla ambigua.

## Extensión Chromium — pruebas manuales

| ID / Caso | Chrome | Edge | Resultado / evidencia |
|---|---|---|---|
| EXT-01 — instalada apagada por defecto; sin registrar hasta activar | [ ] Pendiente | [ ] Pendiente | |
| EXT-02 — activación, pausa y desactivación | [ ] Pendiente | [ ] Pendiente | |
| EXT-03 — navegación normal, SPA y cambios de URL | [ ] Pendiente | [ ] Pendiente | |
| EXT-04 — exclusiones, pestaña privada/subframes y límites de retención | [ ] Pendiente | [ ] Pendiente | |
| EXT-05 — exportación CSV, BOM, comas, comillas, saltos de línea y fórmulas | [ ] Pendiente | [ ] Pendiente | |
| EXT-06 — vista previa, duplicados y rechazo del lote inválido sin escrituras parciales | [ ] Pendiente | [ ] Pendiente | |
| EXT-07 — saneamiento de URLs y evaluación de falsos positivos/negativos | [ ] Pendiente | [ ] Pendiente | |

Usar páginas y cuentas de prueba. Verificar especialmente que datos potencialmente sensibles no se asuman eliminados por completo: el saneamiento de URL es heurístico y no puede reconocer todos los identificadores personalizados que un sitio coloque en rutas/parámetros desconocidos.

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

Añadir una fila por sistema/recorrido comprobado. Si falla, dejarlo como bloqueado y abrir/vincular un issue; no sustituir el resultado negativo por una marca de aprobado.

| Fecha | Versión/commit | OS / navegador | IDs ejecutados | Resultado | Issue / evidencia |
|---|---|---|---|---|---|
| — | — | — | — | Pendiente de primera ejecución | — |
