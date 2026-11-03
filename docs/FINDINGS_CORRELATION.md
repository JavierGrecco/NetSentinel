# Correlación de evidencia en Hallazgos

**Estado:** primera implementación en una rama de trabajo; pendiente de revisión y CI antes de decidir si se integra. No sustituye la aceptación manual ni convierte a NetSentinel en un SIEM/NDR.

## Qué hace esta primera entrega

Cuando la vista Hallazgos reúne un evento del inventario o un incidente de disponibilidad, intenta adjuntar contexto de conexiones procedentes de registros Zeek `conn.log` importados explícitamente. No inicia Zeek, no captura paquetes, no hace consultas DNS ni busca en otras máquinas.

- **Inventario:** solo consulta conexiones asignadas al mismo ID de dispositivo que figura en el evento y cuya hora observada cae dentro de una ventana de cinco minutos antes o después.
- **Monitorización:** solo consulta conexiones donde la IP literal configurada en el objetivo del monitor coincide exactamente con la IP de origen o destino, cerca de la apertura o actualización del incidente. No resuelve nombres ni adivina equivalencias.
- **Origen admisible:** registros con `source='manual_import'`, `import_format='zeek_conn_log'`, `event_type='connection'` y un identificador de origen con prefijo `zeek:`. El formato se establece solo después de que el importador Zeek dedicado valida el archivo; una fila CSV no puede obtener esa etiqueta enviando un UID con apariencia de Zeek.
- **Resultados:** se conservan el ID original del registro, la hora observada y recibida, el dispositivo asociado, los extremos de la conexión, el protocolo y los contadores que la fuente realmente informó. Un contador ausente sigue siendo desconocido; un cero real permanece cero.
- **Límites:** hasta cinco registros por contexto y una ventana fija de ±300 segundos. La consulta agrupa contextos, parametriza valores y lee SQLite sin modificar los datos.
- **Navegación:** cada conexión que lleva un identificador de origen enlaza a Actividad con el filtro por `source_event_id` exacto, y mantiene visible que la evidencia se importó.

## Cómo interpretar los estados

- **Coincidencia encontrada:** hay una o más conexiones Zeek dentro de la ventana y con la identidad definida por la regla. No significa que el evento haya causado la conexión ni que sea maliciosa.
- **Sin coincidencia en la ventana:** la consulta no encontró registros que cumplieran el alcance. No prueba que no hubiera tráfico; puede faltar una fuente, haber expirado por retención o estar fuera del intervalo.
- **No disponible:** no se pudo formar una consulta de forma segura, por ejemplo porque el objetivo del monitor está configurado con un nombre y no con una IP literal. No se intenta resolverlo en segundo plano.

Una proximidad temporal es **contexto para que una persona investigue**, no una atribución causal, detección autónoma, confirmación de ataque ni identificación de quién estaba usando el equipo.

## Privacidad, seguridad y retención

La correlación usa únicamente filas ya guardadas y marcadas por el importador dedicado. Respeta el mecanismo existente de retención de actividad; si la evidencia importada ya se eliminó, no reaparecerá. Los registros históricos con prefijo `zeek:` cuya ruta de importación no estaba registrada se conservan como `unknown` y no se atribuyen automáticamente a Zeek. Al volver a importar el `conn.log` por la ruta dedicada, la nueva fila queda marcada de forma explícita; la fila histórica no se sobreescribe y puede seguir visible como dato sin clasificar hasta que venza su retención. El enlace de evidencia filtra por UID **y** formato, de modo que no confunde ambas filas. La vista no copia carga útil de paquetes, credenciales, contenido HTTPS ni PCAP. No se añade ningún colector ni se modifica la política de exportación por defecto.

El filtro de Actividad exige un ID exacto de origen, lo valida como texto acotado y lo pasa como parámetro SQL. Se mantiene separado de los filtros de dispositivo, fuente, fecha y tipo.

## Verificación

La suite de esta rama debe cubrir:

- coincidencia temporal por ID de activo;
- coincidencia por IP literal del objetivo del monitor;
- ausencia de coincidencia por IP distinta o fuera de ventana;
- exclusión de fuentes que no sean conexiones Zeek importadas;
- preservación de dirección, UID, contadores y cero frente a desconocido;
- límites de registros/contextos y filtro de origen exacto;
- navegación segura desde Hallazgos a Actividad, sin usar `innerHTML` para datos de la fuente;
- compatibilidad de formato del informe existente y límites de arquitectura.

Los tests automatizados no sustituyen la revisión manual visual y de accesibilidad del producto. La implementación no debe fusionarse a `main` hasta cerrar las puertas de estabilización actuales, incluidas aceptación guiada y protección efectiva del repositorio. Seguimiento: [issue #197](https://github.com/JavierGrecco/NetSentinel/issues/197).
