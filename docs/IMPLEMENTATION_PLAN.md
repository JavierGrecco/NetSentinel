# Plan de implementación

## Estado actual

La versión 0.6.9 reúne inventario local, monitorización, diagnóstico guiado y búsqueda automática acotada a redes RFC 1918, con alcance, respuestas y duración de cada descubrimiento guardados en el historial.

### Completado
- Panel de inventario, nombres, notas, confianza manual y exportación.
- Fuentes de descubrimiento separadas y seguimiento de direcciones.
- Detección automática de las subredes IPv4 privadas activas y búsqueda local limitada, sin pedir al usuario que calcule el rango.
- Controles de ping, TCP y HTTP/HTTPS.
- Historial de resultados e incidentes que se deduplican.
- Notificaciones opcionales por webhook HTTPS.
- Pruebas automatizadas y CI multiplataforma.

### Próximas etapas
1. Mejorar cobertura del descubrimiento, incluyendo estrategias para equipos que no responden a ICMP y una ruta IPv6 bien delimitada.
2. Incorporar integraciones opcionales de DNS y DHCP.
3. Agregar informes y visualización de tendencias.
4. Evaluar integraciones con routers según sus APIs y permisos.
5. Considerar un proxy separado solo tras definir su alcance y sus implicaciones de privacidad.

## Criterios de aceptación

Cada función nueva debe tener pruebas automatizadas, mensajes de error comprensibles, documentación de permisos y tráfico que genera, y una opción de desactivación cuando corresponda. Las pruebas no deben depender de Internet, una red real ni privilegios de administrador.
