# Seguimiento del proyecto

> Esta es la nota breve para retomar el trabajo. El [roadmap](ROADMAP.md) contiene las tareas completas y la [matriz de validación](VALIDATION_MATRIX.md) guarda la evidencia de las pruebas reales.

**Actualizado:** 15 de octubre de 2026  
**Versión objetivo:** 0.10.0. Sigue en estabilización; no hay fecha prometida.

## Dónde estamos

NetSentinel continúa siendo una aplicación local. Estamos ordenando el código por responsabilidades sin cambiar la forma en que la usa la persona que la instala.

- **Main:** [a4d96dd](https://github.com/JavierGrecco/NetSentinel/commit/a4d96ddfd7fb40cd88425a875cd7bfe147bf34ff). Ya incorpora el saneamiento reforzado de URLs de la extensión y de la importación CSV.
- **Rama de modularización:** `refactor/activity-persistence-modules`.
- **Pull request de trabajo:** [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), abierta y en borrador. Todavía no está integrada en `main`.

## Qué se mejoró en esta ronda

- La base SQLite se separó en conexión, esquema y repositorios por responsabilidad. Se añadió una transacción explícita para que un error deshaga los cambios parciales, una prueba que comprueba ese rollback y otra que verifica que los registros de actividad antiguos se conserven al ampliar el esquema.
- El cálculo de hashes de la política CSP ahora reconoce cierres de etiquetas `script` con espacios o atributos inesperados; se añadieron pruebas para esos casos.
- Se preparó la rama de modularización para conservar la mejora de privacidad de la PR #110, evitando que el refactor restaure el saneamiento anterior.
- Se corrigió un pequeño error de formato en la lista de funciones del README.

Estos cambios están en revisión automática. Hay que mirar los controles del commit más reciente de la PR #111; no tomar como validación vigente los resultados de commits anteriores.

## Qué falta cerrar primero

1. **Comprobar la rama integrada.** Revisar que el saneamiento reforzado de URLs siga presente y que pasen CI, análisis de seguridad y cadena de suministro sobre el último commit.
2. **Probar la persistencia.** Verificar actualización de bases existentes, copia, restauración e integridad SQLite con escenarios representativos.
3. **Hacer las pruebas manuales.** Completar los recorridos en Windows, macOS y Linux, y en Chrome/Edge, dejando fecha, versión, commit y resultados en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md). El seguimiento está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
4. **Verificar la protección de main.** Confirmar desde los ajustes de GitHub que los cambios requieren PR y que los controles necesarios son obligatorios. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
5. **Revisar dependencias y preparar la versión.** No declarar estable la 0.10.0 hasta cerrar la puerta de salida de la Fase 0 del roadmap.

## Regla para dar una tarea por terminada

Que el código exista o que CI pase no demuestra por sí solo que funcione en un equipo real. Si el roadmap exige una prueba manual, el resultado y su evidencia tienen que quedar registrados. Si algo falla, anotá cómo reproducirlo y vinculá un issue; no marques la tarea como completa.
