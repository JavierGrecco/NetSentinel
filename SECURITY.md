# Seguridad y límites

## Alcance de la versión 0.7.0

NetSentinel es una herramienta de observación local. El panel escucha en `127.0.0.1` de forma predeterminada y los datos se guardan en SQLite. La lectura pasiva de tablas de vecinos solo muestra direcciones que el sistema ya conoce; el descubrimiento activo está separado y comienza únicamente cuando el usuario lo solicita desde el panel.

El descubrimiento activo detecta interfaces compatibles y se limita a subredes privadas RFC 1918: `10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. Examina como máximo dos subredes y, si una es mayor que /24, reduce el alcance a un /24. Envía como máximo un ping por dirección dentro de esos límites y acepta una sola ejecución de descubrimiento simultánea. No escanea Internet ni cambia la configuración de ningún dispositivo. Algunos equipos pueden no responder; los resultados no garantizan un inventario completo.

Una MAC puede aleatorizarse o suplantarse; una alerta de dispositivo desconocido no demuestra una intrusión. Las interfaces Apple de enlace local como AWDL/LLW no se consideran dispositivos de una LAN convencional en nuevas lecturas; las alertas históricas se etiquetan visualmente sin borrar eventos ni datos. El historial del descubrimiento conserva también la duración de cada ejecución.

## Protección de la interfaz local

NetSentinel valida el encabezado `Host` para aceptar loopback y direcciones privadas de LAN, más hostnames adicionales configurados explícitamente en `NETSENTINEL_ALLOWED_HOSTS` (lista separada por comas). Las operaciones de modificación bloquean solicitudes del navegador con origen distinto y peticiones marcadas como `cross-site`. También se envían cabeceras anti-framing y anti-MIME-sniffing.

Estas defensas reducen riesgos de DNS rebinding y CSRF en navegadores, pero no reemplazan la autenticación si se expone el panel a otros equipos. No uses `--host 0.0.0.0` en redes compartidas sin controles de acceso adicionales. Si usás un hostname propio, agregalo explícitamente a `NETSENTINEL_ALLOWED_HOSTS`.

## Operación segura

- Mantener el host de escucha en `127.0.0.1`. No exponer el panel a otras interfaces sin autenticación, protección CSRF/origen, HTTPS y una revisión de seguridad específica.
- El descubrimiento local genera tráfico únicamente al solicitarlo desde el panel. El diagnóstico y las comprobaciones de monitorización también generan tráfico cuando se ejecutan.
- Los comandos de lectura y ping usan argumentos separados; los datos del inventario nunca se ejecutan como comandos.
- Los fabricantes, si se habilitan, se consultan únicamente en un CSV OUI local. No se envían direcciones MAC a un proveedor externo para resolver fabricantes.
- El archivo SQLite puede contener metadatos de red. Protegé la cuenta de usuario, revisá las exportaciones antes de compartirlas y conservá copias de seguridad seguras.
- Usá NetSentinel únicamente en redes y sobre objetivos que administrás o tenés autorización para revisar.
- Los webhooks externos están deshabilitados por defecto. Si configurás uno, protegé su URL como un secreto y usá HTTPS.

## Funciones que exigen revisión específica

Las consultas SNMP, las integraciones con routers, los cambios de DNS, el bloqueo de dispositivos y la interceptación de proxy requieren una revisión de autorización, alcance, límites de tasa, auditoría, almacenamiento de secretos, reversión de cambios y tratamiento de datos sensibles antes de implementarse.

## Reporte de vulnerabilidades

No publiques credenciales, tokens ni detalles explotables en issues públicos. Hasta contar con un canal privado dedicado, abrí un issue con una descripción mínima y sin secretos.
