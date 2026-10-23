# Auditoría de ramas remotas — 23 de octubre de 2026

**HEAD de código revisado:** [`91d5568a`](https://github.com/JavierGrecco/NetSentinel/commit/91d5568a89ee8aa2cc6b8881a404bb69e96461c1)  
**Rama canónica:** `main`

## Resumen de la auditoría

La consulta de GitHub encontró 174 referencias de ramas: `main` y otras 173. Se revisaron 184 PR y no había ninguna PR abierta al momento de la auditoría.

| Grupo de ramas | Cantidad | Tratamiento |
|---|---:|---|
| Asociadas al menos a una PR fusionada | 152 | Candidatas normales a limpieza, previa comprobación de que la referencia actual siga apuntando al SHA fusionado. |
| Asociadas a PR cerradas sin fusionar | 15 | Revisadas como reemplazadas, superadas o incorporadas por otra integración. |
| Sin PR asociada | 6 | Revisadas por duplicación de SHA, contenido antiguo y diferencias con `main`. |
| **Total fuera de `main`** | **173** | No confundir ramas cerradas con ramas eliminadas. |

No se borraron referencias remotas en esta pasada. Una rama fusionada por *squash* puede mantener un historial Git distinto aunque su contenido ya esté en `main`; para borrarla con seguridad hay que confirmar que su HEAD no recibió cambios posteriores al merge. Las ramas cerradas sin fusionar requieren también comprobar que cualquier contenido exclusivo quedó preservado.

## PR cerradas sin fusionar

| Rama / grupo | PR asociada | Resultado de la revisión |
|---|---|---|
| `arch/close-boundary-policy-gaps` | #88 | Reemplazada por #89. |
| `docs/record-dependency-triage` | #154 | Documentación de una revisión de dependencias anterior; no aporta archivos exclusivos al árbol actual. |
| `feat/forensics-workspace-foundation` | #113 | Superada por la evolución de Forense y su integración en #189. |
| `feat/ip-world-map-geoip-2026-10` | #182, #188 | Mapa GeoIP incluido en #189. |
| `feat/reconcile-forensics-main-2026-10` | #157 | Forense integrado en #189. |
| `fix/isolate-monitor-check-failures` y `fix/isolate-monitor-check-failures-validated` | #54, #55 | Se recuperó la mejora útil de retroceso progresivo en el código modular actual; ver commit [`91d5568a`](https://github.com/JavierGrecco/NetSentinel/commit/91d5568a89ee8aa2cc6b8881a404bb69e96461c1). |
| `fix/safe-data-dir-permissions-v2`, `fix/safe-data-directory-permissions` | #35, #33 | Reemplazadas por #36. |
| `fix/serialize-extension-navigation-events` | #30 | Reemplazada por #31. |
| `lab/reference-reengineering-2026-10` | #172 | El prototipo de topología se trasladó a la integración #171/#189. La rama también tenía un documento exclusivo, que se preserva en [`REFERENCE_REENGINEERING_PLAN.md`](REFERENCE_REENGINEERING_PLAN.md). |
| `qa/integrated-map-forensics-scenarios-2026-10` | #184 | Superada por #189. |
| `research/digital-forensics-proposal` | #112 | La propuesta se conservó en [`FORENSIC_MODE_PROPOSAL.md`](FORENSIC_MODE_PROPOSAL.md), etiquetada como alcance futuro y no como función implementada. |
| `test/manual-scenarios-2026-10` | #183 | Generadores y casos sintéticos incluidos en #189. |
| `test/restore-monitoring-history` | #161 | La cobertura de restauración está en los tests actuales; `main` incluye además la regresión para cerrar la conexión de origen si falla la apertura del destino del respaldo. |

## Ramas sin PR

- `fix/isolate-monitor-check-failures-v2`: misma línea de trabajo de reintentos; la protección se recuperó y se está validando en el código actual.
- `privacy/exclude-special-use-browser-addresses`: snapshot anterior. El código actual tiene filtros y pruebas más completos para direcciones de uso especial y límites de URL.
- `qa/expert-acceptance-lab-2026-10`: comparte SHA con `qa/integrated-map-forensics-scenarios-2026-10`; ambas quedaron superadas por #189.
- `test/local-review-forensics-2026-10`: comparte SHA con la rama de reconciliación de Forense integrada.
- `test/local-review-inventory-layout-2026-10`: comparte SHA con la rama de importación Zeek integrada.
- `test/local-review-zeek-2026-10`: snapshot anterior; no contiene rutas de archivos ausentes de `main`, y sus archivos relevantes están en una versión más antigua.

## Resultado del análisis de árboles

Se compararon los árboles de las 21 referencias sin una PR fusionada asociada con el árbol de `main`. La única ruta de archivo que faltaba en `main` era `docs/REFERENCE_REENGINEERING_PLAN.md`; se ha copiado y contextualizado en el commit de documentación que acompaña a esta auditoría. Para los módulos funcionales, no se detectó una ruta de archivo exclusiva que haya que reincorporar. También se inspeccionaron los cambios en el supervisor de monitorización: la rama antigua contenía retroceso progresivo por monitor que no estaba en la versión modular; esa mejora ya se adaptó al código actual con pruebas.

La comparación de rutas no es lo mismo que declarar idénticos todos los archivos: ramas viejas contienen versiones anteriores de archivos compartidos. Por eso la limpieza debe basarse en el estado de las PR, el SHA remoto actual y la preservación de los cambios útiles, no en borrar todas las ramas por patrón.

## Procedimiento seguro para la limpieza física

1. Consultar una rama candidata y confirmar la PR que la fusionó o la PR posterior que la reemplazó.
2. Confirmar que no hay PR abierta y que el SHA de la rama no avanzó después del trabajo ya integrado.
3. Borrar primero las ramas de PR fusionadas cuyo HEAD siga coincidiendo con el SHA de integración revisado.
4. Para las ramas cerradas sin merge, borrar solo después de verificar la preservación documentada de su contenido.
5. Mantener `main` y las ramas activas de trabajo; no usar una eliminación masiva basada solamente en los prefijos `feat/`, `fix/`, `qa/` o `test/`.

**Estado:** auditoría documentada; la eliminación física de referencias remotas queda pendiente. No se presenta como completada mientras GitHub todavía enumere esas ramas.
