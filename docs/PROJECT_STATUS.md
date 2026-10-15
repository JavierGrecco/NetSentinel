# Seguimiento del proyecto

> Una guía corta para saber dónde estamos y cómo retomar el trabajo. El detalle de las tareas y sus criterios está en el [roadmap](ROADMAP.md).

**Actualizado:** 15 de octubre de 2026  
**Versión objetivo:** 0.10.0 (todavía en estabilización; no hay fecha prometida).

## Dónde estamos

Estamos ordenando el código por responsabilidades sin cambiar el modo de uso local de NetSentinel. La mayor parte del trabajo de modularización está reunida en la [PR #111](https://github.com/JavierGrecco/NetSentinel/pull/111), que sigue **abierta y en borrador**.

- **Rama de trabajo:** `refactor/activity-persistence-modules`.
- **Último commit técnico revisado:** [`6f807f7`](https://github.com/JavierGrecco/NetSentinel/commit/6f807f756e1c144ee0514f6ee05ce72d9d7b3f86).
- **Importante:** `main` sigue en [`a671df7`](https://github.com/JavierGrecco/NetSentinel/commit/a671df74376ec635e1233f1da045f01dca77199a). Los cambios de la PR aún no están en `main`.

En el commit técnico indicado, las verificaciones automáticas terminaron bien: [CI, 17 trabajos](https://github.com/JavierGrecco/NetSentinel/actions/runs/38748130166), [seguridad, 2 trabajos](https://github.com/JavierGrecco/NetSentinel/actions/runs/38748130200) y [cadena de suministro, 3 trabajos](https://github.com/JavierGrecco/NetSentinel/actions/runs/38748129804). Las pruebas de la extensión del navegador también pasaron: 47 de 47.

Estas ejecuciones corresponden al commit técnico anterior a esta nota. Después de cada cambio, revisá siempre los checks del commit más nuevo que muestra la PR.

## Qué se hizo

- Se separaron partes de la API, la aplicación, la base SQLite, la actividad, la monitorización y los diagnósticos en módulos más pequeños.
- Se sacó el JavaScript de las pantallas a archivos separados y se comprobó que se incluya en el paquete.
- Se mejoraron los mensajes y el registro de errores para que sea más fácil entender qué falló.
- Se endurecieron las validaciones de DNS, TLS y los datos de actividad del navegador.
- Se añadieron pruebas para impedir que registros antiguos sin validar se exporten tal cual y para comprobar que la limpieza no borre una navegación que llega al mismo tiempo.

También se corrigió un fallo de pruebas durante este trabajo. La corrección ya pasó en la revisión automática indicada arriba.

## Qué falta cerrar primero

1. **Revisar la modularización completa.** Comprobar los límites entre módulos y que las rutas, respuestas y comportamientos existentes sigan siendo compatibles.
2. **Reforzar las pruebas de SQLite.** Cubrir actualización del esquema, operaciones atómicas y recuperación a partir de una copia de seguridad antes de mover más código de persistencia.
3. **Hacer las pruebas manuales reales.** Probar instalación y uso en Windows, macOS y Linux, además de Chrome/Edge para la extensión, y anotar el resultado en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md). El seguimiento operativo está en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
4. **Comprobar los controles de GitHub.** Confirmar la protección efectiva de `main` según el [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73) y revisar por separado las actualizaciones de dependencias pendientes.
5. **Recién entonces decidir si la PR está lista para revisión final, integración y preparación de la versión 0.10.0.** No alcanza con que el código compile o CI pase si quedan pruebas manuales sin evidencia.

## Próximo paso recomendado

Empezar por las pruebas de actualización, copia y restauración de SQLite. Son importantes para proteger los datos existentes y para poder seguir modularizando con menos riesgo.

## Cómo mantener esta nota útil

- Actualizá esta página cuando cambien de forma importante el estado, el commit validado, los bloqueos o el siguiente paso.
- Usá el [roadmap](ROADMAP.md) para las tareas y sus criterios de aceptación; usá [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) para anotar las pruebas manuales reales.
- No marques una tarea como terminada solo porque exista el código o pase CI. Si una prueba falla, dejá el resultado, los pasos para repetirla y el issue relacionado.
- Evitá porcentajes generales: es más claro decir qué está listo, qué falta y qué evidencia lo confirma.
