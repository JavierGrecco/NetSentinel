# Estado del proyecto — NetSentinel

**Corte de estado:** 27 de noviembre de 2026.  
**Rama canónica:** `main`. Última integración funcional verificada: `a6088f5ed2239b530d07b484eb60bf8024e1a91f`.

## Situación verificada

- **Estado del producto:** desarrollo activo. La versión 0.10.0 no se declara estable: continúan pendientes la aceptación operativa integral, instalaciones limpias, restauración manual, accesibilidad con tecnologías de asistencia y la protección efectiva de `main`.
- **Última integración funcional:** PR #200, correlación temporal Zeek en Hallazgos, squash commit [`a6088f5ed2239b530d07b484eb60bf8024e1a91f`](https://github.com/JavierGrecco/NetSentinel/commit/a6088f5ed2239b530d07b484eb60bf8024e1a91f). Incluye la sincronización con el núcleo semántico CSV/Zeek de #212, la procedencia `blocked` de #222, la correlación, los ajustes visuales de Actividad y pruebas de regresión adicionales.
- **PR #222 — procedencia de `blocked`:** integrada en `main` mediante [`6d71604`](https://github.com/JavierGrecco/NetSentinel/commit/6d71604fb4ca1613d68439e632a62001c36d2fbe). BPR-01–BPR-08 se cerraron mediante pruebas automatizadas de API/CSV/Chromium, reimportación y migración/backup/restauración SQLite; no se afirma una instalación manual local.
- **PR #200 — correlación temporal Zeek:** integrada en `main` mediante [`a6088f5`](https://github.com/JavierGrecco/NetSentinel/commit/a6088f5ed2239b530d07b484eb60bf8024e1a91f). El HEAD de la PR `d7b57ada501696c64f0fb76335fdbbd3f561ac69` pasó CI 19/19, Security Analysis 2/2 y Supply Chain 2/2; la firma de procedencia se omitió de forma esperada al no ser un release. Chromium verificó 135/135 casos de nueve páginas en quince tamaños. La prueba temporal acepta ±300 segundos y rechaza ±301; Hallazgos conserva UID, origen, delta y enlace a Actividad sin afirmar causalidad.
- **PR #231 — instalación del artefacto:** integrada en `main` mediante `fdc5ce43435b7a4fa0def8c7300ec1f0d445cd7f`. La CI pasó 22/22, Security 2/2 y Supply Chain 2 trabajos aplicables en el HEAD de PR `ade8ec02edc172d3cc38cd227764d7583235cbec`. Añade un smoke test que construye el wheel, lo instala en un venv nuevo, arranca la aplicación desde fuera del checkout y comprueba health/cabeceras, páginas, estáticos, API inicial y exportación con datos temporales en Ubuntu, Windows y macOS. Es aceptación automatizada del artefacto, no prueba humana de instalación, actualización o restauración.
- **PR #233 — integración navegador de la extensión MV3:** integrada en `main` mediante [`f06feb067dc36264ab9362b4a9a56b213a03fda5`](https://github.com/JavierGrecco/NetSentinel/commit/f06feb067dc36264ab9362b4a9a56b213a03fda5). En el HEAD probado `ce28791dd32bc2c575777cdd6f110b323d60a3eb`, CI 22/22, Security 2/2 y Supply Chain 2 trabajos aplicables aprobaron. El job Chromium carga la extensión Manifest V3, verifica apagado por defecto/opt-in, captura sintética de páginas y búsquedas, saneamiento, exclusiones, exportación CSV, borrado y opt-out; las solicitudes HTTP/HTTPS se interceptan y se abortan las no permitidas. Los workflows de push sobre `f06feb0` también pasaron CI 22/22, Security 2/2 y Supply Chain con dos trabajos aplicables. No sustituye la aceptación humana en Chrome/Edge.
- **Corrección visual de Actividad:** los estados de procedencia `blocked` se presentan como texto informativo, no como chips con borde. Una regresión Chromium comprueba que la celda no contiene elementos `.tag`. El selector de temas Oscuro, Medio y Claro permanece disponible.
- **CI posterior al merge:** sobre el commit integrado `a6088f5ed2239b530d07b484eb60bf8024e1a91f`, los workflows `push` también finalizaron correctamente: CI 19/19 ([run 46073568765](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073568765)), Security Analysis 2/2 ([run 46073568777](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073568777)) y Supply Chain 2 trabajos exitosos ([run 46073568823](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073568823)); la firma de procedencia se omitió como corresponde para una PR sin release.
- **Laboratorio de aceptación:** el asistente integrado contiene 13 pasos, incluido Hallazgos–Zeek. La ejecución de Chromium valida páginas y tamaños, pero no constituye una sesión humana de aceptación ni una revisión de accesibilidad con lector de pantalla.
- **Ramas remotas:** después de integrar PR #233, el workflow de borrado automático terminó correctamente y el inventario remoto mostró únicamente `main`; no quedaron ramas auxiliares activas.
- **Gobernanza de `main`:** el ruleset #25281660 está Active pero sigue sin patrón de inclusión, sin checks requeridos y con cero aprobaciones requeridas; además la API indica `protected: false`. No protege efectivamente `main`. La corrección requiere una persona administradora desde Settings; ver [GITHUB_SETUP.md](GITHUB_SETUP.md) e issue #73.
- **Forense:** casos, hashes, auditoría y borradores de informes siguen siendo experimentales. No son una cadena de custodia validada ni sustituyen procedimientos institucionales.
- **Alcance pendiente de investigación:** #197 sigue abierto para cubrir casos adicionales como IP reasignada/ambigua, timestamps inválidos, importaciones repetidas, faltantes y exportación reproducible. La PR #200 cerró solo el primer tramo Zeek.
- **Seguimiento temporal:** [issue #219](https://github.com/JavierGrecco/NetSentinel/issues/219). M0 continúa abierto por la configuración administrativa de protección y la aceptación integral 0.10.0.

Las secciones históricas posteriores se conservan como fotografías fechadas y no representan el estado vivo.



## Histórico: fotografía de main — 3 de noviembre de 2026

- **Rama canónica:** `main`, HEAD `d8b6a64214f8168d361fe62af38d37c728331575`. Esta fotografía no implica que las PR abiertas estén integradas.
- **Estado del producto:** desarrollo activo. No declarar 0.10.0 estable hasta completar la aceptación manual integral, la recuperación de datos y la revisión de accesibilidad.
- **PR #209 — navegación del laboratorio:** integrada en `main` mediante squash en [`ca9c4d9`](https://github.com/JavierGrecco/NetSentinel/commit/ca9c4d9644d99f98988475bf04692ef04373f743). Los accesos de CSV/Zeek llevan a Actividad → Importar.
- **PR #210 — mantenimiento de dependencias:** integrada en `main` mediante squash en [`d8b6a64`](https://github.com/JavierGrecco/NetSentinel/commit/d8b6a64214f8168d361fe62af38d37c728331575). Consolida siete actualizaciones revisadas e incorpora fixtures MaxMind City/ASN.
- **PR #208 — presentación y documentación:** abierta, fuera de Draft. HEAD anterior `487dfe06cc9f14095b44881a169303d00e63968f`; último resultado observado: 21 checks exitosos, 1 omisión esperada, 1 job macOS cancelado y 1 job macOS en cola, sin fallos. Se está refrescando el estado documental en esta misma rama; no reutilizar esos resultados para el nuevo SHA. No modifica runtime.
- **PR #212 — registro semántico para CSV/Zeek:** abierta, fuera de Draft. HEAD `f89c7654904ae9cd243a545477cbe2b610263151`, basada en el `main` consolidado. Última consulta: 17 checks exitosos, 1 omisión esperada, 1 en curso y 5 en cola, sin fallos. Ubuntu Python 3.10–3.14 pasó con 903 pruebas por versión; Windows Python 3.11–3.14, con 894 aprobadas y 9 omitidas por versión. Faltan Windows 3.10, Chromium y los cinco jobs macOS. [PR #212](https://github.com/JavierGrecco/NetSentinel/pull/212) · [issue #211](https://github.com/JavierGrecco/NetSentinel/issues/211).
- **PR #200 — correlación Zeek en Hallazgos:** continúa como Draft. HEAD `f58af31afba49fe3232f1dd5ce013910fbc42be0`; la rama tiene como base el `main` consolidado `d8b6a64214f8168d361fe62af38d37c728331575). Última consulta: 22 checks exitosos, 1 omisión esperada y 1 job macOS en cola, sin fallos. Mantener Draft hasta actualizarla con #212, volver a validar el SHA final y realizar una sola aceptación manual integral. [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200).
- **Issue #211 — normalización semántica:** dejó de ser solo una propuesta: la primera implementación está en revisión en #212. Su alcance actual es Actividad CSV/Zeek, no un motor universal de Monitorización, Inventario o Forense. La especificación detalla qué se implementó y qué queda pendiente.
- **PR abiertas:** #208 (documentación), #212 (catálogo semántico) y #200 (correlación Zeek, Draft). #209 y #210 ya están integradas.
- **Ramas remotas:** la última auditoría en vivo contabilizó 188 referencias, incluida `main`. No se borraron ramas en esta etapa. El snapshot CSV es histórico y no debe utilizarse como inventario vivo.
- **Higiene de ramas:** la auditoría anterior identificó 156 ramas cuyo SHA coincidía exactamente con una PR fusionada, 2 integradas mediante QA, 15 PR cerradas sin merge y 6 sin PR asociada. Cada referencia debe volver a verificarse por SHA y contenido exclusivo antes de cualquier limpieza.
- **Gobernanza de GitHub:** la protección efectiva de `main`, los checks obligatorios y el borrado automático de ramas se posponen para una revisión administrativa posterior. No se han modificado esos ajustes en esta etapa. La integración debe seguir siendo secuencial, con SHA y CI verificados.
- **Aceptación manual:** pendiente. No se harán pruebas parciales repetidas. El recorrido completo se realizará una sola vez cuando #212 esté integrada y #200 haya incorporado esos cambios, con CI completa en el SHA final.

**Vigencia:** fotografía de GitHub del 3/11/2026 (Argentina/Córdoba). Para validar cualquier cambio, prevalece siempre el HEAD y los checks actuales de esa PR; este documento es una fotografía editorial.

## Revisión comparativa y dirección técnica

El [análisis comparativo de 23/10/2026](COMPETITIVE_ANALYSIS_2026-10-23.md) prioriza precisión, contexto e interoperabilidad frente a imitar la captura profunda de un SIEM/NDR. La línea actual refuerza la calidad de los datos y la trazabilidad de su interpretación antes de ampliar la captura o el alcance operativo.

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
