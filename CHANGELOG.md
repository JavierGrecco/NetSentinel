# Historial de cambios

## 0.5.1 — 11 de octubre de 2026

- Corrige el mensaje de inicio para aclarar que NetSentinel no sondea la red al arrancar y que el descubrimiento activo se inicia solo desde el panel.
- Agrega una prueba de regresión para el mensaje de inicio de la CLI.

## 0.5.0 — 11 de octubre de 2026

- Añade descubrimiento de red local sin configuración manual de subredes.
- Limita la búsqueda bajo demanda a dos subredes IPv4 privadas y hasta 254 direcciones por subred.
- Filtra el inventario del barrido a las subredes detectadas y excluye interfaces virtuales y túneles comunes.
- Configura pytest para encontrar el paquete del layout `src/` al ejecutar las pruebas desde el repositorio.
- Amplía CI a Python 3.14 y agrega pruebas del descubrimiento automático.

## 0.4.0 — 11 de octubre de 2026

- Agrega un resumen orientativo al diagnóstico de conectividad, con pasos sugeridos según los resultados.
- Distingue posibles problemas de DNS de pruebas de ping sin respuesta y aclara que ICMP puede estar filtrado.
- Muestra en el panel la versión real de la aplicación para evitar números desactualizados en la interfaz.

## 0.3.1 — 11 de octubre de 2026

- Unifica la versión del paquete y la aplicación para evitar metadatos desactualizados.
- Corrige las variables de tema del enlace a Monitorización.
- Amplía la CI a Python 3.11 y comprueba que el paquete distribuible incluya los HTML y CSS.

## 0.3.0 — 11 de octubre de 2026

- Agrega monitorización periódica de hosts, puertos TCP y endpoints HTTP/HTTPS.
- Guarda el resultado y la latencia de cada comprobación.
- Agrupa una caída en un único incidente y lo resuelve al volver a responder el servicio.
- Permite enviar avisos de caída y recuperación a un webhook HTTPS opcional.
- Separa los estilos CSS de la estructura HTML.
- Simplifica la instalación y mueve las instrucciones para desarrolladores a su propio documento.

## 0.2.0 — 2026-10-11

Mejora de inventario y procedencia de datos.

- Nuevo contrato `DiscoveryProvider` y proveedor de comandos de sistema intercambiables.
- Se combinan fuentes de vecinos disponibles y se toleran fallos parciales; se amplía la lectura IPv6 y NDP.
- Se registran varias direcciones IPv4/IPv6 por dispositivo/MAC con origen y fechas de primera/última observación.
- Se generan eventos revisables ante cambios detectados de IPv4 principal, con mensaje que aclara que debe verificarse.
- Se agrega resolución OUI local opcional, sin enviar direcciones MAC a servicios externos.
- Se agrega indicador de MAC localmente administrada (posiblemente aleatoria o manual).
- La API y el panel muestran fabricante, varias direcciones e historial de lecturas.
- La exportación pasa a formato JSON `netsentinel-data-export-v2` e incluye direcciones.
- La inicialización migra bases v0.1 de forma aditiva sin descartar los dispositivos existentes.
- Se amplían las pruebas de parser IPv6/NDP, migración, cambios IP, API y OUI.

## [0.1.0] — 2026-10-11

Primera entrega funcional del proyecto.

- Panel web local en español y API FastAPI documentada.
- Descubrimiento pasivo desde la tabla de vecinos del sistema operativo.
- Persistencia SQLite de dispositivos, lecturas y eventos.
- Lista de confianza, nombres personalizados y notas por dispositivo.
- Diagnóstico manual de gateway, DNS y conectividad IP externa con aviso previo.
- Exportación de inventario a CSV y copia de datos a JSON.
- Tests de parser, persistencia y API.
- CI multiplataforma inicial para Windows, macOS y Linux.
- Documentación de arquitectura, seguridad, contribución e implementación.
