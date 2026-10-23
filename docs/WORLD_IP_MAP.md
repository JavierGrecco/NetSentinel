# Mapa mundial de IP

## Estado y propósito

La pantalla `/world-map` está integrada en `main` junto con NetSentinel Red y NetSentinel Forense. `/api/geolocation/map` lista destinos observados y `/api/geolocation/lookup` enriquece direcciones que la persona usuaria ya resolvió manualmente. La función es experimental y su aceptación manual todavía está pendiente.

La vista muestra ubicaciones aproximadas de direcciones IP públicas que **ya existen como `destination_ip` en eventos guardados en la base local de NetSentinel**. No es un mapa de dispositivos LAN, no descubre IP externas y no captura conexiones o paquetes en vivo.

## Preparar la geolocalización

1. Instalá el extra opcional en el mismo entorno virtual de NetSentinel:

   ```bash
   python -m pip install -e ".[geoip]"
   ```

2. Descargá por tu cuenta la base **GeoLite2-City** desde MaxMind y guardala en:

   ```text
   ~/.netsentinel/GeoLite2-City.mmdb
   ```

   También podés definir `NETSENTINEL_GEOIP_CITY_DB` con la ruta a esa base. Se aplican las condiciones de cuenta, licencia y distribución establecidas por MaxMind; NetSentinel no descarga esta base automáticamente ni la incluye en el repositorio.

3. Si necesitás el número y la organización del sistema autónomo, descargá además **GeoLite2-ASN** y guardala como `~/.netsentinel/GeoLite2-ASN.mmdb`, o configurá `NETSENTINEL_GEOIP_ASN_DB`. Esa base es opcional.

La cartografía mundial se incluye localmente en `src/netsentinel/static/world_110m.geojson`; sus derechos y la atribución MIT están en `THIRD_PARTY_NOTICES.md` y en el enlace de atribución que muestra la pantalla. Ese archivo dibuja formas de países y no aporta coordenadas de IP.

## Qué muestra y qué no

- Una dirección pública solo recibe un marcador si la base local devuelve latitud y longitud válidas. La tabla puede seguir mostrando IP sin coordenadas o sin coincidencia en la base.
- Las direcciones privadas y especiales (por ejemplo, `192.168.x.x`, `10.x.x.x`, loopback y rangos reservados) no se muestran como ubicaciones geográficas públicas.
- Un punto representa una aproximación de GeoIP para una dirección; no determina una ubicación física exacta, la identidad de una persona ni el origen verdadero de un incidente.
- El recuento se refiere a **eventos almacenados**, no a paquetes, bytes ni sesiones confirmadas. La pantalla no dibuja conexiones entre países ni trayectorias de ataque.
- Para poblar el mapa histórico, el CSV de actividad autorizado puede incluir la columna `destination_ip` (y, si la fuente los proporciona, `destination_port` y `protocol`). La importación manual valida el archivo antes de guardar; no agregues una IP que la fuente original no haya registrado.
- Si un evento contiene solo un dominio y no una `destination_ip`, el mapa histórico no lo resuelve para fingir que conoce la IP que se usó entonces. La pantalla permite una consulta DNS actual, explícita y separada: se consulta el resolvedor configurado en el sistema y luego se geolocalizan localmente las IP públicas devueltas. Eso puede consultar un resolvedor remoto y nunca se presenta como prueba de la IP usada en una visita anterior.
- No se realizan solicitudes a APIs GeoIP externas: el enriquecimiento lee los archivos MMDB locales. Solo al enviar el formulario manual de dominio se hace una consulta DNS a través del resolvedor configurado en el sistema, que puede estar fuera de la computadora.
- La respuesta de la API se limita a un máximo de 500 IP únicas por consulta; si la muestra está truncada, se indica en la interfaz.

## Integraciones todavía pendientes

Esta primera entrega no incluye un colector de paquetes, actividad continua TCP/UDP/ICMP, NetFlow/IPFIX, integración automática con un router, un escaneo WAN/UPnP, threat intelligence ni reputación de IP. El importador específico de Zeek ya está integrado en `main`; sus límites, formato y procedimientos manuales están descritos en [ZEEK_CONNLOG_IMPORT.md](ZEEK_CONNLOG_IMPORT.md). También se puede importar CSV de actividad cuando contiene IP destino procedentes de una fuente autorizada. Ninguna de estas vías convierte el mapa en un capturador en vivo.

Para avanzar, primero hay que validar el mapa con eventos sintéticos conocidos y una base GeoIP de prueba o autorizada, revisar la privacidad/retención y documentar el resultado de la ejecución local. Solo después conviene evaluar fuentes adicionales una por una.
