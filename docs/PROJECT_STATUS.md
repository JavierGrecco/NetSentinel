# Estado actual del proyecto

**Actualizado:** 22 de octubre de 2026 (Argentina/Córdoba)  
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

**HEAD documental verificado:** [`60557638e89dcae377437263d74d2ff5e4ff9b1e`](https://github.com/JavierGrecco/NetSentinel/commit/60557638e89dcae377437263d74d2ff5e4ff9b1e).

Las tres ejecuciones de GitHub Actions terminaron correctamente sobre ese SHA:

- **CI:** 18/18 trabajos correctos, incluidos Python en Windows, macOS y Linux, y la comprobación de interfaz adaptable en Chromium. [Ver ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39879018894).
- **Security Analysis:** 2/2 correctos; auditoría de dependencias y CodeQL. [Ver ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39879019093).
- **Supply Chain Security:** detección de secretos y generación de wheel, SBOM y manifiesto de integridad correctas. La firma de procedencia se omitió porque esta ejecución no corresponde a una publicación de release. [Ver ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39879018893).

Esto demuestra el resultado automatizado de ese SHA; **no equivale a una aceptación manual** ni autoriza a declarar estable la versión. La prueba real en macOS, el recorrido de los doce pasos, el uso exclusivo de datos sintéticos y la evaluación manual con teclado/lector de pantalla siguen pendientes.

## Higiene del repositorio

No hay PR abiertas de integración. La [auditoría de ramas](BRANCH_AUDIT_2026-10.md) documenta las 174 referencias encontradas, las ramas duplicadas o reemplazadas y el contenido exclusivo recuperado a `main`.

La clasificación de ramas ya está reconciliada: 150 referencias coinciden exactamente con heads de PR fusionadas directamente en `main`, 2 corresponden a PR apiladas en el laboratorio consolidado luego absorbido por #189, 15 están asociadas a PR cerradas sin merge y 6 no tienen PR. No se borró ninguna referencia. El ruleset no define los checks requeridos ni expresa explícitamente su alcance; la limpieza física queda en pausa hasta resolverlo administrativamente. Ver [auditoría completa](BRANCH_AUDIT_2026-10.md).

## Controles administrativos de GitHub

La lectura del ruleset activo `rules` (ID `25281660`) muestra reglas de borrado, force-push, PR y checks obligatorios, pero la lista de checks está vacía; las aprobaciones requeridas son 0 y la condición `ref_name` devuelve `include: []`, `exclude: []`, sin declarar explícitamente el alcance esperado. No hay actores de bypass. Además, la API de ramas informa `protected: false` para `main`; el endpoint de protección clásica no estuvo disponible para la integración de revisión (403). Esto no permite afirmar que CI/seguridad sean requisitos de merge ni validar el alcance efectivo del ruleset. La administración debe resolverlo y probarlo antes de declarar completa la protección o eliminar referencias.

**Consecuencia:** no asumir que CI, seguridad y cadena de suministro son checks requeridos para fusionar. La configuración en Settings necesita revisión administrativa y una prueba real con una PR. La limpieza física de ramas queda en pausa hasta confirmar el alcance de la regla de borrado y comprobar los SHA candidatos. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73) y [auditoría de ramas](BRANCH_AUDIT_2026-10.md).

## Puertas pendientes antes de declarar estable la versión 0.10.0

1. Cerrar CI, seguridad y cadena de suministro sobre el HEAD exacto que se usará para probar.
2. Ejecutar el recorrido guiado completo usando solamente la base de datos y los archivos sintéticos de la guía; registrar los 12 resultados, las notas y el SHA probado.
3. Revisar de forma real el teclado, el lector de pantalla, la claridad de las instrucciones, el cambio entre módulos y los tamaños de escritorio/móvil.
4. Revisar el informe final y confirmar que los fallos y pasos no comprobados no aparecen como aprobados; registrar evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
5. Corregir y verificar administrativamente el ruleset de `main` según [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73): patrón explícito y checks requeridos reales.
6. Solo después de confirmar el alcance del ruleset, completar la eliminación controlada de ramas históricas según [BRANCH_AUDIT_2026-10.md](BRANCH_AUDIT_2026-10.md).

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
