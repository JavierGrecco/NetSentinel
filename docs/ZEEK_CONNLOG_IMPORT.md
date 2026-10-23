# Importar registros de conexiones de Zeek

**Estado:** primera versión del adaptador integrada en `main`; aceptación manual pendiente.  
**Modalidad:** importación explícita de archivo; solo lectura de la fuente original.  
**Límites:** 1 MB por petición y hasta 1000 registros.

## Para qué sirve

Permite incorporar a la sección Actividad metadatos de conexión que Zeek ya haya exportado a su formato TSV habitual o a JSON Lines. NetSentinel no inicia Zeek, no captura paquetes, no abre interfaces de red y no configura sensores. El archivo debe provenir de una red propia o de una fuente para la que exista autorización.

Zeek documenta `conn.log` como un registro de conversaciones de red con campos como `ts`, `uid`, `id.orig_h`, `id.orig_p`, `id.resp_h`, `id.resp_p`, `proto`, `orig_bytes`, `resp_bytes`, `orig_ip_bytes`, `resp_ip_bytes`, `orig_pkts` y `resp_pkts`. La referencia de campos es la [documentación oficial de conn.log](https://docs.zeek.org/en/current/reference/logs/conn.html).

## Qué se importa

| Campo de Zeek | Campo de NetSentinel | Regla |
|---|---|---|
| `ts` | `observed_at` | Tiempo Unix convertido a UTC; la persistencia actual conserva segundos. |
| `uid` | `source_event_id` | Se guarda como `zeek:<uid>` para reconocer el mismo registro al reimportarlo. |
| `id.orig_h`, `id.orig_p` | IP y puerto de origen | Las IP se validan. El puerto 0 queda desconocido porque el contrato común solo admite puertos del 1 al 65535. |
| `id.resp_h`, `id.resp_p` | IP y puerto de destino | Mismas reglas que el origen. |
| `proto` | `protocol` | TCP, UDP, ICMP y QUIC se conservan; los demás valores se agrupan como `other`. |
| `orig_ip_bytes`, `resp_ip_bytes` | `bytes_sent`, `bytes_received` | Contadores a nivel IP orientados desde la perspectiva del dispositivo elegido. Si su IP es únicamente el extremo respondedor (`id.resp_h`), se invierten. No se mezclan con `orig_bytes` o `resp_bytes`, que miden bytes de carga útil. |
| `orig_pkts`, `resp_pkts` | `packets_sent`, `packets_received` | Contadores de paquetes orientados a la perspectiva del dispositivo elegido, con la misma regla de inversión para el extremo respondedor. |

Los campos adicionales del registro Zeek se ignoran; no se guardan automáticamente. Los contadores ausentes, nulos o marcados con `-` permanecen desconocidos (`NULL`). Un cero informado se conserva como cero. Cada evento queda registrado con la fuente común `manual_import`; el prefijo `zeek:` en el identificador permite reconocer el formato de origen sin cambiar el contrato de fuentes de sesiones autorizadas.

Como un archivo de Zeek puede contener conexiones de muchos equipos, la asociación se limita deliberadamente al dispositivo elegido en la interfaz. La IP de origen o destino debe pertenecer al intervalo temporal en que esa dirección se observó para el dispositivo. Además, si otro activo tiene un intervalo registrado que se solapa para esa misma IP en el momento del evento, la fila se considera ambigua y no se importa. Las filas fuera del intervalo quedan fuera de alcance y tampoco se asignan a ese equipo. Esta regla es conservadora: puede omitir registros si el inventario está desactualizado, pero evita asumir que una dirección IP identifica siempre al mismo equipo.

## Validaciones y protección de datos

- Se admite JSON Lines (un objeto JSON por línea) y el TSV nativo de Zeek. El TSV estándar se lee mediante sus directivas `#separator`, `#path`, `#fields` y `#types`; también se acepta TSV simple con una primera fila de nombres de campo.
- Se rechazan filas malformadas, claves JSON repetidas, IP no válidas, puertos fuera de rango, contadores negativos o no enteros, marcas de tiempo no válidas y más de 1000 registros.
- Se valida el lote completo antes de escribir. Una fila inválida hace que la importación completa falle, sin guardar filas anteriores del mismo archivo.
- La vista previa usa la misma validación, política de retención y deduplicación que la importación real, pero no escribe eventos.
- Los IDs estables de Zeek se usan para evitar duplicados al repetir una importación, incluso si otros metadatos del registro cambiaron.
- La atribución usa los intervalos `first_seen`/`last_seen` guardados en el inventario y descarta IP que tengan propietarios con intervalos solapados. La respuesta distingue filas fuera del intervalo y filas con propietario ambiguo.
- Se aplican la política de retención configurada y los controles HTTP de NetSentinel. No se incluyen secretos, credenciales ni cuerpos de paquetes.
- No se genera una afirmación sobre aplicaciones, contenido de comunicaciones, vulnerabilidades ni tráfico actual a partir de campos que el registro no contiene.

## API disponible en esta primera entrega

La integración ofrece dos operaciones locales. En ambas, el cuerpo usa `device_id` del dispositivo asociado y `log_data` con el contenido de `conn.log`, ya sea TSV o JSON Lines.

- `POST /api/activity/import/zeek/preview`: valida y muestra hasta diez registros de ejemplo, con indicación de duplicados. No guarda datos.
- `POST /api/activity/import/zeek`: importa el lote validado y devuelve los recuentos de registros nuevos y duplicados.

Ejemplo de JSON para una petición de vista previa:

```json
{
  "device_id": 1,
  "log_data": "{\"ts\": 1792490400, \"uid\": \"CZeekExample42\", \"id.orig_h\": \"192.0.2.20\", \"id.orig_p\": 51514, \"id.resp_h\": \"198.51.100.53\", \"id.resp_p\": 53, \"proto\": \"udp\", \"orig_bytes\": 62, \"resp_bytes\": 141, \"orig_ip_bytes\": 118, \"resp_ip_bytes\": 197, \"orig_pkts\": 2, \"resp_pkts\": 3}"
}
```

La sección Actividad incluye selector de archivo, selección de dispositivo, vista previa y confirmación de importación. La interfaz es parte de este prototipo; la revisión manual en escritorio y móvil sigue pendiente antes de cerrar la PR.

## Pruebas previstas y límites conocidos

La sección Actividad incluye selección de archivo, selección explícita del dispositivo, vista previa y confirmación de importación para ambos formatos. La vista previa indica cuántas filas están dentro del alcance temporal, cuántas se omitirían por quedar fuera del intervalo observado y cuántas son ambiguas por intervalos de propiedad de IP solapados.

Las pruebas automáticas usan únicamente registros sintéticos y una base SQLite temporal. Cubren el mapeo direccional, la inversión de contadores cuando el dispositivo elegido es el extremo respondedor, cero frente a desconocido, registros repetidos, vista previa, reimportación idempotente, alcance por IP del dispositivo seleccionado, validación estricta y ausencia de escrituras parciales.

Esto no sustituye la prueba manual con un archivo Zeek real, sanitizado y autorizado. La siguiente revisión debe comprobar que los datos se entiendan correctamente en Actividad, que las fechas respeten la retención y que las conexiones de otros equipos queden omitidas sin atribuirse al dispositivo seleccionado.

## Comprobación manual antes de salir del borrador

1. Abrí **Actividad → Importar** y elegí un dispositivo que tenga direcciones con historial de observación.
2. Cargá el `conn.log` TSV predeterminado o un archivo `.jsonl`/`.ndjson` de una red propia o autorizada. Primero usá **Previsualizar registros**. Confirmá que se muestran origen, destino y protocolo; los contadores de envío/recepción deben leerse desde la perspectiva del dispositivo elegido, incluso si aparece como destino. Los campos ausentes deben indicar que son desconocidos.
3. Antes de importar, consultá **Actividad → Eventos**: el evento sintético de prueba no debe aparecer. Volvé a Importar, confirmá la acción y verificá que se guarde una sola fila con identificador `zeek:<uid>`.
4. Previsualizá e importá de nuevo el mismo archivo. La segunda operación debe señalar duplicados y no crear otra fila.
5. Probá un archivo con una fila malformada después de una fila válida. La petición debe informar la fila con error y no guardar ninguna parte del lote. Probá también un registro cuya IP cae fuera del intervalo de observación y otro cuya IP tenga propietarios solapados; ambos deben quedar omitidos y contabilizados.
6. Repetí el recorrido en escritorio y móvil, incluyendo selección de archivo, teclado, mensajes de error, desplazamiento horizontal y los tres temas visuales.

Usá registros sanitizados y no incluyas datos sensibles innecesarios. No hace falta ejecutar Zeek ni generar tráfico de red para completar las primeras comprobaciones. La estructura del TSV de Zeek sigue la [guía oficial de formatos de registro](https://docs.zeek.org/en/current/tutorial/logs.html).

