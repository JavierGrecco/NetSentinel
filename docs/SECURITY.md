# Seguridad y límites

## Alcance de la versión actual

NetSentinel mantiene el inventario local y puede iniciar un descubrimiento activo cuando el usuario lo solicita desde el panel. Detecta automáticamente subredes IPv4 privadas en interfaces activas compatibles, excluye interfaces virtuales y túneles conocidos, limita la búsqueda a un máximo de dos subredes y 254 direcciones por subred y envía como máximo un ping por dirección. Después filtra la tabla local de vecinos para guardar únicamente IPv4 dentro de esos rangos. No explora direcciones públicas, no cambia configuraciones y no bloquea equipos.

El descubrimiento es best effort: algunos dispositivos bloquean ICMP, redes invitadas pueden aislar clientes y una LAN exclusivamente IPv6 no entra en este barrido. Una MAC puede aleatorizarse o suplantarse; una alerta de dispositivo desconocido no demuestra una intrusión.

## Operación segura

- Ejecutar en la computadora donde está el usuario y mantener el host en `127.0.0.1`.
- No exponer el servidor a una interfaz de red sin autenticación, protección CSRF/origen, configuración HTTPS apropiada y revisión de seguridad.
- El diagnóstico y el descubrimiento de la red generan tráfico únicamente cuando se solicitan desde el panel. El descubrimiento se limita a subredes IPv4 privadas detectadas localmente.
- Los comandos de lectura son listas fijas de argumentos; los valores del inventario no se ejecutan como comandos. Los fabricantes, si se habilitan, se consultan únicamente en un CSV OUI local.
- El archivo SQLite puede contener metadatos de red. Proteger la cuenta de usuario, evitar compartir copias sin revisarlas y eliminar la base cuando ya no sea necesaria.
- No utilizar en redes sin autorización.

## Funciones futuras que exigen revisión específica

Las consultas SNMP, las modificaciones de routers/DNS y la interceptación de proxy siguen fuera del alcance. Antes de incorporarlas, hay que definir autorización, límites de tasa, auditoría, almacenamiento de secretos, protección de credenciales, reversión de cambios y tratamiento de datos sensibles.

## Reporte de vulnerabilidades

Hasta configurar un canal dedicado, no publiques credenciales, tokens ni detalles explotables en issues públicos. Abrí un issue con una descripción mínima y sin secretos; se definirá un proceso privado de reporte antes de distribuir versiones estables.

## Monitorización de disponibilidad

Los monitores contactan con los objetivos que configura quien administra la aplicación. Los intervalos están limitados a 15 segundos como mínimo y los tiempos de espera a 10 segundos como máximo. El monitor HTTP no sigue redirecciones y rechaza credenciales, parámetros y fragmentos en las URL. Los webhooks deben usar HTTPS; su URL se configura mediante una variable de entorno y no se almacena en la base de datos. No supervises sistemas sin autorización ni publiques secretos en incidencias.
