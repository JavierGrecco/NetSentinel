# Seguimiento del proyecto

> Esta es la nota breve para retomar el trabajo. El [roadmap](ROADMAP.md) contiene las tareas completas y la [matriz de validación](VALIDATION_MATRIX.md) guarda la evidencia de las pruebas reales.

**Actualizado:** 15 de octubre de 2026  
**Versión objetivo:** 0.10.0. Sigue en estabilización; no hay fecha prometida.

## Dónde estamos

NetSentinel continúa siendo una aplicación local. Estamos ordenando el código por responsabilidades sin cambiar la forma en que la usa la persona que la instala.

- **Main:** [a4d96dd](https://github.com/JavierGrecco/NetSentinel/commit/a4d96ddfd7fb40cd88425a875cd7bfe147bf34ff). Ya incorpora el saneamiento reforzado de URLs de la extensión y de la importación CSV.
- **Rama de modularización:** `refactor/activity-persistence-modules`.
- **Pull request de trabajo:** [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), abierta y en borrador. Todavía no está integrada en `main`.
- **Preparación de pruebas en macOS:** [guía paso a paso](MACOS_MANUAL_TEST.md) para descargar esta rama, instalar las dependencias de forma aislada, ejecutar las pruebas y recorrer la aplicación sin reutilizar datos de otra instalación.

## Qué se mejoró en esta ronda

- La base SQLite se separó en conexión, esquema y repositorios por responsabilidad. Se añadió una transacción explícita para que un error deshaga los cambios parciales, una prueba que comprueba ese rollback y otra que verifica que los registros de actividad antiguos se conserven al ampliar el esquema.
- El cálculo de hashes de la política CSP ahora reconoce cierres de etiquetas `script` con espacios o atributos inesperados; se añadieron pruebas para esos casos.
- La clasificación de errores SQLite ya no interpreta un mensaje como causa confirmada si el motor devolvió un código nativo distinto o no reconocido. Se mantiene la compatibilidad por texto en runtimes antiguos sin código nativo y se agregó una regresión.
- La rotación del diario de errores también restringe los permisos de los archivos archivados, para no conservar permisos abiertos heredados de versiones anteriores.
- Se preparó la rama de modularización para conservar la mejora de privacidad de la PR #110, evitando que el refactor restaure el saneamiento anterior.
- Se corrigió un pequeño error de formato en la lista de funciones del README.

Antes de integrar la PR, hay que revisar CI, Security y Supply Chain sobre el SHA exacto que se va a integrar. Los resultados de un commit anterior no validan automáticamente uno nuevo.

## Qué falta cerrar primero

1. **Probar en macOS.** Seguir [la guía de prueba manual](MACOS_MANUAL_TEST.md), guardar el SHA probado y registrar resultado y evidencia en la [matriz](VALIDATION_MATRIX.md). El seguimiento está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
2. **Comprobar la persistencia.** Verificar actualización de bases existentes, copia, restauración e integridad SQLite con escenarios representativos.
3. **Completar pruebas manuales multiplataforma.** Registrar recorridos reales de Windows y Linux, y de Chrome/Edge. No inferir resultados manuales a partir de CI.
4. **Verificar la protección de main.** Confirmar desde los ajustes de GitHub que los cambios requieren PR y que los controles necesarios son obligatorios. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
5. **Revisar dependencias y preparar la versión.** No declarar estable la 0.10.0 hasta cerrar la puerta de salida de la Fase 0 del roadmap.

## Regla para dar una tarea por terminada

Que el código exista o que CI pase no demuestra por sí solo que funcione en un equipo real. Si el roadmap exige una prueba manual, el resultado y su evidencia tienen que quedar registrados. Si algo falla, anotá cómo reproducirlo y vinculá un issue; no marques la tarea como completa.