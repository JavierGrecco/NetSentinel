# Seguimiento familiar de actividad

La ruta `/activity` permite revisar metadatos que ya estén disponibles para NetSentinel, abrir ventanas temporales para recibirlos e importar logs normalizados. Esta etapa no captura paquetes ni inspecciona aplicaciones por sí sola; no instala un agente y no convierte una sesión en una fuente de tráfico.

## Fuentes disponibles

- `router_dns`: consultas DNS registradas por un router, punto de acceso o resolvedor local.
- `router_flow`: metadatos de flujos/conexiones que proporcione una fuente que tenga visibilidad suficiente.
- `device_agent`: metadatos explícitos comunicados por un agente local del dispositivo. NetSentinel todavía no instala ni distribuye tal agente.
- `manual_import`: registros históricos incorporados desde un CSV con el esquema de abajo.

Todavía no hay un adaptador nativo para una marca/modelo de router. El primer paso es exportar sus registros y normalizarlos; la API de ingestión permite incorporar un adaptador local después. En redes Wi-Fi o conmutadas, la computadora que ejecuta el panel no necesariamente ve el tráfico unicast de los demás dispositivos.

## Límites de recopilación y privacidad

NetSentinel admite solo los metadatos que esta versión modela:

- Nombre DNS consultado o SNI TLS visible, cuando la fuente lo reporte.
- Dirección IP de destino, puerto y protocolo, cuando estén disponibles.
- Nombre de aplicación y eventos de bloqueo si la fuente los proporciona.
- Fecha/hora observada, fuente y dispositivo al que se asoció el evento.

No se almacenan contraseñas, usuarios de inicio de sesión, cookies, tokens, cuerpos HTTP, contenido de paquetes, rutas ni URLs completas. La API de eventos rechaza campos extra. Un nombre DNS consultado no demuestra que alguien haya abierto una página, y una conexión no demuestra que una persona haya iniciado sesión. DNS cifrado, VPN, caché DNS, ECH y limitaciones de la fuente pueden ocultar parte de la actividad.

NetSentinel no instala certificados raíz, no intercepta TLS, no intenta degradar conexiones cifradas y no intenta descifrar o recuperar credenciales. Para saber qué aplicaciones usa un menor y cuánto tiempo pasa en ellas, combiná estos metadatos con los controles parentales nativos del sistema operativo, con conocimiento y supervisión apropiados.

## Ventanas de seguimiento

1. Abrí `/activity` y elegí el dispositivo del inventario.
2. Seleccioná la fuente que realmente vas a integrar y una duración entre 5 minutos y 12 horas.
3. NetSentinel abre la sesión y muestra un token de recopilación una única vez. El token es un secreto portador: no lo guardes en el repositorio, no lo publiques y guardalo solo en la configuración privada del adaptador local. La base almacena el hash del token, no el token en claro.
4. Un adaptador debe enviar eventos a `POST /api/activity/ingest` e incluir `session_id`, `collector_token`, `device_id`, `event_type`, `source` y los metadatos opcionales. La sesión debe estar activa y la fuente debe coincidir.
5. Detené la sesión cuando termines o dejá que venza. Solo se aceptan eventos mientras está activa.

La API está pensada para usarse en el contexto local de NetSentinel. No expongas el panel ni la API en la LAN o Internet sin añadir autenticación, transporte seguro y una evaluación de seguridad independiente.

### Ejemplo de evento DNS

```json
{
  "session_id": 12,
  "collector_token": "TOKEN_DE_LA_SESION",
  "device_id": 4,
  "event_type": "dns_query",
  "source": "router_dns",
  "observed_at": "2026-10-11T18:30:00Z",
  "domain": "example.com"
}
```

Los tipos admitidos son `dns_query`, `connection`, `tls_sni`, `app_usage` y `blocked`. Los protocolos admitidos son `tcp`, `udp`, `quic`, `icmp` y `other`. Para los eventos `dns_query` y `tls_sni` se exige un nombre DNS; para `connection` debe haber un dominio o una IP de destino; para `app_usage` se exige `app_name`.

## Importación CSV local

En la misma página podés cargar como máximo 1 MB y 1.000 eventos por importación. Cada evento se asocia al dispositivo seleccionado y se etiqueta `manual_import`.

Cabeceras admitidas (se pueden omitir las columnas opcionales):

```csv
observed_at,event_type,domain,destination_ip,destination_port,protocol,app_name,blocked
2026-10-11T18:30:00Z,dns_query,example.com,,,,,false
2026-10-11T18:31:00Z,connection,,203.0.113.10,443,tcp,,false
2026-10-11T18:32:00Z,blocked,adult.example,,,,,true
```

No se admiten columnas desconocidas ni campos como `url`, `path`, `username`, `password`, `token`, `cookie`, `payload` o cuerpos HTTP. Para importar logs nativos del router, convertí primero su fecha, evento, dominio o destino a este esquema; no se debe asumir que todos los modelos entregan los mismos datos.

## Conservación

- Retención predeterminada: 7 días.
- Configurable entre 1 y 90 días desde `/activity`.
- Eventos anteriores a la retención se eliminan en la próxima consulta o actualización de actividad.
- Las sesiones cerradas se depuran después de 90 días.
- Las exportaciones JSON y la copia SQLite incluyen el historial de metadatos. Protegé los respaldos porque revelan información sobre la red familiar.
