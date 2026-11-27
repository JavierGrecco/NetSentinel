# Correlación de evidencia en Hallazgos

**Estado:** primera entrega integrada en `main` mediante PR #200, squash `a6088f5ed2239b530d07b484eb60bf8024e1a91f` (27/11/2026). Validada en el HEAD de PR `d7b57ada501696c64f0fb76335fdbbd3f561ac69`: CI 19/19, Security Analysis 2/2, Supply Chain 2/2 y Chromium 135/135. No sustituye la aceptación manual de 0.10.0 ni convierte a NetSentinel en un SIEM/NDR.

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

## Verificación registrada

La PR #200 se integró en `main` mediante [`a6088f5ed2239b530d07b484eb60bf8024e1a91f`](https://github.com/JavierGrecco/NetSentinel/commit/a6088f5ed2239b530d07b484eb60bf8024e1a91f). En el HEAD final de la PR se aprobaron:

- [CI 19/19](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073256547), incluida Chromium 135/135;
- [Security Analysis 2/2](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073256811);
- [Supply Chain Security 2/2](https://github.com/JavierGrecco/NetSentinel/actions/runs/46073256516), con firma de procedencia omitida en forma esperada al no tratarse de un release.

Cobertura específica: `test_findings_link_exact_zeek_connection_to_inventory_and_monitor_target`, `test_findings_do_not_resolve_monitor_hostnames_for_zeek_context`, el conjunto `tests/test_findings_activity_repository.py` (incluida `test_zeek_context_query_uses_inclusive_five_minute_boundaries`) y la prueba Chromium que asegura que los estados de procedencia en Actividad sean texto simple, no componentes tipo botón.

La revisión ampliada de #197 sigue abierta para IP reasignadas/ambiguas, timestamps inválidos, registros antiguos, reimportación duplicada, faltantes/cero y exportación portátil reproducible. La aceptación general 0.10.0 también sigue pendiente; ver [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md), [issue #197](https://github.com/JavierGrecco/NetSentinel/issues/197) e [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).
