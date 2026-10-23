# Estado actual del proyecto

**Actualizado:** 23 de octubre de 2026  
**Rama canónica:** `main`  
**Última mejora funcional revisada:** [`91d5568a`](https://github.com/JavierGrecco/NetSentinel/commit/91d5568a89ee8aa2cc6b8881a404bb69e96461c1)  
**Estado:** integración consolidada; robustez de reintentos reforzada; aceptación local aún pendiente.

## Fuente única de trabajo

La [PR #189](https://github.com/JavierGrecco/NetSentinel/pull/189) se integró mediante squash en `main`. Reúne el explorador LAN histórico, la importación controlada de Zeek, el mapa mundial con GeoIP local opcional, NetSentinel Forense y el asistente de aceptación de 12 pasos con datos sintéticos.

Los módulos funcionales deben tomarse desde `main`, no desde las ramas de integración antiguas. La guía para preparar la prueba desde `origin/main` es [EXPERT_ACCEPTANCE_LAB.md](EXPERT_ACCEPTANCE_LAB.md); los archivos y casos de prueba están descritos en [MANUAL_TEST_SCENARIOS.md](MANUAL_TEST_SCENARIOS.md).

## Cambio funcional más reciente

Se recuperó la protección de reintentos que existía en una rama antigua pero no había llegado al supervisor ya modularizado:

- Si una excepción inesperada impide completar la comprobación de un monitor, se aplica retroceso exponencial de 2, 4, 8 segundos y sucesivos, con un máximo de 60 segundos.
- El retraso solo afecta al monitor que falla; los siguientes siguen ejecutándose.
- El estado se borra cuando el monitor vuelve a funcionar, se desactiva o se elimina.
- No se cambia el intervalo configurado ni se confunde una excepción inesperada con una respuesta de sonda que indica que el destino está caído.

La regresión está cubierta en `tests/test_monitoring.py` y documentada en [MONITORING.md](MONITORING.md).

## Validación automatizada

Sobre el commit funcional `91d5568a89ee8aa2cc6b8881a404bb69e96461c1`, en la última revisión:

- **Supply Chain Security:** correcto; detección de secretos, paquete, SBOM y manifiesto de integridad.
- **Security Analysis:** correcto; auditoría de dependencias y CodeQL.
- **CI multiplataforma y Chromium:** los trabajos restantes habían terminado correctamente o seguían en ejecución; no se observaba ningún fallo, pero faltaba confirmar el cierre del job de Python 3.13 en Ubuntu.

Ejecuciones: [CI](https://github.com/JavierGrecco/NetSentinel/actions/runs/39877440216), [Security Analysis](https://github.com/JavierGrecco/NetSentinel/actions/runs/39877440226) y [Supply Chain Security](https://github.com/JavierGrecco/NetSentinel/actions/runs/39877440195).

La prueba real en macOS, el teclado y el lector de pantalla siguen pendientes. Los checks automatizados no equivalen a una aceptación manual.

## Higiene del repositorio

No hay PR abiertas de integración. La [auditoría de ramas](BRANCH_AUDIT_2026-10.md) documenta las 174 referencias encontradas, las ramas duplicadas o reemplazadas y el contenido exclusivo recuperado a `main`.

La limpieza lógica de PR está terminada, pero las ramas remotas no se han borrado físicamente. La auditoría separa las referencias asociadas a PR fusionadas de las ramas cerradas sin merge y de las que no tienen PR; no se deben eliminar en bloque sin comprobar el SHA actual de cada referencia.

## Puertas pendientes antes de declarar estable la versión 0.10.0

1. Cerrar CI, seguridad y cadena de suministro sobre el HEAD exacto que se usará para probar.
2. Ejecutar el recorrido guiado completo usando solamente la base de datos y los archivos sintéticos de la guía; registrar los 12 resultados, las notas y el SHA probado.
3. Revisar de forma real el teclado, el lector de pantalla, la claridad de las instrucciones, el cambio entre módulos y los tamaños de escritorio/móvil.
4. Revisar el informe final y confirmar que los fallos y pasos no comprobados no aparecen como aprobados; registrar evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
5. Completar la eliminación controlada de ramas históricas según [BRANCH_AUDIT_2026-10.md](BRANCH_AUDIT_2026-10.md).
6. Comprobar los ajustes de protección de `main`; el seguimiento administrativo continúa en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).

GeoLite2-City no se descarga junto con las dependencias Python y necesita una instalación local autorizada. NetSentinel Forense sigue siendo experimental: un hash detecta cambios, pero no autentica por sí solo al operador ni crea una firma digital o un anclaje externo independiente.

## Documentación vigente

- [Laboratorio de aceptación](EXPERT_ACCEPTANCE_LAB.md)
- [Escenarios sintéticos](MANUAL_TEST_SCENARIOS.md)
- [Matriz de validación](VALIDATION_MATRIX.md)
- [Roadmap](ROADMAP.md)
- [Arquitectura](ARCHITECTURE.md)
- [Seguimiento de ramas](BRANCH_AUDIT_2026-10.md)
- [Explorador de topología LAN](NETWORK_OBSERVABILITY_CONSOLE.md)
- [Matriz de adopción de las referencias](REFERENCE_FEATURE_ADOPTION_MATRIX.md)
- [Plan de reingeniería de referencia (decisiones históricas)](REFERENCE_REENGINEERING_PLAN.md)
- [Alcance futuro de Forense](FORENSIC_MODE_PROPOSAL.md)
