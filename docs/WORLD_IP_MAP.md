# Mapa mundial de IP

## Estado y propósito

La primera versión del mapa vive en la rama `feat/ip-world-map-geoip-2026-10`; todavía no está integrada en `main`. La pantalla es `/world-map` y su API de solo lectura es `/api/geolocation/map`.

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
- Si un evento contiene solo un dominio y no una `destination_ip`, el mapa no resuelve ese dominio ahora para fingir que conoce la IP que se usó históricamente. Se necesita un registro original de conexión/DNS con el dato de destino.
- No se realizan solicitudes a APIs GeoIP externas y no se remiten direcciones IP ni dominios a proveedores. Las consultas leen los archivos MMDB locales.
- La respuesta de la API se limita a un máximo de 500 IP únicas por consulta; si la muestra está truncada, se indica en la interfaz.

## Integraciones todavía pendientes

Esta primera entrega no incluye un colector de paquetes, actividad continua TCP/UDP/ICMP, NetFlow/IPFIX, integración automática con un router, un escaneo WAN/UPnP, threat intelligence ni reputación de IP. La importación Zeek existente en otra rama proporciona registros de conexiones preexistentes cuando se exportan e importan explícitamente; no transforma este mapa en un capturador en vivo.

Para avanzar, primero hay que validar el mapa con eventos sintéticos conocidos y una base GeoIP de prueba o autorizada, revisar la privacidad/retención y documentar el resultado de la ejecución local. Solo después conviene evaluar fuentes adicionales una por una.
