# Estado actual del proyecto

## Fotografía vigente — 3 de noviembre de 2026

- **Rama canónica:** `main`, HEAD `d8b6a64214f8168d361fe62af38d37c728331575`.
- **Estado del producto:** desarrollo activo. No declarar la versión 0.10.0 estable hasta completar la aceptación manual integral, la recuperación de datos y la revisión de accesibilidad.
- **PR #209 — navegación del laboratorio:** integrada mediante squash en [`ca9c4d9`](https://github.com/JavierGrecco/NetSentinel/commit/ca9c4d9644d99f98988475bf04692ef04373f743). Los accesos CSV/Zeek llevan a Actividad → Importar y las regresiones reconocen el fragmento de navegación.
- **PR #210 — mantenimiento:** integrada mediante squash en [`d8b6a64`](https://github.com/JavierGrecco/NetSentinel/commit/d8b6a64214f8168d361fe62af38d37c728331575). Consolida siete actualizaciones revisadas; incluye fixtures MaxMind City/ASN y lectores reales en las pruebas multiplataforma.
- **PR #208 — presentación profesional y documentación:** abierta, fuera de Draft. HEAD `979b3800f81c37e0b74d087cb5d49940f78fade8`; 19 checks exitosos, 1 omisión esperada y 4 jobs macOS en cola, sin fallos conocidos en la última consulta. No declarar la validación completa hasta que terminen los cuatro jobs. Este HEAD incluye la propuesta `docs/SEMANTIC_DATA_NORMALIZATION.md`, que no modifica el runtime. [Ejecución de CI](https://github.com/JavierGrecco/NetSentinel/actions/runs/41674600264).
- **PR #200 — correlación Zeek en Hallazgos:** continúa como Draft. Su rama se actualizó sobre el `main` consolidado mediante `d341d4ca7ceb5354ec16c4508e47cdce2b8dfeb8`, que conserva el HEAD funcional anterior como segundo padre. La CI se relanzó para ese nuevo SHA y sigue en curso; los checks anteriores no lo validan. La aceptación manual integral continúa pendiente. [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200).
- **Issue #211 — normalización semántica:** diseño documentado, todavía sin implementación funcional. La primera entrega prevista es un catálogo determinista para Actividad/CSV/Zeek, con alias por fuente, sugerencias seguras de errores de tipeo, unidades explícitas y estados diferenciados para ausencias y ambigüedades. [Especificación](SEMANTIC_DATA_NORMALIZATION.md) · [seguimiento](https://github.com/JavierGrecco/NetSentinel/issues/211).
- **PR abiertas:** #208 (documentación) y #200 (funcionalidad en Draft). #209 y #210 ya están integradas.
- **Ramas remotas:** la última auditoría contabilizó 188 referencias (incluida `main`). Los merges no eliminan automáticamente las ramas fuente; no se ha borrado ninguna en esta consolidación. El snapshot CSV es histórico y no debe utilizarse como inventario vivo.
- **Higiene de ramas:** la auditoría previa identificó 156 ramas cuyo SHA coincidía exactamente con una PR fusionada, 2 integradas mediante QA, 15 PR cerradas sin merge y 6 sin PR asociada. Los siete cambios de Dependabot ya se consolidaron en #210; verificar cada referencia antes de incorporarla a un lote de limpieza.
- **Gobernanza de GitHub:** la protección efectiva de `main` y el borrado automático de ramas quedan pospuestos para una revisión posterior, como decisión administrativa. No se presentan como requisito funcional de NetSentinel ni como bloqueo para seguir desarrollando. Mientras tanto, cada integración se realiza secuencialmente con comprobación explícita de SHA y CI.
- **Checks posteriores al último merge:** sobre `d8b6a64214f8168d361fe62af38d37c728331575`, la última consulta encontró 17 checks exitosos, 1 omisión esperada y 5 jobs macOS en cola, sin fallos conocidos. No atribuir esos resultados a commits posteriores.

**Vigencia:** fotografía de GitHub del 3/11/2026 (Argentina/Córdoba). Los resultados y SHA anteriores se conservan como evidencia histórica y no sustituyen la comprobación del HEAD actual.

## Revisión comparativa y siguiente mejora

El [análisis comparativo de 23/10/2026](COMPETITIVE_ANALYSIS_2026-10-23.md) prioriza precisión, contexto e interoperabilidad frente a imitar la captura profunda de un SIEM/NDR.

