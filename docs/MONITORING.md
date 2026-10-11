# Monitorización

NetSentinel comprueba tres tipos de objetivo:

- **Ping:** comprueba si un host responde a una petición ICMP.
- **TCP:** comprueba si se puede establecer una conexión con un puerto.
- **HTTP/HTTPS:** realiza una petición GET al endpoint indicado sin seguir redirecciones.

Los intervalos van de 15 segundos a 24 horas; el tiempo límite va de 1 a 10 segundos. Cada resultado guarda fecha, estado, detalle y latencia cuando está disponible. El primer fallo abre un incidente. Los fallos siguientes actualizan ese incidente; el primer resultado correcto lo resuelve.

Para evitar conexiones inesperadas, el monitor HTTP no sigue redirecciones y rechaza credenciales, parámetros y fragmentos en la URL. No incluyas tokens en direcciones web. Las comprobaciones generan tráfico hacia los objetivos seleccionados: usá solo equipos y servicios que administrás o tenés autorización para supervisar.

## Informes y tendencias

En la página de monitorización podés cambiar entre las últimas 24 horas y los últimos 7 días. El resumen muestra cantidad de comprobaciones, fallos, tasa de resultados correctos, latencia media registrada y los incidentes que siguen abiertos.

La tasa se calcula como comprobaciones correctas divididas por el total de comprobaciones registradas en la ventana seleccionada. No es una garantía de disponibilidad continua: depende de los intervalos configurados, de que NetSentinel permanezca abierto y de las respuestas guardadas. La latencia media se calcula solo con comprobaciones correctas que hayan registrado latencia.

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
