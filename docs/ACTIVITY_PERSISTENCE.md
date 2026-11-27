# Persistencia de actividad: mapa de módulos

Este documento explica dónde buscar cada parte del almacenamiento de actividad de NetSentinel. La idea es sencilla: cada archivo debe tener un motivo claro para cambiar y las rutas existentes deben seguir funcionando durante la reorganización.

## Cómo se recorre el código

1. **La API** recibe la solicitud y conserva el contrato que usa el panel.
2. **El servicio de actividad** valida los filtros o coordina el caso de uso: sesión, importación, lectura, retención o borrado.
3. **`activity_repository.py`** mantiene los nombres históricos como fachada de compatibilidad.
4. **El repositorio especializado** ejecuta las consultas SQLite que pertenecen a esa tarea.

Los repositorios no conocen FastAPI ni generan respuestas HTTP. Los servicios no deben construir SQL ni modificar directamente las tablas.

## Qué hace cada archivo

| Archivo | Responsabilidad |
| --- | --- |
| `activity_repository.py` | Mantiene las funciones históricas y las dirige al repositorio correspondiente. No es el lugar donde debe crecer nueva lógica SQL. |
| `activity_repository_support.py` | Centraliza comprobaciones comunes, como verificar que un dispositivo exista. |
| `activity_retention_repository.py` | Lee y actualiza los días de retención, convierte fechas a UTC y elimina eventos/sesiones vencidos. |
| `activity_session_repository.py` | Guarda, consulta y cierra sesiones; persiste eventos que el servicio ya validó. Recibe una conexión para que el servicio controle la transacción. |
| `activity_import_repository.py` | Deduplica eventos importados y guarda el lote de forma atómica. También prepara el resultado de la vista previa sin escribir datos. |
| `activity_deletion_repository.py` | Cuenta y borra eventos dentro de un alcance limitado y una confirmación exacta. |
| `activity_read_repository.py` | Recupera el resumen del panel y las filas que necesita la exportación. No decide el formato HTTP. |

## Reglas que no se deben perder

- **Los cambios deben ser compatibles.** La fachada conserva las funciones usadas por los servicios y por las pruebas existentes. Los cambios de esquema deben ser aditivos, transaccionales y acompañados por migraciones probadas; los contratos HTTP existentes se mantienen compatibles.
- **Las consultas deben tener alcance.** Los filtros se construyen con predicados conocidos y los valores siempre se pasan como parámetros SQL. No concatenar datos del usuario dentro de una consulta.
- **La vista previa no escribe.** La importación real bloquea la escritura antes de comprobar duplicados y persistir el lote.
- **El borrado requiere confirmación.** Se vuelve a contar la selección dentro de la transacción para detectar si cambió desde la vista previa.
- **Las fechas se normalizan a UTC.** Las operaciones que comparten una transacción reciben la conexión del servicio; las operaciones completas pueden abrir su propia conexión.
- **No se mezclan reglas de negocio con SQL.** La validación de eventos y archivos, los mensajes para usuarios y los contratos de API permanecen en sus servicios.

## Procedencia del indicador de bloqueo

El booleano heredado `blocked` se conserva como contrato compatible (0/1), pero ya no es la única información disponible. Cada evento también expone `blocked_observation`:

| Estado | Significado |
| --- | --- |
| `reported_true` | La fuente informó explícitamente un valor verdadero. |
| `reported_false` | La fuente informó explícitamente un valor falso. |
| `missing` | La fuente no incluyó el campo. |
| `empty` | El campo se incluyó, pero llegó vacío o nulo. |
| `event_type_blocked` | El propio tipo de evento indica un bloqueo y no se informó un booleano contradictorio. |
| `legacy_unknown` | El registro proviene de una base anterior cuya procedencia no puede reconstruirse. |

La migración agrega la columna dentro de la inicialización transaccional de SQLite y asigna `legacy_unknown` a las filas existentes. Conserva el valor histórico de `blocked`; no lo reinterpreta como una declaración explícita. En eventos nuevos, `event_type=blocked` aporta evidencia positiva cuando el campo está ausente o vacío; si la misma fila declara explícitamente `blocked=false`, la validación la rechaza por contradicción.

La API mantiene el booleano `blocked` y expone el estado adicional en cada evento. La ingesta conserva si la propiedad fue omitida o enviada explícitamente. El importador y exportador CSV preservan `blocked_observation`; Zeek no aporta ese campo y, por eso, sus conexiones se etiquetan como `missing`. La interfaz presenta `No bloqueado` separado de los estados `No informado`.

La exportación de Actividad incluye además `device_id`, `device_name`, `ip_address` y `source` como contexto informativo. Al reimportar un CSV propio, esas cuatro columnas se reconocen como metadatos ignorados: el dispositivo destino sigue siendo el que se selecciona en el formulario y el origen se registra como `manual_import`. No se confía en identificadores locales ni en el campo `source` del archivo, pero sí se conservan los campos del evento y `blocked_observation`.

`legacy_unknown` es intencional: no se puede reconstruir retrospectivamente si un booleano histórico en cero fue informado por la fuente o agregado por el valor por defecto de versiones anteriores.

## Dónde hacer un cambio

- Para cambiar límites o alias de un CSV, empezar por `activity_import_service.py`; tocar el repositorio solo si cambia cómo se guarda el lote.
- Para cambiar el período de retención o el vencimiento, revisar `activity_retention_service.py` y `activity_retention_repository.py`.
- Para alterar el alcance de una consulta o de un borrado, revisar los filtros del servicio y el repositorio correspondiente, y agregar pruebas negativas para filtros no permitidos.
- Para agregar una consulta de panel, revisar `activity_read_service.py` y `activity_read_repository.py`.
- Para cambiar la autorización de una sesión o la validación de un evento, modificar el servicio de aplicación; el repositorio debe seguir recibiendo datos ya validados.

## Al agregar o cambiar un repositorio

Actualizá `scripts/check_architecture_boundaries.py` solo cuando la nueva dependencia sea intencional y esté justificada. Después, actualizá `tests/test_architecture_boundaries.py` para documentar el grafo esperado y mantené una prueba de regresión para el comportamiento. No alcanza con mover una función a otro archivo: la extracción debe conservar los contratos y pasar la suite de CI.
