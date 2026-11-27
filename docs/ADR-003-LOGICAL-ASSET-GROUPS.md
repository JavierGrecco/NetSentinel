# ADR-003 — Fichas lógicas y asociaciones manuales de activos

- **Estado:** decisión adoptada.
- **Fecha:** 27 de noviembre de 2026.
- **Ámbito:** NetSentinel Red / Inventario.
- **Sustituye:** ninguna decisión anterior.

## Contexto

El inventario conserva registros técnicos en `devices`, agrupados por MAC. Ese identificador puede ser administrado localmente, aleatorio, virtual, rotado o reutilizado. Las IP pueden reasignarse; un hostname también puede cambiar o repetirse. La tabla `devices` está además referenciada por observaciones, eventos, sesiones y actividad. Reemplazar su clave ahora podría alterar la interpretación del historial.

## Decisión

Separar dos conceptos sin migrar ni reescribir las observaciones históricas:

1. **Registro técnico (`devices`):** la fila actual que conserva los datos y vínculos existentes. Mantiene su ID y su clave actual por compatibilidad.
2. **Ficha lógica (`assets`):** identificador propio y nombre operativo que crea el usuario local para organizar uno o varios registros técnicos.
3. **Asociación (`asset_device_links`):** vínculo manual entre una ficha y un registro, con motivo, fecha de inicio y fecha de finalización. Se conserva el historial; no se elimina al cambiar o retirar una asociación.

Un registro técnico puede tener como máximo una asociación vigente. Una ficha lógica puede agrupar múltiples registros técnicos. La aplicación no crea ni recomienda asociaciones automáticas basadas solo en MAC, IP, hostname o tiempo.

## Reglas de operación

- Crear una ficha lógica es una acción local explícita.
- Asociar, cambiar o retirar un vínculo exige un motivo de entre 8 y 280 caracteres.
- La creación de una ficha y su asociación inicial se ejecutan en una única transacción.
- Un índice único parcial impide que un registro tenga dos asociaciones vigentes.
- Los vínculos finalizados conservan el motivo inicial y el motivo de retiro.
- No se incorpora eliminación física de fichas ni de historial en esta entrega.
- La confianza continúa asociada al registro técnico; no se propaga automáticamente a otros registros del mismo grupo.
- La asociación manual no constituye verificación de identidad física, titularidad ni identidad humana.
- La copia SQLite conserva las nuevas tablas. La exportación JSON se versiona a `netsentinel-data-export-v5` e incluye las fichas y los vínculos históricos.

## Consecuencias

**Positivas:** permite organizar MAC rotadas o varios registros bajo una ficha común sin fusionar información; conserva trazabilidad y evita cambiar las claves foráneas del inventario.

**Límites:** la agrupación depende de una decisión manual; no resuelve la identidad de forma automática ni aporta usuarios/roles, pues la aplicación sigue siendo local y monousuario.

**Siguiente decisión separada:** INV-01 definirá cómo representar MAC, IP, hostname e interfaz como identificadores con fuente, alcance, precisión y vigencia temporal, y cuándo una futura sugerencia de agrupación tiene evidencia suficiente. Cualquier automatización deberá explicar incertidumbre y exigir aceptación explícita.
