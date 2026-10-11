# Arquitectura de NetSentinel

NetSentinel es una aplicación local. El servidor web expone un panel y una API en `127.0.0.1`; SQLite guarda el inventario y el historial.

## Componentes

- **Panel web:** HTML y hojas CSS independientes para el inventario y la monitorización.
- **API:** FastAPI valida los datos recibidos y llama a la lógica de la aplicación.
- **Descubrimiento:** lee fuentes del sistema operativo y normaliza las observaciones de red.
- **Inventario:** registra dispositivos, direcciones, confianza manual y eventos.
- **Monitorización:** ejecuta comprobaciones de ping, TCP y HTTP/HTTPS con límites de tiempo.
- **Incidentes:** agrupa fallos consecutivos de un mismo control y registra su recuperación.
- **Notificaciones:** envía avisos solo si se configura explícitamente un webhook HTTPS.
- **Persistencia:** SQLite almacena dispositivos, monitores, comprobaciones, incidentes y registros de notificación.

## Límites importantes

La lista de vecinos del sistema no es una vista completa de todos los equipos de la red. Los resultados dependen del sistema operativo y de la actividad reciente. Una dirección o fabricante por sí solo no demuestra que un dispositivo sea legítimo o malicioso.

Los controles de disponibilidad generan tráfico hacia objetivos configurados por el usuario. Las funciones que cambien la configuración de la red no forman parte de esta versión.

## Pruebas

Las pruebas usan datos sintéticos y no requieren una red real. GitHub Actions valida la instalación y la suite de pruebas en Windows, macOS y Ubuntu con distintas versiones de Python.
