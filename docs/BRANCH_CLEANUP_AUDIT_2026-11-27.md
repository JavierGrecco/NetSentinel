# Auditoría de limpieza de ramas — actualización 27/11/2026

**Estado:** el manifiesto inicial incluido en este archivo quedó **superado** por una revisión posterior. No ejecutar borrados usando listados de secciones antiguas de este documento.

## Fuente vigente para la limpieza

La lista íntegra de ramas y las comprobaciones individuales están en [issue #221 — Eliminar ramas ya integradas y revisar referencias huérfanas](https://github.com/JavierGrecco/NetSentinel/issues/221). Ese issue contiene el corte actualizado de 193 referencias, su clasificación, la evidencia de PR fusionadas y las 23 referencias que deben preservarse o revisarse.

## Resumen del corte actualizado

- 193 referencias remotas, incluida `main`.
- 189 SHA de commit distintos.
- Cuatro pares de ramas apuntan al mismo SHA.
- 167 referencias candidatas: 163 ramas cuyo HEAD coincide exactamente con el HEAD de una PR fusionada y cuatro punteros redundantes de parejas duplicadas.
- 23 referencias deben preservarse/revisarse: 19 con PR cerradas sin merge y cuatro sin PR cerrada coincidente con el HEAD actual.
- No se eliminó ninguna rama.

## Reglas de seguridad

1. Consultar de nuevo las ramas y PR abiertas inmediatamente antes de borrar.
2. Confirmar SHA actual = HEAD de la PR fusionada; verificar que el merge commit siga en `main`.
3. Confirmar que no exista una PR cerrada sin merge cuyo HEAD coincida con esa misma referencia.
4. En cada pareja duplicada, preservar la rama canónica y eliminar solo el puntero redundante.
5. Preservar siempre `main`, #200 y #222; revisar nuevas PR que aparezcan desde el corte.
6. Recuperar a una única rama/PR cualquier trabajo exclusivo que se decida conservar.
7. No borrar por prefijo, antigüedad o nombre; no fusionar en bloque ni mover una rama a `main` para simular un DELETE.

## Restricción operativa

La conexión GitHub utilizada aquí permite leer el inventario y crear/actualizar archivos, pero no expone una operación para eliminar referencias Git. Por lo tanto, el recuento permanece en 193 hasta que un mantenedor con una operación `DELETE refs` ejecute el lote de #221 y se verifique el inventario posterior.

**Este documento es un resumen de control. El issue #221 es el único manifiesto vigente de candidatos, referencias preservadas y evidencia individual.**
