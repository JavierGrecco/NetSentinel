# Auditoría de limpieza de ramas — resultado final 27/11/2026

## Estado

La limpieza histórica quedó **completada** y no hay una tarea de borrado masivo pendiente.

- Manifiesto operativo: [issue #221](https://github.com/JavierGrecco/NetSentinel/issues/221), cerrado como completado.
- Ejecución final: [GitHub Actions #46062536965](https://github.com/JavierGrecco/NetSentinel/actions/runs/46062536965).
- Resultado registrado en esa ejecución: **193 refs eliminadas** (190 referencias del manifiesto auditado + 3 referencias auxiliares del procedimiento).
- El inventario remoto posterior se verificó con exactamente tres refs: `main`, `feat/findings-zeek-evidence-context-2026-10-23` (#200) y `fix/activity-blocked-provenance-2026-11` (#222).
- Las ramas auxiliares de las PR de mantenimiento posteriores se retiraron al completar sus merges. La PR #229 añadió una política automática para evitar nueva acumulación.

## Automatización permanente

El workflow `.github/workflows/delete-merged-head-branch.yml` se ejecuta al cerrar una PR dirigida a `main`. Solo elimina la rama fuente cuando GitHub confirma que:

1. La PR fue fusionada y apunta a este mismo repositorio.
2. La rama fuente no es `main`.
3. Ninguna otra PR abierta utiliza esa rama.
4. El SHA remoto sigue siendo exactamente el SHA de la PR fusionada.

La eliminación usa `--force-with-lease`; si alguna condición falla, la rama se conserva. El workflow usa el código del repositorio base, no hace checkout ni ejecuta el código de la PR. La primera ejecución real eliminó la rama fuente de #229: [run 46067740405](https://github.com/JavierGrecco/NetSentinel/actions/runs/46067740405).

## Reglas permanentes

- Mantener `main` como rama canónica y solo una o dos ramas funcionales activas.
- Revisar PR, SHA y contenido antes de cualquier eliminación extraordinaria.
- No borrar por prefijo, antigüedad o nombre.
- No usar la limpieza automática como sustituto de revisión o integración de cambios.
- Volver a contar refs después de cualquier operación excepcional.

**Nota:** el recuento 193 pertenece a la ejecución puntual de limpieza masiva; no es el número actual de ramas ni un total acumulado de posteriores ramas auxiliares.
