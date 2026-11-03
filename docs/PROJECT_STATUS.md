# Estado actual del proyecto

## Fotografía vigente — 3 de noviembre de 2026

- **Rama canónica:** `main`, HEAD `299360f088f1eb92c766d29e448133ce3608142a` (23/10/2026).
- **Estado del producto:** desarrollo activo. No declarar la versión 0.10.0 estable hasta completar aceptación manual, recuperación de datos, revisión de accesibilidad y gobernanza.
- **PR #208 — presentación profesional:** abierta y lista para revisión. El HEAD documental `37a2822baffc2af0fb8c64eee2ff0098f5585a77` completó 23 checks exitosos y 1 omisión esperada (firma de procedencia, solo para releases), sin fallos. CI, Chromium, seguridad, Gitleaks, wheel, SBOM y manifiesto terminaron correctamente. Incluye el caso de estudio técnico, la consolidación de referencias y la adopción documentada del monolito modular como dirección arquitectónica. La PR no cambia el runtime; la aceptación manual del producto sigue pendiente. Este SHA es la última revisión completa registrada antes de la sincronización documental de este estado.
- **PR #209 — corrección de la guía:** abierta y lista para revisión. HEAD `a0b69b09a86919b5d837ea081ecc6e7fed984180`; 23 checks exitosos y 1 omisión esperada. Chromium pasó 135/135. El acceso directo abre Actividad en la pestaña Importar y el test harness reconoce los enlaces con fragmento.
- **PR #210 — dependencias:** abierta y lista para revisión. HEAD `5f7332cf13c0834ddc46e15d4bd446c316bd504f`; 23 checks exitosos y 1 omisión esperada. Consolida siete actualizaciones revisadas, incluye pruebas con lectores MaxMind reales y fixtures sintéticos City/ASN, y comprueba el extra GeoIP en la matriz Python 3.10–3.14. Es una actualización de mantenimiento, no una nueva funcionalidad de producto.
- **PR #200 — correlación Zeek:** continúa como Draft. El HEAD `996695e7fbd1f912af158b07ede332543ff4da98` completó 23 checks exitosos y 1 omisión esperada. No equivale a aceptación manual ni a integración en `main`.
- **Ramas remotas:** la consulta posterior a la consolidación devuelve **188 referencias**: `main` y 187 adicionales. El CSV registra una fotografía anterior de 190 referencias; tres referencias de Dependabot que figuraban en ese corte ya no aparecen. No usar el CSV como inventario vivo ni como instrucción de borrado.
- **PR abiertas:** cuatro: #200 (funcionalidad en Draft), #208 (documentación), #209 (corrección de la guía) y #210 (mantenimiento). Las siete actualizaciones originales #201–#207 están consolidadas en #210.
- **Gobernanza:** el ruleset `rules` (ID `25281660`) está activo, pero su condición `ref_name.include` está vacía, no exige checks y requiere cero aprobaciones. La API informa `protected: false` para `main`; no hay protección efectiva demostrada.
- **Checks de `main`:** el historial no está completamente verde. La última CI registrada para este HEAD terminó correctamente el 23/10; Security Analysis terminó correctamente el 2/11, pero la ejecución de Supply Chain Security del 2/11 terminó con fallo. También hubo dos fallos en ejecuciones programadas de Dependabot el 26/10 por respuestas del servicio/API. Estos resultados no deben mezclarse con las PR actuales, cuyos checks se consultaron por SHA y terminaron correctamente.

**Vigencia:** este resumen refleja consultas de GitHub realizadas el 3/11/2026 después de la consolidación del mantenimiento. Los apartados posteriores conservan decisiones, validaciones y cronología anteriores; cuando contienen SHA o resultados antiguos, son evidencia histórica y no sustituyen el estado de las PR.

**Actualizado:** 3 de noviembre de 2026 (Argentina/Córdoba). La aceptación manual integral sigue pendiente.

## Revisión comparativa y siguiente mejora

El [análisis comparativo de 23/10/2026](COMPETITIVE_ANALYSIS_2026-10-23.md) incorpora los dos NetSentinel de referencia y herramientas especializadas de observabilidad, análisis de tráfico, monitorización e inventario. La conclusión es priorizar la precisión, el contexto y la interoperabilidad en lugar de imitar la captura profunda de un SIEM/NDR. El documento es investigación estática; no agrega capacidades al runtime.

