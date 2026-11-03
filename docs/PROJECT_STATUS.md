# Estado actual del proyecto

## Fotografía vigente — 3 de noviembre de 2026

- **Rama canónica:** `main`, HEAD `1add65657b39a8f6d50dfbe2b7ed7866b741b71a`. Este commit acota en `.gitleaksignore` once falsos positivos históricos detectados en el snapshot de ramas. Las excepciones se limitan al commit, archivo, regla y líneas exactas; no se desactiva el escaneo.
- **Estado del producto:** desarrollo activo. No declarar 0.10.0 estable hasta completar la aceptación manual integral, la recuperación de datos, la revisión de accesibilidad y la verificación de gobernanza.
- **PR #208 — presentación profesional:** integrada en `main` mediante squash en [`28a99a4`](https://github.com/JavierGrecco/NetSentinel/commit/28a99a4b04690d6cd788240dea01b5135ce9a937). El HEAD de la PR terminó su CI, análisis de seguridad y cadena de suministro correctamente. El commit de merge volvió a activar Gitleaks por identificadores del snapshot histórico; el commit posterior `1add656` añadió excepciones exactas y su escaneo de secretos terminó correctamente. La matriz global de ese último commit todavía debe completar su propia ejecución.
- **PR #209 — navegación del laboratorio:** integrada en `main` mediante squash en [`ca9c4d9`](https://github.com/JavierGrecco/NetSentinel/commit/ca9c4d9644d99f98988475bf04692ef04373f743). Los accesos de CSV/Zeek llevan directamente a Actividad → Importar.
- **PR #210 — mantenimiento de dependencias:** integrada en `main` mediante squash en [`d8b6a64`](https://github.com/JavierGrecco/NetSentinel/commit/d8b6a64214f8168d361fe62af38d37c728331575). Consolida siete actualizaciones revisadas e incorpora fixtures MaxMind City/ASN.
- **PR #212 — registro semántico para CSV/Zeek:** abierta, fuera de Draft. La rama `feat/semantic-data-registry-2026-11` ya incorpora el `main` actual. Implementa resolución determinista de cabeceras para CSV/Zeek, sugerencias no vinculantes, detección de colisiones, límites numéricos y pruebas adversariales. La revisión añadió controles para valores `float` extremos y para rangos enteros escritos como decimales o notación científica. La CI debe completarse sobre el HEAD exacto más reciente antes de integrar. [PR #212](https://github.com/JavierGrecco/NetSentinel/pull/212) · [issue #211](https://github.com/JavierGrecco/NetSentinel/issues/211).
- **PR #200 — correlación Zeek en Hallazgos:** continúa en Draft. El HEAD `f58af31` completó 23 trabajos aplicables y una omisión esperada; ese resultado corresponde a la rama anterior y no valida la actualización pendiente. Después de integrar #212, actualizar #200 sobre el nuevo `main`, reconciliar los tres archivos compartidos y ejecutar la matriz completa sobre el SHA resultante. [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200).
- **Alcance semántico:** la primera entrega se limita a Actividad CSV/Zeek. `inspect_field_value` sigue siendo una utilidad tipada; no reemplaza la validación autoritativa de `activity_event_service.py`. Monitorización, Inventario y Forense no utilizan todavía el catálogo.
- **Aceptación manual:** pendiente. No iniciar pruebas parciales repetidas. Ejecutar una única aceptación integral cuando #212 esté integrada y #200 se encuentre actualizada y validada, incluyendo importaciones CSV/Zeek, Hallazgos → Actividad, recuperación de datos, accesibilidad y revisión visual.
- **Gobernanza de GitHub:** la protección efectiva de `main` sigue sin estar demostrada. El ruleset está activo, pero su patrón de inclusión está vacío, no exige checks y la API devuelve `protected: false` para `main`. La configuración administrativa debe corregirse y probarse desde GitHub Settings; no declarar esta puerta resuelta.
- **Estado de CI:** el commit `1add656` ya no presenta el fallo de Gitleaks, pero su matriz completa todavía está en curso. No trasladar los resultados de los HEAD de las PR a commits posteriores ni marcar una validación como completa hasta que todos los checks aplicables del SHA final terminen.
- **Ramas históricas:** la auditoría documenta referencias candidatas y sus SHA de una fotografía anterior. No borrar ramas por nombre, prefijo o antigüedad; comprobar de nuevo PR de origen, SHA y contenido exclusivo antes de cualquier limpieza.

**Vigencia:** fotografía editorial del 3/11/2026 (Argentina/Córdoba). Para el estado operativo prevalecen el HEAD y los checks actuales de cada PR.

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
