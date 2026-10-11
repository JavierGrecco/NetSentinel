# Seguridad y límites

## Alcance de la versión inicial

NetSentinel v0.2 es una herramienta de observación local. La lectura de tablas de vecinos no es un escaneo de todos los equipos: contiene solo entradas que el sistema ha aprendido. v0.2 conserva varias direcciones por MAC y puede leer ARP, `ip neigh` y NDP según el sistema operativo. Una MAC puede aleatorizarse o suplantarse; una alerta de dispositivo desconocido no demuestra una intrusión.

## Operación segura

- Ejecutar en la computadora donde está el usuario y mantener el host en `127.0.0.1`.
- No exponer el servidor a una interfaz de red sin autenticación, protección CSRF/origen, configuración HTTPS apropiada y revisión de seguridad.
- El diagnóstico genera tráfico de salida únicamente cuando se solicita desde el panel.
- Los comandos de lectura son listas fijas de argumentos; los valores del inventario no se ejecutan como comandos. Los fabricantes, si se habilitan, se consultan únicamente en un CSV OUI local.
- El archivo SQLite puede contener metadatos de red. Proteger la cuenta de usuario, evitar compartir copias sin revisarlas y eliminar la base cuando ya no sea necesaria.
- No utilizar en redes sin autorización.

## Funciones futuras que exigen revisión específica

El escaneo activo, las consultas SNMP, las modificaciones de routers/DNS y la interceptación de proxy deben ser módulos explícitos. Antes de habilitarlos, hay que definir autorización, límites de tasa, auditoría, almacenamiento de secretos, protección de credenciales, reversión de cambios y tratamiento de datos sensibles.

## Reporte de vulnerabilidades

Hasta configurar un canal dedicado, no publiques credenciales, tokens ni detalles explotables en issues públicos. Abrí un issue con una descripción mínima y sin secretos; se definirá un proceso privado de reporte antes de distribuir versiones estables.