El primer tramo de esa línea está implementado en la [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200): añade contexto temporal de registros Zeek importados expresamente a hallazgos de inventario y disponibilidad, con límites de consulta y atribución documentados. Sigue como Draft y no forma parte de `main`; su CI verde no reemplaza la aceptación manual ni autoriza a presentarlo como funcionalidad integrada.

## Fuente única de trabajo

La [PR #189](https://github.com/JavierGrecco/NetSentinel/pull/189) se integró mediante squash en `main`. Reúne el explorador LAN histórico, la importación controlada de Zeek, el mapa mundial con GeoIP local opcional, NetSentinel Forense y el asistente de aceptación de 12 pasos con datos sintéticos.

Los módulos funcionales deben tomarse desde `main`, no desde las ramas de integración antiguas. La guía para preparar la prueba desde `origin/main` es [EXPERT_ACCEPTANCE_LAB.md](EXPERT_ACCEPTANCE_LAB.md); los archivos y casos de prueba están descritos en [MANUAL_TEST_SCENARIOS.md](MANUAL_TEST_SCENARIOS.md).

## Cambio más reciente en la experiencia de aceptación

La [PR #193](https://github.com/JavierGrecco/NetSentinel/pull/193) integró el asistente iterativo: navegación por fases alcanzadas, revisión directa de un paso desde el resumen, guardado y recuperación visible, y un desglose que separa correctos, fallidos, sin comprobar y pendientes. El commit de integración es [`a1bbeaa`](https://github.com/JavierGrecco/NetSentinel/commit/a1bbeaa27c98f85991ad07bc998651b269c739c6).

La [PR #194](https://github.com/JavierGrecco/NetSentinel/pull/194) amplió el recorrido Chromium para probar la interacción real: revisar un paso desde su fila, cambiar su resultado, preservar una nota y volver al resumen sin reiniciar el asistente. Sus checks sobre el SHA de la PR terminaron correctamente: CI 18/18, Chromium 135/135, análisis de seguridad y cadena de suministro. El commit de merge en `main` es [`1f1a7fce`](https://github.com/JavierGrecco/NetSentinel/commit/1f1a7fce22d366ed4a584eaff336993a1a92fb95).

## Mejora anterior de monitorización

Se recuperó la protección de reintentos que existía en una rama antigua pero no había llegado al supervisor ya modularizado:

- Si una excepción inesperada impide completar la comprobación de un monitor, se aplica retroceso exponencial de 2, 4, 8 segundos y sucesivos, con un máximo de 60 segundos.
- El retraso solo afecta al monitor que falla; los siguientes siguen ejecutándose.
- El estado se borra cuando el monitor vuelve a funcionar, se desactiva o se elimina.
- No se cambia el intervalo configurado ni se confunde una excepción inesperada con una respuesta de sonda que indica que el destino está caído.

La regresión está cubierta en `tests/test_monitoring.py` y documentada en [MONITORING.md](MONITORING.md).

## Historial de validación automatizada — hasta el 23/10/2026

**Fotografía posterior al merge documental #198:** sobre `3625709cf08f2c51a5c34d14db0b1a58bf1802b1`, en la consulta del 23/10/2026, CI llevaba 17/18 trabajos exitosos y el último trabajo de Python 3.12/macOS seguía activo ([CI](https://github.com/JavierGrecco/NetSentinel/actions/runs/39970706874)); Security Analysis terminó 2/2 ([seguridad](https://github.com/JavierGrecco/NetSentinel/actions/runs/39970706482)); Supply Chain Security terminó sin fallos, con 2 jobs aplicables correctos y la firma de procedencia omitida por no ser un release ([cadena de suministro](https://github.com/JavierGrecco/NetSentinel/actions/runs/39970706741)). Es una fotografía por SHA, no una aceptación manual ni un estado dinámico.

**Checks completos sobre el SHA de la PR #194** [`02bfbd73`](https://github.com/JavierGrecco/NetSentinel/commit/02bfbd733f67d67464d7d848816328e2da1565a4):

- **CI:** 18/18 trabajos correctos, incluida la matriz multiplataforma y Chromium con 135/135 comprobaciones. [Ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943281106).
- **Security Analysis:** 2/2 correctos. [Ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943281170).
- **Supply Chain Security:** detección de secretos y generación de paquete, SBOM y manifiesto de integridad correctas. La firma de procedencia se omite en ejecuciones que no corresponden a una publicación de release. [Ejecución](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943281097).

**Comprobaciones posteriores al merge:** en la consulta del 23/10/2026, los workflows de seguridad y cadena de suministro sobre el merge [`1f1a7fce`](https://github.com/JavierGrecco/NetSentinel/commit/1f1a7fce22d366ed4a584eaff336993a1a92fb95) ya habían terminado correctamente. CI tenía 17/18 trabajos completados; el trabajo responsive Chromium seguía ejecutándose. [CI posterior al merge](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943667918), [seguridad](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943667935) y [cadena de suministro](https://github.com/JavierGrecco/NetSentinel/actions/runs/39943667953). Antes de la prueba local hay que volver a consultar Actions para el SHA vigente, no inferir un resultado final a partir de esta fotografía.

Los checks automatizados no sustituyen la aceptación manual. El recorrido completo de doce pasos, la revisión visual, el teclado/lector de pantalla y las observaciones en escritorio y ventana estrecha siguen pendientes de registrar en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## Higiene del repositorio

La consulta del 3/11/2026 encontró **190 referencias remotas**: `main` y 189 ramas adicionales. La fotografía está en [BRANCH_SNAPSHOT_2026-11.csv](BRANCH_SNAPSHOT_2026-11.csv) y su clasificación en [BRANCH_AUDIT_2026-11.md](BRANCH_AUDIT_2026-11.md): 156 cabezas coinciden con PR fusionadas directamente a `main`, 2 se integraron mediante el laboratorio QA, 10 tienen PR abiertas, 15 corresponden a PR cerradas sin merge y 6 no tienen PR asociada.

Las diez PR abiertas se componen de siete actualizaciones automatizadas, #200 (correlación Zeek en Draft), #208 (presentación documental) y #209 (corrección de la guía). Las ramas de #208 y #209 deben conservarse hasta resolver sus PR. No se eliminó ninguna referencia en esta reorganización; la limpieza queda pausada hasta verificar la protección de `main` y revisar cada SHA candidato.

## Controles administrativos de GitHub

La lectura del ruleset activo `rules` (ID `25281660`) muestra reglas de borrado, force-push, PR y checks obligatorios, pero la lista de checks está vacía; las aprobaciones requeridas son 0 y la condición `ref_name` devuelve `include: []`, `exclude: []`, sin declarar explícitamente el alcance esperado. No hay actores de bypass. Además, la API de ramas informa `protected: false` para `main`; el endpoint de protección clásica no estuvo disponible para la integración de revisión (403). Esto no permite afirmar que CI/seguridad sean requisitos de merge ni validar el alcance efectivo del ruleset. La administración debe resolverlo y probarlo antes de declarar completa la protección o eliminar referencias.

**Consecuencia:** la gobernanza de `main` sigue pendiente: no dar por hecho que CI, seguridad y cadena de suministro bloquean el merge. Se necesita un cambio administrativo en Settings y una prueba real con una PR. Mantener en pausa la limpieza de ramas hasta confirmar el alcance de las reglas y verificar cada SHA candidato. Seguimiento: [issue #195](https://github.com/JavierGrecco/NetSentinel/issues/195), [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73) y [auditoría de ramas](BRANCH_AUDIT_2026-10.md).

## Puertas pendientes antes de declarar estable la versión 0.10.0

1. Cerrar CI, seguridad y cadena de suministro sobre el HEAD exacto que se usará para probar.
2. Ejecutar el recorrido guiado completo usando solamente la base de datos y los archivos sintéticos de la guía; registrar los 12 resultados, las notas y el SHA probado.
3. Revisar de forma real el teclado, el lector de pantalla, la claridad de las instrucciones, el cambio entre módulos y los tamaños de escritorio/móvil.
4. Revisar el informe final y confirmar que los fallos y pasos no comprobados no aparecen como aprobados; registrar evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
5. Corregir y verificar administrativamente el ruleset de `main` según [issue #195](https://github.com/JavierGrecco/NetSentinel/issues/195) y [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73): patrón explícito, checks requeridos reales y prueba de que se aplican a `main`.
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
