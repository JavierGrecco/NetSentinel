# Seguimiento del proyecto

> Esta es la nota breve para retomar el trabajo. El [roadmap](ROADMAP.md) contiene las tareas completas y la [matriz de validación](VALIDATION_MATRIX.md) guarda la evidencia de las pruebas reales.

**Actualizado:** 16 de octubre de 2026  
**Versión objetivo:** 0.10.0. Sigue en estabilización; no hay fecha prometida.

## Dónde estamos

NetSentinel continúa siendo una aplicación local. Estamos ordenando el código por responsabilidades sin cambiar la forma en que la usa la persona que la instala.

- **Main:** la última integración es el [merge de la PR #129](https://github.com/JavierGrecco/NetSentinel/commit/d15fe9e0218b441c27e1272096d2368a2bb32b27), que refuerza el control automático de dependencias de la fachada de Actividad. La regla evita que el módulo importe directamente persistencia o capacidades ajenas; las extracciones anteriores de inventario, monitorización y seguridad también siguen integradas.
- **Modularización y límites integrados:** [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), [PR #115](https://github.com/JavierGrecco/NetSentinel/pull/115), [PR #116](https://github.com/JavierGrecco/NetSentinel/pull/116), [PR #118](https://github.com/JavierGrecco/NetSentinel/pull/118), [PR #120](https://github.com/JavierGrecco/NetSentinel/pull/120), [PR #121](https://github.com/JavierGrecco/NetSentinel/pull/121), [PR #123](https://github.com/JavierGrecco/NetSentinel/pull/123), [PR #125](https://github.com/JavierGrecco/NetSentinel/pull/125), [PR #127](https://github.com/JavierGrecco/NetSentinel/pull/127) y [PR #129](https://github.com/JavierGrecco/NetSentinel/pull/129) están fusionadas. La PR #129 pasó CI multiplataforma, dependencias mínimas, empaquetado, CodeQL, auditoría de dependencias, SBOM y manifiesto en el SHA `34792aa0838f520b29792e38060071d2bcc14100`.
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
- La [PR #118](https://github.com/JavierGrecco/NetSentinel/pull/118) integró la separación de las rutas HTTP de DNS y TLS en `tools_dns.py` y `tools_tls.py`, manteniendo `tools.py` como punto de composición. Las rutas y métodos existentes se conservan.
- La [PR #120](https://github.com/JavierGrecco/NetSentinel/pull/120) separó las cabeceras defensivas, CSP e identificación de solicitudes del middleware Host/Origin. Se preservó la interfaz histórica y se agregó una comprobación para detectar definiciones superiores duplicadas.
- Las cabeceras defensivas y la CSP quedaron separadas del middleware de host/origen en `api/security_headers.py`. Se eliminó una definición duplicada de `_error_response` y se agregó una regla automática para que funciones o clases de nivel superior no puedan quedar duplicadas y ocultarse entre sí.
- La [PR #121](https://github.com/JavierGrecco/NetSentinel/pull/121) integró la separación de la API de Actividad en lectura/exportación, sesiones/ingreso, importación CSV, borrado selectivo y retención. Los modelos están en un módulo compartido y `api/activity.py` mantiene el punto de composición junto con los imports históricos.
- La [PR #123](https://github.com/JavierGrecco/NetSentinel/pull/123) extrajo el manejo de errores de validación a `api/validation_errors.py`. `api/error_handling.py` mantiene el registro global de errores HTTP/inesperados y reexporta los nombres históricos; los tests comprueban que los valores sensibles de una petición inválida no aparezcan en respuesta, logs ni diario.
- La [PR #125](https://github.com/JavierGrecco/NetSentinel/pull/125) dividió `monitoring_repository.py` en configuración de monitores, consultas analíticas, transiciones y notificaciones. La fachada histórica sigue disponible y `record_monitor_check` conserva el guardado de checks, incidentes y eventos dentro de una única transacción.
- La [PR #127](https://github.com/JavierGrecco/NetSentinel/pull/127) separó las consultas de solo lectura del inventario y dejó las escrituras en `inventory_repository.py`. `record_scan` conserva una única transacción para la exploración, los dispositivos, direcciones, observaciones y eventos.
- La [PR #129](https://github.com/JavierGrecco/NetSentinel/pull/129) agregó una regla explícita sobre las dependencias de `activity_tracking.py` y una prueba negativa para detectar futuras importaciones directas a `database.py`.
- Se unificó el selector de apariencia en todas las páginas, con temas Oscuro, Medio y Claro persistentes entre secciones. Monitorización y Actividad se dividieron en sectores navegables; se aclaró cuándo corren las comprobaciones y qué requiere una fuente de telemetría real.
- Se reorganizó la cuadrícula del inventario: Actividad reciente queda junto a la tabla y Diagnóstico e Historial aprovechan la segunda fila. En pantallas más estrechas, las secciones se apilan y la tabla conserva su desplazamiento horizontal. Hay una prueba automatizada para mantener esta estructura; la revisión visual real de este cambio sigue pendiente.
- Se reajustó la jerarquía tras la primera prueba visual en macOS: la marca NetSentinel queda fija, el título y la descripción identifican la sección actual, la navegación ocupa todo el ancho y las tarjetas de tema pasan a un formato compacto. Se agregaron pruebas para mantener esta distribución en las cinco páginas.
- Se reemplazó el desplegable de apariencia por tres tarjetas visuales con iconos (Oscuro, Medio y Claro) en las cinco secciones. La selección sigue guardándose, se comparte entre páginas y se sincroniza si se cambia desde otra pestaña. El control usa radios accesibles y contempla el foco de teclado y pantallas pequeñas.
- Se detectaron y corrigieron diferencias de estructura visual entre páginas: Inventario/Hallazgos usaban hasta 1400 px de ancho, Monitorización/Actividad 1180 px y Herramientas 850 px. La capa compartida fija un marco de 1320 px, tipografía, paneles, separaciones, controles y márgenes adaptables; se agregaron pruebas para evitar que cada sección vuelva a separarse del patrón común. Falta recorrerlo visualmente en navegador real.
- Se documentó el camino para observar actividad sin instalar un agente en cada dispositivo: utilizar registros DNS o flujos del router/firewall, si el equipo los ofrece. La integración central requiere un adaptador específico y todavía no está implementada; la guía aclara los límites de visibilidad de HTTPS, VPN y DNS cifrado.
- Hallazgos ahora ofrece la acción de marcar un dispositivo como conocido, separada de marcar el evento como revisado, con una confirmación que aclara los límites de esa decisión.
- Se agregaron pruebas automatizadas para comprobar los recursos frontend compartidos y los controles de navegación por sectores. La validación visual real en macOS todavía está pendiente.

Para las próximas integraciones, revisar CI, Security y Supply Chain sobre el SHA exacto que se vaya a integrar. Los resultados de un commit anterior no validan automáticamente uno nuevo.

## Qué falta cerrar primero

1. **Probar en macOS.** Seguir [la guía de prueba manual](MACOS_MANUAL_TEST.md), revisar también la nueva distribución del Inventario en pantalla ancha y estrecha, guardar el SHA probado y registrar resultado y evidencia en la [matriz](VALIDATION_MATRIX.md). El seguimiento está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
2. **Comprobar la persistencia.** Verificar actualización de bases existentes, copia, restauración e integridad SQLite con escenarios representativos.
3. **Completar pruebas manuales multiplataforma.** Registrar recorridos reales de Windows y Linux, y de Chrome/Edge. No inferir resultados manuales a partir de CI.
4. **Verificar la protección de main.** Confirmar desde los ajustes de GitHub que los cambios requieren PR y que los controles necesarios son obligatorios. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
5. **Revisar dependencias y preparar la versión.** No declarar estable la 0.10.0 hasta cerrar la puerta de salida de la Fase 0 del roadmap.

## Regla para dar una tarea por terminada

Que el código exista o que CI pase no demuestra por sí solo que funcione en un equipo real. Si el roadmap exige una prueba manual, el resultado y su evidencia tienen que quedar registrados. Si algo falla, anotá cómo reproducirlo y vinculá un issue; no marques la tarea como completa.

## Trabajo separado: NetSentinel Forense

Forense se desarrolla con marca, navegación y flujos propios, sin incorporarse todavía al `main`. La primera entrega incluye registro de casos, metadatos de evidencia, auditoría y comparación de SHA-256 sobre una copia autorizada. No equivale a una cadena de custodia certificada. La [PR #113](https://github.com/JavierGrecco/NetSentinel/pull/113) debe seguir en borrador hasta terminar la guía [FORENSIC_MANUAL_TEST.md](FORENSIC_MANUAL_TEST.md) y registrar el resultado; la validación manual de Red no sustituye esa revisión.
