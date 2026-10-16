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

## NetSentinel Forense — primera entrega

**Estado: pendiente de revisión manual propia.** La confirmación de uso local de NetSentinel Red no aprueba esta pantalla ni sus nuevas operaciones.

- [ ] FOR-MAN-01 — Abrir/cerrar caso, listar datos y rechazar identificadores duplicados.
- [ ] FOR-MAN-02 — Registrar recepción con timestamp ISO-8601 y offset explícito; rechazar timestamp sin offset.
- [ ] FOR-MAN-03 — Registrar nombre de archivo sin ruta, procedencia, tamaño opcional y hash declarado con su fuente.
- [ ] FOR-MAN-04 — Comparar una copia sintética: coincidencia, diferencia y fallo de lectura; el hash declarado no se sobrescribe.
- [ ] FOR-MAN-05 — Probar rutas y nombres no válidos; confirmar que se rechazan, que el intento queda en el historial con un marcador genérico y que el texto enviado/ruta privada no aparece en respuestas ni registros.
- [ ] FOR-MAN-06 — Confirmar que la API bloquea nuevas recepciones/comprobaciones tras cerrar el caso y que el historial previo se mantiene.
- [ ] FOR-MAN-07 — Confirmar la navegación Red/Forense, selección de temas, foco de teclado y lectura en ventana estrecha.
- [ ] FOR-MAN-08 — En macOS/Linux, probar con permisos de carpeta inicialmente abiertos y confirmar que se restrinjan a `0700`; confirmar que un fallo al restringir permisos bloquea la lectura. En Windows, revisar el comportamiento bajo las ACL locales.

**Registro de la revisión Forense:**
- Fecha y zona horaria:
- Persona que prueba:
- Commit exacto:
- Sistema operativo y versión:
- Navegador y versión:
- Resultado global: pendiente / aprobado / bloqueado:
- Observaciones visuales y de uso:
- Enlaces a evidencia sanitizada o issues:

Usar únicamente archivos y casos sintéticos. No adjuntar rutas privadas, datos personales ni evidencia real. Si algo falla, abrir un issue con pasos para reproducirlo; no marcar la casilla afectada como completada.

## Registro de sesiones

Añadir una fila por sesión; si falla, dejarlo como bloqueado y abrir/vincular un issue.

| Fecha | Versión/commit | OS / navegador | IDs ejecutados | Resultado | Issue / evidencia |
|---|---|---|---|---|---|
| — | — | — | — | Pendiente de primera ejecución | — |

## NetSentinel Forense — revisión manual pendiente (PR #157)

Usar un directorio de datos aislado y **archivos sintéticos**. No probar con evidencia real ni reutilizar datos de otra instalación. Seguir también la [guía manual de Forense](FORENSIC_MANUAL_TEST.md). Estas casillas solo se marcan con el resultado de una prueba real y la información del entorno arriba indicada.

- [ ] **FOR-01 — Alta y trazabilidad:** crear un caso de prueba con referencia de autoridad, objetivo y alcance; comprobar que la operación y el nombre declarado del operador queden en la auditoría.
- [ ] **FOR-02 — Metadatos sin copiar evidencia:** registrar una pieza sintética y comprobar que se guarden los metadatos declarados sin subir ni copiar el contenido original ni persistir rutas completas.
- [ ] **FOR-03 — Hash correcto e incorrecto:** comparar una copia de trabajo con su SHA-256 de referencia correcto y con otro valor; confirmar que el resultado y el tamaño correspondan al archivo leído.
- [ ] **FOR-04 — Entradas inseguras y errores:** probar una ruta absoluta, traversal, nombre no portable, archivo ausente y enlace simbólico cuando el sistema lo permita. Confirmar mensajes entendibles y que la auditoría no exponga la ruta completa ni el nombre rechazado.
- [ ] **FOR-05 — Caso cerrado:** cerrar un caso y confirmar que no admita nuevas evidencias ni comparaciones, sin borrar el historial existente.
- [ ] **FOR-06 — Auditoría alterada:** exportar el manifiesto, comprobarlo con el verificador local y modificar una copia de prueba del JSON para confirmar que el verificador detecta el cambio. No presentar el digest como firma digital.
- [ ] **FOR-07 — Interfaz y accesibilidad:** navegar con teclado, probar foco y mensajes de estado, tema claro/oscuro, ventana estrecha y lector de pantalla disponible. Anotar navegador y versión.
- [ ] **FOR-08 — Revisión visual real:** revisar la pantalla en escritorio y ventana estrecha y adjuntar capturas sanitizadas; la ejecución automática de Chromium no reemplaza esta revisión humana.

**Registro de Forense:** commit exacto, sistema operativo y versión, versión de Python, navegador y versión, comandos utilizados, resultado de cada caso, problemas observados y enlaces a logs/capturas sanitizados. Todos los casos comienzan pendientes; no inferir aprobación manual a partir de CI.
