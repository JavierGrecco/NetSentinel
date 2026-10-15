# Seguimiento del proyecto

> Esta es la nota breve para retomar el trabajo. El [roadmap](ROADMAP.md) contiene las tareas completas y la [matriz de validación](VALIDATION_MATRIX.md) guarda la evidencia de las pruebas reales.

**Actualizado:** 15 de octubre de 2026  
**Versión objetivo:** 0.10.0. Sigue en estabilización; no hay fecha prometida.

## Dónde estamos

NetSentinel continúa siendo una aplicación local. Estamos ordenando el código por responsabilidades sin cambiar la forma en que la usa la persona que la instala.

- **Main:** la última integración de código es el [merge de la PR #116](https://github.com/JavierGrecco/NetSentinel/commit/7247e478213158821b61ca51aa87ecb3698fc21b), que dejó en `main` la base modular y las separaciones de API de Monitorización e Inventario.
- **Modularización integrada:** [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), [PR #115](https://github.com/JavierGrecco/NetSentinel/pull/115) y [PR #116](https://github.com/JavierGrecco/NetSentinel/pull/116) están fusionadas. Sus checks de CI pasaron en los SHA revisados; la PR #111 también pasó Security y Supply Chain.
- **NetSentinel Forense:** [PR #113](https://github.com/JavierGrecco/NetSentinel/pull/113) sigue abierta y en borrador, separada de Red. La CI pasó para el SHA `24060d592322bc01c45754cba51c60427a85ec97` ([ejecución #38807621209](https://github.com/JavierGrecco/NetSentinel/actions/runs/38807621209)); falta ejecutar y registrar su revisión manual con un archivo sintético antes de integrarla.
- **Preparación de pruebas en macOS:** [guía paso a paso](MACOS_MANUAL_TEST.md) para instalar las dependencias de forma aislada, ejecutar las pruebas y recorrer la aplicación sin reutilizar datos de otra instalación.

## Revisión manual local

El responsable del proyecto confirmó el 15 de octubre de 2026 que los recorridos manuales locales de NetSentinel Red fueron satisfactorios. Los comentarios pendientes se centraban en presentación, organización visual y facilidad de uso, no en un bloqueo funcional. Esa confirmación queda registrada, pero no identifica sistema operativo, navegador ni SHA probado.

La confirmación no identifica el sistema operativo, el navegador ni el commit exacto probado, así que no se marcan como aprobados los recorridos específicos de Windows, macOS, Linux o la extensión. Esos resultados siguen registrándose por separado en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## Qué se mejoró en esta ronda

- La base SQLite se separó en conexión, esquema y repositorios por responsabilidad. Se añadió una transacción explícita para que un error deshaga los cambios parciales, una prueba que comprueba ese rollback y otra que verifica que los registros de actividad antiguos se conserven al ampliar el esquema.
- El cálculo de hashes de la política CSP ahora reconoce cierres de etiquetas `script` con espacios o atributos inesperados; se añadieron pruebas para esos casos.
- La clasificación de errores SQLite ya no interpreta un mensaje como causa confirmada si el motor devolvió un código nativo distinto o no reconocido. Se mantiene la compatibilidad por texto en runtimes antiguos sin código nativo y se agregó una regresión.
- La rotación del diario de errores también restringe los permisos de los archivos archivados, para no conservar permisos abiertos heredados de versiones anteriores.
- Se preparó la rama de modularización para conservar la mejora de privacidad de la PR #110, evitando que el refactor restaure el saneamiento anterior.
- Se corrigió un pequeño error de formato en la lista de funciones del README.
- La API de Monitorización quedó separada en gestión de monitores/incidentes/avisos, informes/exportaciones y diagnóstico, conservando las rutas y respuestas públicas.
- La API de Inventario quedó separada en consulta y cambios de activos/eventos, descubrimiento local y exportaciones. El router histórico permanece como punto de composición y las pruebas siguen los módulos responsables.
- Ambas extracciones están integradas en `main` mediante las PR #115 y #116. El control de arquitectura comprueba las dependencias permitidas para evitar que vuelvan a mezclarse capacidades.
- Se unificó el selector de apariencia en todas las páginas, con temas Oscuro, Medio y Claro persistentes entre secciones. Monitorización y Actividad se dividieron en sectores navegables; se aclaró cuándo corren las comprobaciones y qué requiere una fuente de telemetría real.
- Se reajustó la jerarquía tras la primera prueba visual en macOS: la marca NetSentinel queda fija, el título y la descripción identifican la sección actual, la navegación ocupa todo el ancho y las tarjetas de tema pasan a un formato compacto. Se agregaron pruebas para mantener esta distribución en las cinco páginas.
- Se reemplazó el desplegable de apariencia por tres tarjetas visuales con iconos (Oscuro, Medio y Claro) en las cinco secciones. La selección sigue guardándose, se comparte entre páginas y se sincroniza si se cambia desde otra pestaña. El control usa radios accesibles y contempla el foco de teclado y pantallas pequeñas.
- Se detectaron y corrigieron diferencias de estructura visual entre páginas: Inventario/Hallazgos usaban hasta 1400 px de ancho, Monitorización/Actividad 1180 px y Herramientas 850 px. La capa compartida fija un marco de 1320 px, tipografía, paneles, separaciones, controles y márgenes adaptables; se agregaron pruebas para evitar que cada sección vuelva a separarse del patrón común. Falta recorrerlo visualmente en navegador real.
- Se documentó el camino para observar actividad sin instalar un agente en cada dispositivo: utilizar registros DNS o flujos del router/firewall, si el equipo los ofrece. La integración central requiere un adaptador específico y todavía no está implementada; la guía aclara los límites de visibilidad de HTTPS, VPN y DNS cifrado.
- Hallazgos ahora ofrece la acción de marcar un dispositivo como conocido, separada de marcar el evento como revisado, con una confirmación que aclara los límites de esa decisión.
- Se agregaron pruebas automatizadas para comprobar los recursos frontend compartidos y los controles de navegación por sectores. La validación visual real en macOS todavía está pendiente.

Para las próximas integraciones, revisar CI, Security y Supply Chain sobre el SHA exacto que se vaya a integrar. Los resultados de un commit anterior no validan automáticamente uno nuevo.

## Qué falta cerrar primero

1. **Probar en macOS.** Seguir [la guía de prueba manual](MACOS_MANUAL_TEST.md), guardar el SHA probado y registrar resultado y evidencia en la [matriz](VALIDATION_MATRIX.md). El seguimiento está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
2. **Comprobar la persistencia.** Verificar actualización de bases existentes, copia, restauración e integridad SQLite con escenarios representativos.
3. **Completar pruebas manuales multiplataforma.** Registrar recorridos reales de Windows y Linux, y de Chrome/Edge. No inferir resultados manuales a partir de CI.
4. **Verificar la protección de main.** Confirmar desde los ajustes de GitHub que los cambios requieren PR y que los controles necesarios son obligatorios. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
5. **Revisar dependencias y preparar la versión.** No declarar estable la 0.10.0 hasta cerrar la puerta de salida de la Fase 0 del roadmap.

## Regla para dar una tarea por terminada

Que el código exista o que CI pase no demuestra por sí solo que funcione en un equipo real. Si el roadmap exige una prueba manual, el resultado y su evidencia tienen que quedar registrados. Si algo falla, anotá cómo reproducirlo y vinculá un issue; no marques la tarea como completa.

## Trabajo separado: NetSentinel Forense

Forense se desarrolla con marca, navegación y flujos propios, sin incorporarse todavía al `main`. La primera entrega incluye registro de casos, metadatos de evidencia, auditoría y comparación de SHA-256 sobre una copia autorizada. No equivale a una cadena de custodia certificada. La [PR #113](https://github.com/JavierGrecco/NetSentinel/pull/113) debe seguir en borrador hasta terminar la guía [FORENSIC_MANUAL_TEST.md](FORENSIC_MANUAL_TEST.md) y registrar el resultado; la validación manual de Red no sustituye esa revisión.
