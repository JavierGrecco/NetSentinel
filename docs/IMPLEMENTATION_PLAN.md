# Plan de implementación

## Estado actual

La versión 0.3 reúne un inventario local con historial y un primer módulo de monitorización.

### Completado
- Panel de inventario, nombres, notas, confianza manual y exportación.
- Fuentes de descubrimiento separadas y seguimiento de direcciones.
- Controles de ping, TCP y HTTP/HTTPS.
- Historial de resultados e incidentes que se deduplican.
- Notificaciones opcionales por webhook HTTPS.
- Pruebas automatizadas y CI multiplataforma.

### Próximas etapas
1. Mejorar el diagnóstico guiado y las explicaciones de los resultados.
2. Incorporar integraciones opcionales de DNS y DHCP.
3. Agregar informes y visualización de tendencias.
4. Evaluar integraciones con routers según sus APIs y permisos.
5. Considerar un proxy separado solo tras definir su alcance y sus implicaciones de privacidad.

## Criterios de aceptación

Cada función nueva debe tener pruebas automatizadas, mensajes de error comprensibles, documentación de permisos y tráfico que genera, y una opción de desactivación cuando corresponda. Las pruebas no deben depender de Internet, una red real ni privilegios de administrador.