La evolución inmediata de datos se sigue en el [issue #211](https://github.com/JavierGrecco/NetSentinel/issues/211). La especificación propone un registro semántico determinista y local, pero todavía no hay código ejecutable que lo implemente. La primera integración se hará después de consolidar las PR actuales y validar la correlación Zeek una sola vez sobre su HEAD actualizado.

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

## Higiene, consolidación y gobernanza — 3 de noviembre de 2026

La consulta viva de GitHub devuelve **188 ramas remotas** (`main` + 187). Hay cuatro PR abiertas: #208 (presentación), #209 (corrección del asistente), #210 (dependencias) y #200 (Zeek, Draft). Las otras **184 ramas no tienen una PR abierta asociada**; no significa que sean todas descartables.

La [auditoría de ramas](BRANCH_AUDIT_2026-11.md) conserva un snapshot de 190 referencias y clasifica las ramas por coincidencia exacta de SHA con PR fusionadas, cerradas o sin PR. El CSV es histórico. Antes de cualquier borrado, volver a consultar que la referencia exista, comparar su SHA y comprobar que su contenido exclusivo esté preservado. No eliminar por nombre, prefijo ni antigüedad.

El repositorio todavía tiene desactivado el ajuste **Automatically delete head branches** (`delete_branch_on_merge: false`). Después de corregir la protección de `main`, activarlo en **Settings → General → Pull Requests** para que las ramas fuente se eliminen automáticamente al fusionar una PR. La limpieza de referencias históricas debe hacerse en lotes pequeños según la auditoría.

El ruleset `rules` (ID `25281660`) aparece activo, pero su inclusión/exclusión de ramas está vacía, no tiene checks requeridos, exige cero aprobaciones y la API devuelve `protected: false` para `main`. El alcance no está demostrado. El conector de GitHub usado en esta revisión permite leer reglas y checks, pero no modificar configuraciones administrativas ni borrar referencias; una persona con permisos de administración debe completar ese paso desde Settings. Seguimiento: [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).

Los checks de la última CI de push registrada para `main` (`299360f0`, 23/10) terminaron correctamente. Security Analysis programada (2/11) también. Supply Chain Security programada (2/11) falló porque Gitleaks detectó dos cadenas de prueba en `scripts/check_responsive_ui.py`; la PR #208 contiene excepciones por fingerprint exacto y su escaneo pasó, pero el fallo no se considera resuelto hasta integrar y volver a ejecutar el workflow sobre `main`. Dos ejecuciones programadas de Dependabot del 26/10 fallaron y quedaron sustituidas por la validación conjunta de #210.

**Decisión de integración:** no fusionar PR en paralelo. El orden preparado es #208, #209 y #210, verificando `main` y sus workflows después de cada merge. Luego actualizar #200 sobre el nuevo `main`, resolver los cuatro archivos compartidos con #209 y revalidar. Mantener #200 en Draft hasta completar aceptación manual.

## Puertas pendientes antes de declarar estable la versión 0.10.0

1. Configurar el ruleset para `main`, exigir los 23 contextos verificados del [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73), mantener bloqueados borrado y force-push, y probar que los checks realmente bloqueen un merge cuando falten o fallen.
2. Activar **Automatically delete head branches** para las ramas fuente de PR fusionadas. No hacer limpieza histórica masiva.
3. Integrar #208, #209 y #210 de forma secuencial, con squash merge y verificación de checks sobre cada nuevo SHA de `main`.
4. Actualizar la PR #200 sobre el `main` resultante, resolver conflictos y repetir CI completa antes de salir de Draft.
5. Ejecutar una única aceptación manual integral sobre el SHA consolidado, registrar sistema operativo, versión de Python, resultados y observaciones en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md). Incluir importación CSV/Zeek, Hallazgos → Actividad, Forense, recuperación SQLite, teclado y lector de pantalla.
6. Capturar evidencia visual real y sanitizada desde la aplicación ejecutada sobre el SHA probado; no usar mockups ni capturas sintéticas de CI como prueba de producto.
7. No declarar 0.10.0 estable hasta completar instalación, actualización, recuperación de datos y aceptación manual en las plataformas previstas.

GeoLite2-City no se descarga junto con las dependencias Python y necesita una instalación local autorizada. NetSentinel Forense sigue siendo experimental: un hash detecta cambios, pero no autentica por sí solo al operador ni crea una firma digital o un anclaje externo independiente.

## Documentación vigente

- [Laboratorio de aceptación](EXPERT_ACCEPTANCE_LAB.md)
- [Escenarios sintéticos](MANUAL_TEST_SCENARIOS.md)
- [Matriz de validación](VALIDATION_MATRIX.md)
- [Roadmap](ROADMAP.md)
- [Arquitectura](ARCHITECTURE.md)
- [Seguimiento de ramas](BRANCH_AUDIT_2026-11.md)
- [Explorador de topología LAN](NETWORK_OBSERVABILITY_CONSOLE.md)
- [Matriz de adopción de las referencias](REFERENCE_FEATURE_ADOPTION_MATRIX.md)
- [Plan de reingeniería de referencia (decisiones históricas)](REFERENCE_REENGINEERING_PLAN.md)
- [Alcance futuro de Forense](FORENSIC_MODE_PROPOSAL.md)
