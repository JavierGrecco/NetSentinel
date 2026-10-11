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

La actividad familiar puede proceder del backend de metadatos o de la extensión Chromium explícita de `browser-extension/`. La extensión, apagada al instalarse, observa navegación futura en el navegador donde se instala; no lee contenido de páginas, formularios, pulsaciones, contraseñas, cookies o tokens. Las URLs HTTP(S) aceptadas por el modelo de visitas se normalizan: se eliminan fragmentos, parámetros conocidos de autenticación/sesión, búsqueda y seguimiento, y se rechazan credenciales embebidas y esquemas no HTTP(S). Los términos de búsqueda se guardan en un campo separado para motores que la extensión reconoce. Ningún filtro puede garantizar eliminar todos los datos personales que un sitio incruste en rutas o parámetros atípicos.

Las sesiones del backend son opt-in, se limitan a un dispositivo y un máximo de 12 horas, y la ingestión requiere un token aleatorio de sesión; en SQLite solo se conserva su hash. La retención es configurable entre 1 y 90 días. El backend no captura paquetes por sí mismo ni instala agentes. El token se muestra una sola vez y nunca se incluye en listados ni exportaciones. Los eventos importados desde la extensión se asocian manualmente al dispositivo que el operador elige; no se sincronizan automáticamente entre equipos.

En redes conmutadas o Wi-Fi, un equipo ordinario no suele ver todo el tráfico unicast de otros clientes; puede requerirse telemetría del router/AP o un puerto espejo administrado y autorizado. DNS/SNI/conexiones son indicios de actividad, no prueba de identidad ni de páginas vistas. No se debe intentar interceptar/deshacer TLS para obtener credenciales. La API está prevista para uso local: no expongas el panel en la LAN o Internet sin autenticación, TLS y revisión de seguridad adicionales.

## Funciones que exigen revisión específica

Las consultas SNMP, las integraciones con routers, los cambios de DNS, el bloqueo de dispositivos y la interceptación de proxy requieren una revisión de autorización, alcance, límites de tasa, auditoría, almacenamiento de secretos, reversión de cambios y tratamiento de datos sensibles antes de implementarse.

## Reporte de vulnerabilidades

No publiques credenciales, tokens ni detalles explotables en issues públicos. Hasta contar con un canal privado dedicado, abrí un issue con una descripción mínima y sin secretos.


### Importación de correo
La funcionalidad de correo es exclusivamente una importación explícita de metadatos desde una exportación de auditoría autorizada. Guarda fecha/proveedor/emisor/destinatarios/asunto opcional, nunca cuerpos ni adjuntos. La aplicación no se autentica en buzones, no extrae mensajes desde webmail y rechaza columnas de contenido. Los CSV importados deben tratarse como datos sensibles y mantenerse solo el tiempo necesario.
