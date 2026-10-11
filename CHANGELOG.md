# Historial de cambios

## 0.7.0 — 11 de octubre de 2026

- Agrega lanzadores para iniciar NetSentinel con un clic en Windows y macOS, además de un script común para macOS/Linux.
- Los lanzadores crean un entorno virtual local, verifican Python 3.10 o posterior e instalan el proyecto sin modificar el Python global.
- Mejora los mensajes ante Python no compatible, instalación fallida o entornos virtuales antiguos.

## 0.6.9 — 11 de octubre de 2026

- Reinterpreta visualmente alertas históricas de interfaces Apple AWDL/LLW como observaciones de enlace local, no como evidencia de un dispositivo de la LAN.
- Mantiene intactos los eventos y registros originales; solo aclara su presentación.

## 0.6.8 — 11 de octubre de 2026

- Mide y guarda el tiempo total que tarda cada descubrimiento local, incluyendo la lectura de vecinos.
- Muestra la duración de cada búsqueda en el historial, junto con las subredes y las respuestas a ping.
- Agrega una prueba para validar la métrica de duración.

## 0.6.7 — 11 de octubre de 2026

- Reconoce visualmente eventos históricos cuya IP coincide con la dirección local de la computadora, sin marcarla automáticamente como confiable ni borrar el evento.
- Reutiliza el mismo cálculo de IP locales para la tabla de inventario y la actividad reciente.

## 0.6.6 — 11 de octubre de 2026

- Identifica visualmente la IP local de la computadora según el informe de descubrimiento más reciente, para distinguirla de otros dispositivos de la LAN.
- Agrega una comprobación automatizada para mantener visible esa aclaración en el panel.

## 0.6.5 — 11 de octubre de 2026

- Añade el BOM UTF-8 a la exportación CSV para que Excel reconozca mejor los acentos y caracteres españoles.
- Extiende la prueba de exportación para comprobar la marca de codificación.

## 0.6.4 — 11 de octubre de 2026

- Amplía la exportación CSV con todas las direcciones IP observadas por dispositivo, su cantidad, interfaz y procedencia.
- Agrega cobertura para comprobar que las direcciones IPv4 e IPv6 secundarias no se pierdan en el CSV.

## 0.6.3 — 11 de octubre de 2026

- Incluye el informe de descubrimiento como objeto JSON en las exportaciones, igual que en la API, en lugar de exportar el JSON serializado dentro de una cadena.
- Actualiza la guía de seguridad que está enlazada desde el README con los límites activos actuales.

## 0.6.2 — 11 de octubre de 2026

- Evita que solicitudes simultáneas inicien más de un descubrimiento local; devuelve HTTP 409 con un mensaje claro mientras hay una lectura en curso.
- Agrega una prueba de concurrencia para comprobar que una segunda solicitud no dispara otro descubrimiento.

## 0.6.1 — 11 de octubre de 2026

- Hace que la búsqueda del inventario encuentre también direcciones IPv4/IPv6 secundarias e interfaces.
- Carga el inventario y su historial de direcciones por lote para evitar consultas SQLite repetidas por cada dispositivo.
- Agrega una prueba para localizar un dispositivo mediante una dirección IPv6 secundaria.

## 0.6.0 — 11 de octubre de 2026

- Restringe el descubrimiento automático a redes privadas RFC 1918 (10/8, 172.16/12 y 192.168/16), evitando rangos especiales y de documentación.
- Guarda el informe de cada descubrimiento en el historial: subredes, interfaces, direcciones consultadas y respuestas ping.
- Muestra las métricas del descubrimiento en el panel, no solo en el aviso temporal.
- Omite entradas de las interfaces de enlace local Apple AWDL/LLW en nuevas lecturas y etiqueta los registros históricos que ya existían.
- Agrega `httpx2` al entorno de pruebas para evitar la advertencia deprecada de Starlette TestClient.
- Añade pruebas para rangos de red elegibles, filtrado de interfaces virtuales y migración de bases SQLite existentes.

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
