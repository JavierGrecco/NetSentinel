# Auditoría y limpieza de ramas — 27 de noviembre de 2026

**Repositorio:** [JavierGrecco/NetSentinel](https://github.com/JavierGrecco/NetSentinel)  
**SHA de referencia para la comparación:** [956ceb442fe21aae3d965e55c1b13d3a7baa2060](https://github.com/JavierGrecco/NetSentinel/commit/956ceb442fe21aae3d965e55c1b13d3a7baa2060)  
**Rama canónica:** `main`. Los commits documentales posteriores descienden de ese SHA; por tanto, las ramas indicadas como ancestros siguen estando contenidas en el main actual, salvo que se hayan movido después de esta auditoría.  
**Método:** inventario paginado de refs, asociación exacta de heads de PR abiertas, agrupamiento por SHA, y comparación de cada rama sin PR contra `main`. Las comparaciones se realizaron en el corte del 27/11. Esta auditoría no interpreta antigüedad/nombre como prueba de integración.

## 1. Inventario actual

| Métrica | Resultado |
|---|---:|
| Ramas remotas totales, incluida main | **193** |
| Ramas distintas de main | **192** |
| SHA de commit distintos | **189** |
| Grupos de refs que comparten exactamente el mismo SHA | **4** |
| Ramas asociadas a PR abiertas | **5** |
| Ramas sin PR abierta | **187** |

PR abiertas que deben conservar sus ramas: #200 (correlación Zeek, Draft), #213 (CodeQL Actions), #215 (FastAPI), #217 (Playwright) y #218 (MaxMindDB). El antiguo head de #212 está en la sección de candidatas, porque la PR ya fue fusionada.

## 2. Candidatas seguras por ancestro de main

Las siguientes 20 ramas fueron comparadas con `main` y dieron **cero commits exclusivos respecto de main** (`behind_by = 0` desde el punto de vista de la comparación rama → main). Sus tips son ancestros del main de referencia. Se pueden borrar sin perder commits que no estén ya en main, después de verificar que ninguna PR nueva haya empezado a utilizarlas.

| Rama | SHA |
|---|---|
| `docs/activity-api-merge-status` | `8315f1f4998cde45fb4c8f04db094c37dd6272c9` |
| `docs/activity-facade-guard-status` | `cbfdc215d0e344318b04b21547461214b5c34e60` |
| `docs/current-state-reconciliation-2026-10` | `a55f449faec87127e871a990bfb8bd9cc0f6935d` |
| `docs/inventory-read-merge-status` | `db72a2b34059c74247587e03cd86e0b584097239` |
| `docs/monitoring-repository-merge-status` | `99765b0dc5deeb9f00009ca168d11ba4521241e5` |
| `docs/record-main-modularization` | `2a93af43049e78827495c4c4b04227837d497279` |
| `docs/status-after-dns-tls-merge` | `38277f69e10715ca8d1873e6c2c357427d394b3b` |
| `docs/validation-errors-merge-status` | `bf15095df76dbd9985b9573936be08813740c1ad` |
| `feat/guided-test-iterative-ux-2026-10` | `0b4f0ded098307b4621f25216acc88098d0d3f9e` |
| `refactor/activity-api-boundaries` | `e3a78ecb50238bdf5e94f793152f458a603a360e` |
| `refactor/activity-persistence-modules` | `53bac5784d8ba4daf3fb6e7c3a83775a51d9d558` |
| `refactor/architecture-activity-facade-boundary` | `34792aa0838f520b29792e38060071d2bcc14100` |
| `refactor/http-validation-errors` | `f04813f10d8f4cb23c323f33509913a34411d4d2` |
| `refactor/inventory-api-boundaries` | `9b8e2352c3b740c57c1301a3d4f80dd9b1277bc4` |
| `refactor/inventory-read-boundaries` | `61a833912e8a3ec8868be2b59583eacc056a4e1f` |
| `refactor/monitoring-api-boundaries` | `a09a0e5d755de516786847eefe36134e0c48b75f` |
| `refactor/monitoring-repository-boundaries` | `b10f1af4dbddc25a33c3e6320ccf36f0d7040d53` |
| `refactor/security-headers-boundary` | `b3fad739ab28a1112e52fc005228729f0700d8d3` |
| `refactor/tools-api-boundaries` | `d1fd4ac289d4b0e4eb5db795939063c3e5cf73ec` |
| `test/guided-acceptance-review-regression-2026-10-23` | `02bfbd733f67d67464d7d848816328e2da1565a4` |

## 3. Referencias duplicadas por SHA

En cada grupo hay dos nombres que apuntan al mismo commit. Conservar la rama principal del par y borrar solo la referencia redundante, si no apareció una PR nueva:

| Conservar | Candidata redundante | SHA idéntico |
|---|---|---|
| `feat/reconcile-forensics-main-2026-10` | `test/local-review-forensics-2026-10` | `b21a66b7a25d539654b4ab33107ae477e21a2629` |
| `feat/zeek-connlog-import-2026-10` | `test/local-review-inventory-layout-2026-10` | `baa379b1b7cf31f8106b73e80fe5ac42db0d9c0a` |
| `fix/isolate-monitor-check-failures` | `fix/isolate-monitor-check-failures-validated` | `627f304f5888016c31341444a0a9e5b8d4fc1062` |
| `qa/expert-acceptance-lab-2026-10` | `qa/integrated-map-forensics-scenarios-2026-10` | `1ce2ab00b0f9d259ff871654536f3d64b49c4604` |

Borrar una referencia duplicada no elimina el commit mientras la otra rama siga apuntando al mismo SHA. No borrar ambos nombres de un par en la misma operación.

## 4. Rama de PR ya fusionada

- `feat/semantic-data-registry-2026-11` — HEAD `2f5e0d1842f16673a70f151fdad3bdcac4dc337d`.
- Corresponde a PR #212, ya fusionada en `main` mediante squash en `956ceb442fe21aae3d965e55c1b13d3a7baa2060`.
- El contenido funcional se integró y los checks del HEAD de PR pasaron (CI 18/18, seguridad 2/2, supply chain correcto).
- Candidata a borrar después de confirmar que la PR #212 sigue fusionada y que ningún trabajo posterior usó esa referencia.

**Total de candidatas identificadas en este corte: 25 referencias** (20 ancestros + 4 referencias redundantes + la rama de la PR #212). Esto no equivale a que ya se hayan borrado.

## 5. Ramas que se conservan

Conservar siempre:
- `main`.
- Las cinco ramas que actualmente respaldan PR abiertas (#200, #213, #215, #217, #218).
- Cualquier rama que, al actualizar el inventario, haya recibido una PR abierta.
- Una rama por cada par de SHA duplicados.

## 6. Las otras 162 ramas sin PR abierta

Las restantes no deben eliminarse por ahora. Varias tienen commits únicos respecto del grafo de main. Eso no significa automáticamente que su funcionalidad falte: en un historial con merges squash, el contenido puede estar integrado en main aunque los SHA antiguos no sean ancestros. Para cada grupo se necesita una comparación de contenido (árbol de archivos y diff contra main), la relación con PR fusionadas/cerradas y una decisión explícita:

1. **Integrada por squash:** el contenido relevante está en main; candidata a borrar aunque el commit no sea ancestro.
2. **Obsoleta/sustituida:** otra implementación o fix integrado la reemplaza; documentar cuál.
3. **Trabajo exclusivo útil:** extraerlo a una única PR de recuperación antes de eliminar la rama.
4. **Trabajo experimental o descartado:** registrar motivo y borrar solo después de esa clasificación.
5. **Rama temporal de QA:** conservar únicamente si sigue siendo requerida; los resultados de pruebas deben estar en main o en la evidencia de aceptación.

No realizar un merge masivo de las 162 ramas ni rebasarlas todas. Un lote por vez, con cambios funcionales aislados y CI completa.

## 7. Procedimiento de borrado seguro

Antes de cada lote:
1. Volver a consultar branches y PRs abiertas.
2. Verificar que el SHA de cada rama no haya cambiado desde este manifiesto.
3. Confirmar que el nombre no sea head de una PR abierta.
4. Para ramas ancestro, comprobar otra vez que el tip sea ancestro del main vigente.
5. Para duplicados, comprobar que la rama que se conserva tenga exactamente el mismo SHA.
6. Eliminar solo las referencias aprobadas y volver a contar ramas.

El borrado de refs requiere permiso de escritura sobre el repositorio y una operación GitHub DELETE de referencia. **La conexión GitHub disponible durante esta auditoría no expone una operación para borrar ramas**; por eso no se ejecutó ninguna eliminación ni se movieron refs a main para simularla. Un mantenedor con permiso de escritura debe ejecutar el lote aprobado en GitHub o habilitar una conexión que permita borrar refs. La lista anterior permite hacerlo de manera controlada y verificable.

## 8. Estado de la auditoría

- Inventario y asociación con PR abiertas: completados para el corte 27/11.
- Comparación de ancestros contra main: 20 candidatas identificadas.
- Duplicados exactos: 4 grupos identificados.
- Rama #212 fusionada: identificada como candidata de limpieza.
- Revisión de contenido de las otras 162 ramas: pendiente.
- Borrado físico: pendiente por falta de operación de borrado en la conexión disponible.

**Fuente de seguimiento:** [issue temporal #219](https://github.com/JavierGrecco/NetSentinel/issues/219).  
**Criterio:** el objetivo es un `main` limpio y pocas ramas activas; preservar una referencia no equivale a mantener una línea de desarrollo activa.
