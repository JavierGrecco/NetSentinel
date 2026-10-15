# Seguimiento del proyecto

> Esta es la nota breve para retomar el trabajo. El [roadmap](ROADMAP.md) contiene las tareas completas y la [matriz de validación](VALIDATION_MATRIX.md) guarda la evidencia de las pruebas reales.

**Actualizado:** 15 de octubre de 2026  
**Versión objetivo:** 0.10.0. Sigue en estabilización; no hay fecha prometida.

## Dónde estamos

NetSentinel continúa siendo una aplicación local. Estamos ordenando el código por responsabilidades sin cambiar la forma en que la usa la persona que la instala.

- **Main:** [a4d96dd](https://github.com/JavierGrecco/NetSentinel/commit/a4d96ddfd7fb40cd88425a875cd7bfe147bf34ff). Ya incorpora el saneamiento reforzado de URLs de la extensión y de la importación CSV.
- **Rama de modularización:** `refactor/activity-persistence-modules`.
- **Pull request de modularización base:** [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), abierta y lista para revisión formal, sin integrar todavía en `main`.
- **Preparación de pruebas en macOS:** [guía paso a paso](MACOS_MANUAL_TEST.md) para descargar esta rama, instalar las dependencias de forma aislada, ejecutar las pruebas y recorrer la aplicación sin reutilizar datos de otra instalación.

## Revisión manual local

El responsable del proyecto confirmó el 15 de octubre de 2026 que los recorridos manuales locales de **NetSentinel Red** fueron satisfactorios. Los comentarios pendientes eran de presentación, organización visual y facilidad de uso, no de un bloqueo funcional. Con esta confirmación, la PR #111 puede pasar a revisión formal. Esta aprobación manual no incluye la nueva pantalla ni el flujo de casos de NetSentinel Forense.

La confirmación no identifica el sistema operativo, el navegador ni el commit exacto probado, así que no se marcan como aprobados los recorridos específicos de Windows, macOS, Linux o la extensión. Esos resultados siguen registrándose por separado en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## Nueva línea de trabajo: NetSentinel Forense

Se está preparando una segunda área del producto, separada de las herramientas de Red. La rama `feat/forensics-workspace-foundation` parte de `refactor/activity-persistence-modules` para reutilizar la cabecera, los temas y la política de seguridad que se están revisando en la PR #111.

- La base está en revisión en la [PR #113](https://github.com/JavierGrecco/NetSentinel/pull/113): entrada `/forensics`, logos propios, cambio entre Red y Forense y guía [FORENSIC_MODE.md](FORENSIC_MODE.md).
- La PR #113 ya incluye un primer flujo persistente: apertura/cierre de casos, registro de metadatos de evidencia e historial de operaciones de solo anexado, con pruebas de API.
- La pantalla ya puede comparar una copia local elegida expresamente con el hash declarado por la fuente, guardar coincidencias/diferencias/fallos y mostrar el historial. La ruta completa se usa solo durante la operación y no se persiste.
- El resultado sigue siendo acotado: la coincidencia no prueba autenticidad, y un desacuerdo no demuestra por sí solo manipulación. El operador todavía es autodeclarado y la lectura puede modificar metadatos de acceso; la interfaz advierte que se debe usar una copia, no el soporte original.
- La revisión manual de la interfaz y la comparación SHA-256 de Forense sigue pendiente. La guía [FORENSIC_MANUAL_TEST.md](FORENSIC_MANUAL_TEST.md) describe el recorrido con archivos sintéticos. Los casos que se deben probar están listados en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
- La primera entrega completa se sigue en el [issue #114](https://github.com/JavierGrecco/NetSentinel/issues/114). Aún faltan un manifiesto consolidado, importadores y los informes; el flujo nuevo requiere una revisión manual propia.
- La primera entrega ya registra casos, elementos de evidencia y eventos de auditoría en SQLite; verifica SHA-256 calculado sobre una copia local, guarda resultado (coincide, difiere o falla) e historial. Es una verificación acotada de integridad, no un manifiesto de adquisición ni una cadena de custodia certificada.
- Siguen pendientes el manifiesto consolidado de adquisición, importadores/parser, informes forenses reproducibles, autenticación del operador y revisión manual con archivos sintéticos sobre el commit exacto. No hay adquisición de discos, memoria o móviles ni una prueba de autenticidad del origen a partir del hash.
- La CI pasó para el SHA `f3f467d64840949f2b32135f78fa2df0d52cc55f` ([ejecución #38806753361](https://github.com/JavierGrecco/NetSentinel/actions/runs/38806753361)), con la matriz Python 3.10–3.14 en Ubuntu/macOS/Windows, dependencias mínimas y empaquetado. Esto no valida la interfaz en un navegador real: la prueba manual de Forense con archivo sintético y el recorrido visual siguen pendientes.

## Qué se mejoró en esta ronda

- La base SQLite se separó en conexión, esquema y repositorios por responsabilidad. Se añadió una transacción explícita para que un error deshaga los cambios parciales, una prueba que comprueba ese rollback y otra que verifica que los registros de actividad antiguos se conserven al ampliar el esquema.
- El cálculo de hashes de la política CSP ahora reconoce cierres de etiquetas `script` con espacios o atributos inesperados; se añadieron pruebas para esos casos.
- La clasificación de errores SQLite ya no interpreta un mensaje como causa confirmada si el motor devolvió un código nativo distinto o no reconocido. Se mantiene la compatibilidad por texto en runtimes antiguos sin código nativo y se agregó una regresión.
- La rotación del diario de errores también restringe los permisos de los archivos archivados, para no conservar permisos abiertos heredados de versiones anteriores.
- Se preparó la rama de modularización para conservar la mejora de privacidad de la PR #110, evitando que el refactor restaure el saneamiento anterior.
- Se corrigió un pequeño error de formato en la lista de funciones del README.
- Se unificó el selector de apariencia en todas las páginas, con temas Oscuro, Medio y Claro persistentes entre secciones. Monitorización y Actividad se dividieron en sectores navegables; se aclaró cuándo corren las comprobaciones y qué requiere una fuente de telemetría real.
- Se reajustó la jerarquía tras la primera prueba visual en macOS: la marca NetSentinel queda fija, el título y la descripción identifican la sección actual, la navegación ocupa todo el ancho y las tarjetas de tema pasan a un formato compacto. Se agregaron pruebas para mantener esta distribución en las cinco páginas.
- Se reemplazó el desplegable de apariencia por tres tarjetas visuales con iconos (Oscuro, Medio y Claro) en las cinco secciones. La selección sigue guardándose, se comparte entre páginas y se sincroniza si se cambia desde otra pestaña. El control usa radios accesibles y contempla el foco de teclado y pantallas pequeñas.
- Se detectaron y corrigieron diferencias de estructura visual entre páginas: Inventario/Hallazgos usaban hasta 1400 px de ancho, Monitorización/Actividad 1180 px y Herramientas 850 px. La capa compartida fija un marco de 1320 px, tipografía, paneles, separaciones, controles y márgenes adaptables; se agregaron pruebas para evitar que cada sección vuelva a separarse del patrón común. Falta recorrerlo visualmente en navegador real.
- Se documentó el camino para observar actividad sin instalar un agente en cada dispositivo: utilizar registros DNS o flujos del router/firewall, si el equipo los ofrece. La integración central requiere un adaptador específico y todavía no está implementada; la guía aclara los límites de visibilidad de HTTPS, VPN y DNS cifrado.
- Hallazgos ahora ofrece la acción de marcar un dispositivo como conocido, separada de marcar el evento como revisado, con una confirmación que aclara los límites de esa decisión.
- Se agregaron pruebas automatizadas para comprobar los recursos frontend compartidos y los controles de navegación por sectores. La validación visual real en macOS todavía está pendiente.

Antes de integrar la PR, hay que revisar CI, Security y Supply Chain sobre el SHA exacto que se va a integrar. Los resultados de un commit anterior no validan automáticamente uno nuevo.

## Qué falta cerrar primero

1. **Probar en macOS.** Seguir [la guía de prueba manual](MACOS_MANUAL_TEST.md), guardar el SHA probado y registrar resultado y evidencia en la [matriz](VALIDATION_MATRIX.md). El seguimiento está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
2. **Comprobar la persistencia.** Verificar actualización de bases existentes, copia, restauración e integridad SQLite con escenarios representativos.
3. **Completar pruebas manuales multiplataforma.** Registrar recorridos reales de Windows y Linux, y de Chrome/Edge. No inferir resultados manuales a partir de CI.
4. **Verificar la protección de main.** Confirmar desde los ajustes de GitHub que los cambios requieren PR y que los controles necesarios son obligatorios. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
5. **Revisar dependencias y preparar la versión.** No declarar estable la 0.10.0 hasta cerrar la puerta de salida de la Fase 0 del roadmap.

## Regla para dar una tarea por terminada

Que el código exista o que CI pase no demuestra por sí solo que funcione en un equipo real. Si el roadmap exige una prueba manual, el resultado y su evidencia tienen que quedar registrados. Si algo falla, anotá cómo reproducirlo y vinculá un issue; no marques la tarea como completa.