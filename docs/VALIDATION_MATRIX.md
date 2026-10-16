# Matriz de validación manual

Esta matriz almacena evidencia para la Fase 0 del [roadmap](ROADMAP.md). El seguimiento de pruebas manuales para la versión 0.10.0 se coordina en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75). Todas las pruebas se consideran **pendientes de registrar** hasta adjuntar evidencia real; no se infieren resultados manuales a partir de CI. Actualizarla en el PR que complete un recorrido y adjuntar enlaces a issues si hubo fallos.

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

### Interfaz y facilidad de uso (todas las plataformas, empezar por macOS)

- [ ] UI-01 — Elegir Oscuro, Medio y Claro desde las tarjetas con iconos en cada página; comprobar el estado seleccionado, el uso con teclado y que la preferencia se mantiene al navegar entre Inventario, Hallazgos, Monitorización, Herramientas y Actividad, después de recargar y al cambiarla desde otra pestaña.
- [ ] UI-02 — En Monitorización, cambiar entre Resumen, Monitores, Incidentes y Avisos; verificar que se distingue un monitor pausado y que la guía aclara que las comprobaciones se detienen al cerrar la app o suspender el equipo.
- [ ] UI-03 — En Hallazgos, comprobar la diferencia entre marcar un dispositivo como conocido y marcar solo el evento como revisado; confirmar que la acción no borra el registro y no se presenta como verificación automática de seguridad.
- [ ] UI-04 — En Actividad, navegar por Resumen, Seguimiento, Importar, Eventos y Privacidad y borrado; verificar que queda claro que una ventana temporal no crea una fuente de datos ni instala un agente.
- [ ] UI-05 — Comprobar que las pestañas funcionan con teclado y que el contenido sigue siendo legible en los tres temas y en una ventana estrecha.
- [ ] UI-06 — Navegar por las cinco secciones con la misma anchura de ventana; verificar que el marco no se ensancha ni se contrae bruscamente, que los márgenes/títulos/paneles/controles mantienen la escala y que las tablas no ensanchan toda la página. Repetir en escritorio y móvil.
- [ ] UI-07 — Confirmar que logo y nombre NetSentinel permanecen fijos en las cinco secciones; que el título y la descripción cambian con la sección, la navegación ocupa el ancho disponible y el selector de temas no domina la cabecera.
- [ ] UI-08 — Ejecutar `python scripts/check_responsive_ui.py --screenshots`; verificar las cinco páginas en los quince tamaños predeterminados, revisar el informe JSON y abrir las capturas. Registrar SO, navegador, commit y fallos; la prueba automática no sustituye la valoración visual humana.
- [ ] UI-09 — Con dos capturas sintéticas o de prueba autorizadas, comparar una subred compartida, una captura con errores/alcance limitado y otra sin la misma subred. Confirmar que los cambios de IP y los equipos no observados se distinguen, que las fuentes/avisos se muestran y que la interfaz no presenta la ausencia como desconexión.
- [ ] UI-10 — Abrir el historial de un monitor con comprobaciones correctas, fallidas sin latencia y períodos sin registros. Verificar que el gráfico distingue cada estado, conserva los huecos temporales y aclara que un intervalo vacío no confirma una caída. Abrir «Ver detalle por intervalo» con teclado; comprobar que cada fecha, latencia y recuento se entiende sin hover y está disponible para lector de pantalla. Revisar también la exportación CSV del mismo período.

**Evidencia interfaz:** fecha/versión/commit, temas probados, páginas visitadas, resultado y fallos observados.

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

## Revisión manual de interfaz — 15 de octubre de 2026

El responsable del proyecto confirmó que las pruebas manuales locales del recorrido de la aplicación fueron satisfactorias. Las observaciones restantes corresponden a la jerarquía visual, la estructura de navegación y la usabilidad; no se informó una falla funcional bloqueante.

- **Alcance aprobado:** revisión local de interfaz y uso general.
- **Resultado:** aprobado por el responsable del proyecto para continuar la revisión del PR #111.
- **Entorno y commit exactos:** no registrados en el mensaje de confirmación.
- **Pendiente:** esta confirmación no reemplaza los recorridos de instalación, persistencia, seguridad, extensión ni la matriz completa de Windows/macOS/Linux y Chrome/Edge.

## Registro de sesiones

Añadir una fila por sesión; si falla, dejarlo como bloqueado y abrir/vincular un issue.

| Fecha | Versión/commit | OS / navegador | IDs ejecutados | Resultado | Issue / evidencia |
|---|---|---|---|---|---|
| — | — | — | — | Pendiente de primera ejecución | — |
