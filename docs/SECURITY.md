# Seguridad y límites

## Alcance de la versión 0.7.3

NetSentinel es una herramienta de observación local. El panel escucha en `127.0.0.1` de forma predeterminada y la base SQLite permanece en la computadora del usuario. La lectura pasiva de tablas de vecinos solo muestra direcciones que el sistema ya conoce; el descubrimiento activo comienza únicamente cuando se solicita desde el panel.

El descubrimiento activo solo examina subredes IPv4 privadas RFC 1918: `10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. Analiza como máximo dos subredes y, si una es mayor que /24, reduce el alcance a un /24. Envía como máximo un ping por dirección y acepta una sola ejecución de descubrimiento simultánea. No explora Internet ni modifica la configuración de los equipos. Un equipo puede no responder al ping, por lo que los resultados no garantizan un inventario completo y no cubren redes exclusivamente IPv6.

Las interfaces Apple de enlace local como AWDL/LLW no se consideran dispositivos de una LAN convencional en nuevas lecturas. Los registros históricos se conservan automáticamente; las observaciones antiguas de AWDL/LLW se etiquetan como interfaces locales virtuales sin borrarlas. Una MAC puede aleatorizarse o suplantarse, y un dispositivo desconocido no demuestra una intrusión.

## Protección de la interfaz local

El servidor valida `Host` para bloquear nombres arbitrarios, acepta loopback y direcciones privadas de LAN, y permite hostnames propios solo si se declaran en `NETSENTINEL_ALLOWED_HOSTS` (lista separada por comas). Las operaciones de modificación rechazan peticiones con origen diferente o marcadas como `cross-site`, y se agregan cabeceras HTTP defensivas.

Estas medidas reducen riesgos de DNS rebinding y CSRF en navegadores, pero no constituyen autenticación para acceso desde otros equipos. No expongas el panel sin controles adicionales. Si accedés por un hostname propio, configurá explícitamente `NETSENTINEL_ALLOWED_HOSTS`.

## Operación segura

- Mantener el host en `127.0.0.1`. No exponer el servidor a otras interfaces sin autenticación, protección CSRF/origen, HTTPS y una revisión de seguridad específica.
- El descubrimiento, el diagnóstico y las comprobaciones de monitorización generan tráfico cuando se solicitan o se habilitan expresamente. El panel rechaza descubrimientos simultáneos para no duplicar el sondeo de la LAN.
- Los comandos se ejecutan con argumentos separados y no interpolan valores del inventario como comandos.
- Los fabricantes, si se habilitan, se consultan únicamente en un CSV OUI local; no se envían direcciones MAC a servicios externos.
- La base SQLite, el respaldo descargable y las exportaciones pueden revelar topología y hábitos de red. Protegé el equipo y revisá los archivos antes de compartirlos. El respaldo se crea con la API de copia de SQLite para mantener una imagen consistente.
- Usá NetSentinel únicamente en redes y sobre objetivos que administrás o tenés autorización para revisar.
- Los webhooks externos están deshabilitados por defecto. Si configurás uno, protegé su URL como un secreto y usá HTTPS.

## Seguimiento de actividad por dispositivo

El historial inicial contiene únicamente observaciones de inventario. No captura paquetes ni inspecciona navegación. Cualquier futura fuente de flujos o captura debe activarse explícitamente, limitarse a un dispositivo y un intervalo, registrar solo metadatos necesarios, no almacenar cargas útiles, credenciales ni cookies, e informar los límites de visibilidad de la interfaz/red. En redes conmutadas o Wi-Fi, un equipo ordinario no suele ver todo el tráfico unicast de otros clientes; puede requerirse telemetría del router/AP o un puerto espejo autorizado.

## Funciones que exigen revisión específica

Las consultas SNMP, las integraciones con routers, los cambios de DNS, el bloqueo de dispositivos y la interceptación de proxy requieren una revisión de autorización, alcance, límites de tasa, auditoría, almacenamiento de secretos, reversión de cambios y tratamiento de datos sensibles antes de implementarse.

## Reporte de vulnerabilidades

No publiques credenciales, tokens ni detalles explotables en issues públicos. Hasta contar con un canal privado dedicado, abrí un issue con una descripción mínima y sin secretos.
