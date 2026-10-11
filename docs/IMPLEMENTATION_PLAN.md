# Plan de implementación

## Estado actual

La versión 0.8.3 reúne inventario local, monitorización con informes de 24 horas/7 días exportables a CSV y una secuencia visual de comprobaciones recientes, diagnóstico guiado, búsqueda automática acotada a redes RFC 1918, lanzadores sencillos y copias de seguridad SQLite consistentes.

### Completado
- Panel de inventario, nombres, notas, confianza manual, búsqueda sobre direcciones secundarias y exportaciones CSV/JSON.
- Respaldo SQLite consistente descargable, con validación de integridad.
- Lanzadores de un clic para Windows y macOS/Linux con instalación incremental.
- Fuentes de descubrimiento separadas y seguimiento de direcciones.
- Descubrimiento automático limitado a RFC 1918: hasta dos redes, máximo 254 direcciones por segmento, una sola lectura simultánea y exclusión de interfaces virtuales conocidas.
- Métricas de alcance, respuestas ping y duración guardadas en el historial.
- Controles de ping, TCP y HTTP/HTTPS.
- Historial de resultados e incidentes que se deduplican.
- Resúmenes de comprobaciones correctas/fallidas y latencia por ventana temporal, tanto globales como por monitor; exportación CSV y secuencia visual de hasta 15 chequeos.
- Índice por fecha para acelerar los resúmenes del historial de monitorización.
- Notificaciones opcionales por webhook HTTPS.
- Protección de host/origen y cabeceras HTTP defensivas.
- Pruebas automatizadas y CI multiplataforma para Python 3.10–3.14 en Windows, macOS y Linux.

### Próximas etapas
1. Mejorar cobertura del descubrimiento, incluyendo estrategias para equipos que no responden a ICMP y una ruta IPv6 bien delimitada.
2. Incorporar integraciones opcionales de DNS y DHCP.
3. Agregar informes y visualización de tendencias.
4. Evaluar integraciones con routers según sus APIs y permisos.
5. Considerar un proxy separado solo tras definir su alcance y sus implicaciones de privacidad.

## Criterios de aceptación

Cada función nueva debe tener pruebas automatizadas, mensajes de error comprensibles, documentación de permisos y tráfico que genera, y una opción de desactivación cuando corresponda. Las pruebas no deben depender de Internet, una red real ni privilegios de administrador.
