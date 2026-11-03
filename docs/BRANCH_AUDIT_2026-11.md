# Auditoría de ramas remotas — 3 de noviembre de 2026

**Repositorio:** [JavierGrecco/NetSentinel](https://github.com/JavierGrecco/NetSentinel)  
**Rama canónica:** `main`  
**HEAD de main consultado:** [`299360f0`](https://github.com/JavierGrecco/NetSentinel/commit/299360f088f1eb92c766d29e448133ce3608142a)  
**Método:** lectura de las dos páginas de la API de ramas y de las 201 PR disponibles en las tres páginas consultadas. La clasificación exige coincidencia exacta entre nombre de rama y SHA actual de la PR; no basta con que una PR tenga el mismo nombre de rama.

## Inventario

La fotografía inicial registra **190 ramas remotas**: `main` y **189 ramas adicionales**. Ese corte se tomó después de abrir la PR #209 y antes de consolidar las actualizaciones de mantenimiento en la PR #210. La auditoría del 22/10/2026 registraba 174 ramas incluyendo `main`; el corte inicial del 3/11 registró 190, un aumento neto de 16. Las cifras y la distribución que siguen describen ese corte, no un inventario vivo.

Distribución por prefijo de las 189 ramas fuera de `main`:

| Prefijo | Cantidad |
|---|---:|
| `docs` | 42 |
| `fix` | 35 |
| `refactor` | 27 |
| `feat` | 24 |
| `security` | 16 |
| `test` | 14 |
| `chore` | 7 |
| `dependabot` | 7 |
| `privacy` | 4 |
| `qa` | 3 |
| `arch` | 2 |
| `ci` | 2 |
| `reliability` | 2 |
| `research` | 2 |
| `feature` | 1 |
| `lab` | 1 |

## Clasificación por evidencia de PR

| Grupo | Cantidad | Qué significa | Acción |
|---|---:|---|---|
| Cabeza de PR fusionada directamente a `main` | 156 | El SHA actual de la rama coincide exactamente con el HEAD de una PR fusionada cuyo destino era `main`. | Candidata a limpieza, no borrado automático. |
| Cabeza de PR integrada en el laboratorio QA | 2 | La PR fue fusionada a `qa/expert-acceptance-consolidated-2026-10`; la integración del laboratorio llegó después a `main`. | Verificar el vínculo con #189 antes de limpiar. |
| PR abierta | 10 | Hay una PR abierta cuyo HEAD coincide con el SHA de la rama. | Mantener. |
| PR cerrada sin merge | 15 | El HEAD coincide con una PR cerrada, pero no hay merge directo asociado a esa rama. Algunas tareas fueron reemplazadas o incorporadas por una integración posterior. | Revisar contenido exclusivo; no borrar por el estado de la PR. |
| Sin PR asociada | 6 | No se encontró una PR cuyo nombre y HEAD coincidan exactamente con la referencia actual. | Revisar árbol y commits manualmente. |
| **Total** | **189** | | |

El CSV [BRANCH_SNAPSHOT_2026-11.csv](BRANCH_SNAPSHOT_2026-11.csv) registra cada nombre, SHA, prefijo, clasificación, PR asociadas y acción recomendada. Es una fotografía del 3/11, no una instrucción de borrado. La fila de `docs/portfolio-presentation-2026-11` conserva el SHA observado al capturar el inventario; la rama fue consolidada posteriormente para revisar esta PR y su SHA actual ya no coincide con esa fotografía. No uses ese campo como referencia viva ni como motivo para borrar la rama.

## Reconciliación posterior a la consolidación — 3 de noviembre de 2026

Una consulta posterior a la apertura de la PR #210 devuelve **188 ramas remotas**: `main` y **187 ramas adicionales**. Tres referencias de Dependabot incluidas en el snapshot inicial ya no aparecen en el listado actual. Esta diferencia no se interpreta como una autorización para borrar otras ramas ni se ejecutó una limpieza masiva. El CSV conserva correctamente la fotografía histórica de 190 referencias; no debe actualizarse a mano para simular un inventario en tiempo real.

La consulta actual devuelve **cuatro PR abiertas**:

| PR | Tipo | Estado consultado |
|---|---|---|
| [#208](https://github.com/JavierGrecco/NetSentinel/pull/208) | Presentación, documentación y excepciones Gitleaks acotadas | Abierta, lista para revisión; 23 checks exitosos y 1 omisión esperada |
| [#209](https://github.com/JavierGrecco/NetSentinel/pull/209) | Corrección del acceso directo a Actividad → Importar y del test harness | Abierta, lista para revisión; 23 checks exitosos y 1 omisión esperada |
| [#210](https://github.com/JavierGrecco/NetSentinel/pull/210) | Consolidación de siete actualizaciones de dependencias y acciones | Abierta, lista para revisión; 23 checks exitosos y 1 omisión esperada |
| [#200](https://github.com/JavierGrecco/NetSentinel/pull/200) | Correlación temporal de contexto Zeek en hallazgos | Abierta, Draft |

Las siete actualizaciones originales #201–#207 se agruparon para revisión conjunta en #210; no deben seguir contabilizándose como siete PR abiertas ni como siete funcionalidades pendientes. Los resultados de checks corresponden a los SHA de cada PR y no validan automáticamente un merge posterior.

## Pull requests abiertas en la fotografía inicial

Se encontraron **10 PR abiertas**:

| PR | Tipo | Estado |
|---|---|---|
| [#209](https://github.com/JavierGrecco/NetSentinel/pull/209) | Corrección del asistente: Actividad → Importar y test harness | 23/23 checks requeribles; pendiente de integración |
| [#208](https://github.com/JavierGrecco/NetSentinel/pull/208) | Presentación y documentación; README, arquitectura y auditorías | Gitleaks pasó tras acotar 11 fingerprints del CSV; CI final en curso |
| [#200](https://github.com/JavierGrecco/NetSentinel/pull/200) | Correlación temporal de contexto Zeek en hallazgos | Draft |
| [#201–#207](https://github.com/JavierGrecco/NetSentinel/pulls) | Siete actualizaciones automatizadas de dependencias y GitHub Actions | Abiertas |

Las diez PR no representan diez funciones de producto sin terminar. #200 es una línea funcional de producto; #209 es una corrección del asistente; #208 es presentación/documentación y #201–#207 son mantenimiento de dependencias/acciones.

## Lectura de la auditoría anterior

La revisión del 22/10 concluyó que muchas ramas correspondían a PR fusionadas y que la limpieza física debía esperar a la confirmación de las reglas de GitHub. La clasificación actual confirma que 158 ramas tienen una ruta de integración exacta (156 directamente a `main` y 2 mediante QA). Las 15 PR cerradas sin merge y las 6 ramas sin PR continúan requiriendo revisión individual.

La cifra histórica de 150 PR fusionadas directamente y 2 integradas por QA quedó desactualizada: el snapshot actual identifica 156 directas y 2 mediante QA. Se conservan las referencias históricas para explicar cómo se llegó hasta aquí.

## Revisión de las siete PR de mantenimiento

Se inspeccionaron sus cambios y los checks de sus SHA actuales contra la base consultada (`main` en `299360f0`). La firma de procedencia aparece omitida en las PR, como corresponde a cambios que no son publicaciones de release.

| PR | Actualización | Resultado de CI y seguridad consultado |
|---|---|---|
| [#201](https://github.com/JavierGrecco/NetSentinel/pull/201) | Playwright 1.64.1 | 23 checks correctos; 1 omisión esperada. |
| [#202](https://github.com/JavierGrecco/NetSentinel/pull/202) | pytest 9.2.0 | 23 checks correctos; 1 omisión esperada. |
| [#203](https://github.com/JavierGrecco/NetSentinel/pull/203) | httpx2 2.14.0 | 23 checks correctos; 1 omisión esperada. |
| [#204](https://github.com/JavierGrecco/NetSentinel/pull/204) | maxminddb 3.2.0 | 23 checks correctos; 1 omisión esperada. Es una actualización mayor de la dependencia opcional GeoIP; revisar compatibilidad funcional antes de integrarla. |
| [#205](https://github.com/JavierGrecco/NetSentinel/pull/205) | setuptools 84.2.1 | 23 checks correctos; 1 omisión esperada. La tarea macOS/Python 3.10 cancelada inicialmente fue reintentada y terminó correctamente. |
| [#206](https://github.com/JavierGrecco/NetSentinel/pull/206) | CodeQL Actions 4.39.1 | 23 checks correctos; 1 omisión esperada. |
| [#207](https://github.com/JavierGrecco/NetSentinel/pull/207) | actions/setup-python 7.1.0 | 23 checks correctos; 1 omisión esperada. |

Estas PR son mantenimiento de dependencias y automatización; no son proyectos funcionales separados ni módulos sin terminar. Sus resultados corresponden a los SHA de sus respectivas PR y no se deben trasladar automáticamente a otro commit.

**Decisión:** no fusionar estas PR en bloque. La protección efectiva de `main` aún no está comprobada; después de resolverla, integrar cambios pequeños de forma controlada y repetir la validación sobre cada nuevo HEAD. La actualización mayor de maxminddb merece además una revisión focalizada de GeoIP.

## Gobernanza y seguridad antes de borrar

La API de ramas sigue informando `protected: false` para `main`. Además, la lectura del ruleset `rules` (ID `25281660`) del 3/11/2026 confirma `enforcement: active`, pero `conditions.ref_name.include` y `exclude` están vacíos, `required_status_checks` es `[]` y la regla PR exige 0 aprobaciones. La documentación oficial de GitHub especifica que al menos un patrón de `include` debe coincidir y reconoce `~DEFAULT_BRANCH` como selector válido; por tanto, el ruleset no identifica `main` ni demuestra una barrera de integración efectiva. [Referencia de GitHub](https://docs.github.com/en/rest/repos/rules).

**Decisión:** no ejecutar limpieza física en esta etapa. Primero resolver la protección de la rama principal y confirmar reglas de borrado. Después revisar cada SHA candidato contra este CSV y la PR que lo originó.

## Procedimiento de limpieza futuro

1. Actualizar el inventario inmediatamente antes de cada lote de borrado.
2. Reconsultar el SHA remoto y verificar que no cambió desde el snapshot.
3. Confirmar que no hay PR abierta ni trabajo posterior en esa referencia.
4. Para ramas integradas mediante QA, seguir la cadena hasta la PR que incorporó el laboratorio a `main`.
5. Para PR cerradas sin merge y ramas sin PR, comprobar que el contenido exclusivo está preservado o que la rama es descartable por una razón documentada.
6. Eliminar lotes pequeños y verificar el resultado después de cada lote.

No usar eliminación masiva por prefijo ni borrar referencias solo por antigüedad.
