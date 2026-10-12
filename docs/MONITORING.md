# Monitorización

NetSentinel comprueba tres tipos de objetivo:

- **Ping:** comprueba si un host responde a una petición ICMP.
- **TCP:** comprueba si se puede establecer una conexión con un puerto.
- **HTTP/HTTPS:** realiza una petición GET al endpoint indicado sin seguir redirecciones.

Los intervalos van de 15 segundos a 24 horas; el tiempo límite va de 1 a 10 segundos. Cada resultado guarda fecha, estado, detalle y latencia cuando está disponible. El primer fallo abre un incidente. Los fallos siguientes actualizan ese incidente; el primer resultado correcto lo resuelve.

Las comprobaciones TCP y HTTP/HTTPS se ejecutan en un proceso hijo terminable, con un límite total de `timeout_seconds + 1` segundo de margen para iniciar Python. Esto cubre también una resolución DNS del sistema bloqueada, que no siempre queda contenida por el timeout del socket. Un resultado agotado se registra como caída sin exponer URLs completas ni detalles del resolvedor. Ping mantiene su proceso y timeout nativo por sistema operativo. El webhook opcional usa otro proceso aislado con límite total de 5 segundos, para que un DNS HTTPS o servidor lento no congele el supervisor secuencial.

## Retención del historial detallado

Las comprobaciones individuales se conservan **90 días por defecto**. La limpieza se ejecuta al iniciar NetSentinel y luego como máximo una vez al día. Solo elimina filas antiguas de comprobaciones detalladas (`monitor_checks`): no elimina monitores, estados actuales, incidentes abiertos o resueltos, eventos, lecturas de inventario ni observaciones de dispositivos. Las tendencias siguen usando sus ventanas de 24 horas/7 días; los controles actuales e incidentes conservan su estado.

Podés cambiar la política con la variable de entorno `NETSENTINEL_MONITOR_HISTORY_DAYS` antes de iniciar:

- Un entero entre `1` y `3650` fija los días de retención (por ejemplo, `365` para un año).
- `0`, `off` o `disabled` desactiva la limpieza automática y conserva las comprobaciones indefinidamente.
- Si el valor no es válido, NetSentinel registra una advertencia y no elimina comprobaciones.

La limpieza no recupera espacio físico del archivo SQLite de inmediato, pero permite reutilizar las páginas liberadas. Los respaldos SQLite incluyen el historial detallado que permanezca retenido: hacé una copia antes de reducir el período si necesitás conservar muestras antiguas.

En PowerShell:

```powershell
$env:NETSENTINEL_MONITOR_HISTORY_DAYS = "365"
netsentinel
```

En macOS/Linux:

```bash
NETSENTINEL_MONITOR_HISTORY_DAYS=365 netsentinel
```

Para evitar conexiones inesperadas, el monitor HTTP no sigue redirecciones y rechaza credenciales, parámetros y fragmentos en la URL. No incluyas tokens en direcciones web. Las comprobaciones generan tráfico hacia los objetivos seleccionados: usá solo equipos y servicios que administrás o tenés autorización para supervisar.

## Informes y tendencias
En cada monitor, el botón **Historial** muestra también una secuencia de hasta 15 estados recientes. Se lee de izquierda (más antiguo) a derecha (más nuevo); el detalle de cada chequeo queda debajo para investigar horarios y motivos de fallo.


En la página de monitorización podés cambiar entre las últimas 24 horas y los últimos 7 días. El resumen muestra cantidad de comprobaciones, fallos, tasa de resultados correctos, latencia media registrada y los incidentes que siguen abiertos.

La tasa se calcula como comprobaciones correctas divididas por el total de comprobaciones registradas en la ventana seleccionada. No es una garantía de disponibilidad continua: depende de los intervalos configurados, de que NetSentinel permanezca abierto y de las respuestas guardadas. La latencia media se calcula solo con comprobaciones correctas que hayan registrado latencia.

El botón **Descargar informe CSV** exporta la ventana seleccionada con estado del monitor, cantidad de comprobaciones, tasa de éxito y latencias mínima/media/máxima. El archivo incluye codificación UTF-8 para Excel y antepone un apóstrofo a campos de texto que podrían interpretarse como fórmulas.

## Duración de incidentes y latencia

Cada incidente muestra el tiempo desde el primer chequeo fallido. Si ya se recuperó, también muestra el tiempo transcurrido entre esa primera detección y el primer chequeo correcto; el resumen del período presenta la media de recuperación y el máximo.

Estos tiempos son **estimaciones de observación**, no la duración exacta de una interrupción: el fallo real puede haber comenzado después del chequeo correcto anterior y la recuperación puede haber ocurrido antes del siguiente chequeo correcto. Un incidente abierto muestra el tiempo transcurrido desde su detección hasta ahora, y no incluye un tiempo de recuperación.

Al expandir el historial de un monitor, el gráfico de latencia presenta las mediciones registradas en hasta 15 comprobaciones recientes. Solo las respuestas correctas con latencia medida contribuyen a los valores mínimo, medio y máximo; un fallo se indica por separado y no se convierte en una latencia ficticia. El gráfico usa datos ya guardados y no realiza chequeos adicionales.

## Informes CSV e historial extendido

En **Incidentes** podés filtrar la lista por abiertos, resueltos o todos y descargar el informe completo en CSV. La exportación incluye monitor, objetivo, fechas, cantidad de fallos y duración estimada en segundos. Se limita a 5000 incidentes por archivo para mantener un tamaño razonable.

En el historial de cada monitor, además del gráfico de las últimas comprobaciones, hay una tendencia agregada del período seleccionado: una barra por hora para las últimas 24 horas y una por bloque de seis horas para los últimos siete días. El botón **Exportar tendencia CSV** descarga los mismos bloques con conteos de comprobaciones y latencia media/mínima/máxima. Los bloques sin latencia no se convierten artificialmente en cero; los fallos se conservan en el conteo y no entran al promedio de latencia.

## Webhook opcional

Configurá la variable `NETSENTINEL_WEBHOOK_URL` antes de iniciar el programa. Debe ser una URL HTTPS sin usuario ni contraseña incrustados. NetSentinel intenta enviar avisos al pasar a caído y al recuperarse. Sin webhook, la monitorización funciona normalmente.

Ejemplo en PowerShell:

```powershell
$env:NETSENTINEL_WEBHOOK_URL = "https://tu-webhook-HTTPS"
netsentinel
```

No publiques el valor real en el repositorio o en capturas.

## API

La documentación interactiva está disponible en `/api/docs`. Los principales controles usan `/api/monitors`, `/api/monitors/{id}/checks`, `/api/incidents` y `/api/notifications`.
