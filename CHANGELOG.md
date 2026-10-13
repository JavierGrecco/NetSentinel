# Historial de cambios

## Próxima versión — 0.10.0 (en desarrollo)

- Evita sondeos accidentales sobre puentes virtuales habituales de Linux (`br*`, `veth*`, Docker, Podman, CNI, Flannel, LXC y OVS), manteniendo el descubrimiento en las interfaces LAN compatibles; añade pruebas para redes virtuales aisladas y coexistentes con la LAN física.
- Actualiza la guía de protección de `main`: incluye el nuevo job obligatorio de dependencias mínimas entre los checks de CI y aclara que la protección de rama debe confirmarse en GitHub, no se aplica desde los documentos.
- Añade una regresión de CI que altera de forma aislada una cota de prueba y verifica que el validador de dependencias mínimas la rechace, evitando que un verificador que deje de detectar divergencias pase inadvertido.
- Amplía la CI con un job que instala y prueba conjuntamente las versiones mínimas declaradas de las dependencias runtime y de test, evitando asumir compatibilidad solo porque la matriz usa las versiones más nuevas disponibles.
- Corrige el límite inferior declarado de `httpx2`: `1.0.0` no es una publicación instalable; el mínimo declarado y fijado para la prueba es ahora `2.0.0`. La CI verifica automáticamente que `pyproject.toml` y las constraints no vuelvan a desalinearse.
- Corrige las gráficas de latencia para respetar la CSP basada en hashes: reemplaza los cambios de estilo inline bloqueados por atributos de altura con bandas CSS predefinidas y agrega una regresión de interfaz.
- Aísla errores de comprobaciones programadas: un fallo inesperado o de almacenamiento de un monitor se registra y no impide comprobar los siguientes; incorpora una regresión determinista sin red real.
- Amplía la neutralización CSV para cubrir controles ASCII y espacios Unicode antes de prefijos de fórmula, alineando la defensa del backend con el exportador de la extensión; añade casos de regresión.
- Corrige la ejecución del endurecimiento de permisos SQLite: el helper estaba decorado accidentalmente como administrador de contexto y no se ejecutaba al abrir la base. Añade regresiones para archivos existentes con permisos 0644 y para preservar el destino de enlaces simbólicos.
- Evita que errores 422 de validación reflejen valores enviados (por ejemplo, tokens o CSV privado): conserva ubicación, mensaje y tipo, elimina `input` y `ctx`, y agrega una prueba de regresión.
- Aclara el alcance real del saneamiento de navegación en la UI, API y documentación: se guardan URLs normalizadas con host/ruta parcial, algunos identificadores se redactan, pero pueden persistir segmentos o parámetros desconocidos; añade pruebas del aviso de privacidad.
- Centraliza el saneamiento de fórmulas de hojas de cálculo en un helper común y lo aplica al inventario, la actividad y los informes de monitorización; agrega una regresión que verifica la exportación segura sin modificar SQLite.
- Canonicaliza `--host localhost` a `127.0.0.1` y rechaza aliases de hostname no literales para que el bind no dependa del resolvedor local; el lanzador Windows conserva y devuelve el código de salida real de la aplicación.
- Aplica la retención configurada también a la ingestión en vivo: rechaza metadatos retrasados fuera de ventana en lugar de aceptarlos y eliminarlos inmediatamente en la siguiente lectura; agrega una regresión de API.
- Limita la lectura CSV de actividad a 1.000 filas antes de materializar el lote y traduce campos/cabeceras demasiado grandes a errores de validación 422 en vez de errores internos; añade regresiones para importación y vista previa sin escrituras parciales.
- Evita cambiar permisos del destino cuando `netsentinel.sqlite3` es un enlace simbólico: el endurecimiento de archivos regulares usa un descriptor abierto sin seguir el enlace, con una regresión POSIX específica.
- Endurece la protección CSRF de operaciones de modificación: bloquea Fetch Metadata `same-site` además de `cross-site` cuando no es el origen exacto de la interfaz, incluso si falta `Origin`; agrega regresiones de rechazo y compatibilidad same-origin.
- Corrige la selección de subredes duplicadas: la preferencia por interfaces físicas se aplica antes de deduplicar, para que el orden de enumeración del sistema no oculte una interfaz mejor.
- Evita endurecer por accidente los permisos del destino de un enlace simbólico usado como `~/.netsentinel`: conserva la ruta predeterminada sin resolverla y prueba el flujo real de configuración, SQLite y permisos.
- Evita que una resolución DNS bloqueada detenga la monitorización secuencial: TCP/HTTP se ejecutan en procesos terminables con plazo global y el webhook opcional queda limitado a 5 segundos. Añade regresiones para timeout, salida inválida y arranque del proceso hijo.
- Evita que una resolución DNS A/AAAA o PTR bloquee indefinidamente una solicitud: las consultas interactivas se aíslan en un proceso terminable con límite de 3 segundos. Añade pruebas de timeout, errores del resolvedor y rechazo de salida malformada.
- Evita importaciones CSV contradictorias con la retención de actividad: previsualización e importación rechazan lotes con filas fuera del plazo configurado antes de escribir, con mensaje para ampliar la retención; la operación se serializa con cambios de política.
- Añade retención configurable para comprobaciones detalladas de monitorización: 90 días por defecto, limpieza al inicio y diaria, opción de desactivación explícita y pruebas de que la limpieza no borra incidentes ni el estado actual.
- Corrige la protección de permisos SQLite: no cambia el modo de directorios personalizados preexistentes (evita alterar `/tmp` u otras carpetas compartidas), conserva privado `~/.netsentinel` y crea de forma privada los directorios faltantes; agrega regresiones multiplataforma.
- Bloquea llamadas cross-site a endpoints GET que generan consultas DNS/PTR mediante Fetch Metadata y validación de `Origin`; añade regresiones que verifican que el resolvedor no se invoca y que las consultas de mismo origen siguen funcionando.
- Serializa las mutaciones del listado de eventos Chromium (navegación, limpieza inicial y borrado explícito) en el service worker; el popup deja de escribir snapshots de eventos al renderizar. Añade regresiones para capturas simultáneas, orden de borrado y exclusión de IPv4-mapped IPv6/links locales IPv6 del registro de navegación.
- Elimina la última excepción `script-src unsafe-inline`: reemplaza la ruta autogenerada de Swagger UI por un endpoint explícito que calcula una CSP con hash SHA-256 del inicializador de cada respuesta, manteniendo el CDN restringido a `/api/docs`.
- Retira `style-src unsafe-inline` de las cinco pantallas principales y de `/api/docs`: externaliza el CSS específico de Actividad, Herramientas y Hallazgos, sustituye estilos inline por clases y verifica las nuevas hojas en el wheel.
- Elimina `unsafe-inline` de `script-src` en las cinco pantallas principales: autoriza los scripts inline mediante hashes SHA-256 específicos por página y agrega pruebas para evitar handlers inline. El inicializador dinámico de Swagger UI queda como la única excepción pendiente para esa política.
- Añade Content Security Policy y Permissions-Policy: restringe recursos al origen local, impide framing/objetos y desactiva funciones del navegador no utilizadas. La excepción CDN de Swagger queda limitada a `/api/docs`; las cabeceras también se prueban en rechazos de Host.
- Endurece el arranque: el CLI rechaza enlaces que no sean loopback hasta contar con autenticación y control de acceso; valida puertos TCP y genera URLs correctas para IPv6. Añade regresiones para hosts remotos y puertos inválidos.
- Endurece la cadena de suministro: escaneo de secretos con Gitleaks, SBOM CycloneDX, checksums SHA-256 con detección de alteraciones y atestaciones Sigstore para releases etiquetadas; CI comprueba de forma regresiva el verificador de checksums.
- Añade una primera vista unificada de hallazgos en `/api/findings` y exportación JSON: normaliza eventos de inventario e incidentes de monitorización con evidencia, procedencia, estado, severidad y confianza diferenciadas; omite duplicados de transiciones de monitorización y mantiene el proceso en solo lectura. Los tipos duplicados se excluyen en SQL antes de aplicar el límite, para que no oculten eventos de inventario anteriores.
- Añade la bandeja visual `/findings`, filtros por estado, panel expandible de evidencia/procedencia, reconocimiento de eventos de inventario y exportación JSON; valida el JavaScript integrado en CI y evita almacenar la vista en caché del navegador.
- Documenta la dirección de producto, la priorización empresarial y los criterios de aceptación de seguridad, privacidad, UX, pruebas y releases.
- Alinea la nomenclatura de actividad de navegador y red con telemetría autorizada, consentimiento, alcance visible y retención; elimina referencias de interfaz orientadas a vigilancia familiar.

- Incorpora en Herramientas una inspección TLS puntual de endpoints autorizados: valida el certificado, informa vencimiento, nombres, versión TLS y cifrado negociado sin solicitar contenido HTTP ni guardar resultados.
- Amplía la CI para validar la sintaxis JavaScript embebida en la página Herramientas.

- Unifica la navegación principal de Inventario, Monitorización, Herramientas y Actividad con enlaces consistentes, estado de sección actual y estilos adaptables a pantallas pequeñas.
- Añade una prueba automatizada que verifica los cuatro enlaces y el indicador de página actual en cada módulo.

- Reduce los permisos de la extensión Chromium: elimina el acceso de host global innecesario y comprueba que no vuelva a solicitarse en las pruebas.
- Añade guía de primer uso a la pantalla principal, con pasos simples para descubrir dispositivos, reconocerlos y revisar la confianza.
- Distingue una búsqueda sin coincidencias de un inventario vacío para evitar mensajes confusos.
- Incorpora validación sintáctica del JavaScript embebido del panel principal en GitHub Actions y actualiza la documentación de DNS y seguridad.

- Añade pruebas del CSV del popup para fórmulas/escapado y validación CI de Manifest V3, permisos mínimos y apagado por defecto.
- Amplía las pruebas Node del service worker para estados opt-in, frames/privado, exclusiones, toggles, retención y deduplicación de navegación.
- Refuerza el saneamiento de URLs en extensión y backend con detección de OAuth/redirect, claves doblemente codificadas, más tracking, IPv6 canónico y redacción heurística de segmentos reconocibles; añade pruebas Python/Node a la CI.
- Añade filtros de historial, exportación CSV y borrado selectivo por fuente, además del dispositivo, tipo de evento y fechas.
- Añade borrado selectivo de eventos con previsualización no destructiva, alcance obligatorio y confirmación exacta del recuento bajo transacción SQLite.
- Incorpora filtros del historial de actividad por dispositivo, tipo y fechas UTC, y exportación CSV de la selección hasta 10.000 filas con neutralización de fórmulas.
- Incorpora vista previa CSV de solo lectura: valida el archivo completo, marca duplicados, estima altas y muestra hasta 10 filas normalizadas antes de confirmar la importación.
- Hace idempotente la importación CSV de metadatos: las filas idénticas ya importadas para el mismo dispositivo se omiten y se muestran en el recuento; no se deduplican eventos de fuentes en vivo.
- Inicia el módulo de herramientas DNS de solo lectura mediante el resolvedor configurado en el sistema.
- Agrega una vista local de actividad familiar en `/activity`, con sesiones limitadas por dispositivo, token de ingestión de un solo uso, validación estricta de metadatos e importación CSV local.
- Añade una extensión Chromium visible y desactivada por defecto para registrar páginas navegadas y búsquedas de motores compatibles en el dispositivo donde se instala; exporta un CSV para importación manual en NetSentinel.
- Amplía el modelo de actividad con `page_visit` y `search_query`; las URLs se normalizan para quitar fragmentos y parámetros sensibles/de seguimiento conocidos, mientras los términos de búsqueda se guardan separados.
- Extiende la CI para comprobar la sintaxis JavaScript de la extensión y la presencia de sus archivos.
- Añade importación de metadatos de correo desde CSV de auditoría autorizado (fecha, proveedor, emisor, destinatarios y asunto opcional); se rechazan los campos de cuerpo, mensaje, contenido y adjuntos.
- Normaliza alias comunes de cabeceras en exportaciones CSV de Google Workspace Email Log Search y Microsoft 365 Message Trace; el adaptador/API nativo de cada proveedor sigue pendiente.
- Persiste eventos DNS, conexiones, SNI visible, uso de aplicaciones reportado por una fuente compatible y bloqueos reportados; no instala un capturador automático ni un agente.
- Añade retención configurable entre 1 y 90 días, un resumen de dominios observados y límites de 1.000 eventos/1 MB por importación CSV.
- Rechaza URLs/rutas y campos no admitidos, incluidos usuario, contraseña, tokens, cookies y payloads; el token de ingestión se almacena como hash.
- Amplía la exportación JSON a `netsentinel-data-export-v4` para incluir sesiones y eventos de actividad sin exportar el hash del token.
- Añade pruebas de API, fuente, sesión, importación, retención y redacción de credenciales; la suite se ejecuta en la matriz de CI multiplataforma.
- Añade una ruta PTR por dispositivo bajo demanda y una acción en la tabla de inventario; no modifica los datos guardados y maneja dispositivos inexistentes o sin direcciones. La interfaz aclara que el nombre DNS no verifica identidad.
- Valida nombres de host y devuelve direcciones IPv4/IPv6 deduplicadas.
- Añade rutas API para consulta A/AAAA y DNS inverso PTR bajo demanda, con pruebas unitarias simuladas.
- Incorpora una interfaz PTR que valida la IP ingresada y distingue errores del resolvedor.
- Muestra los servidores DNS locales detectables en modo de solo lectura, con fuente y advertencias sobre VPN, split DNS y diferencias entre sistemas.
- Clasifica fallos DNS en nombre no encontrado, error temporal y error general; la API responde con códigos HTTP diferenciados (404, 503 y 502).
- Aclara en la interfaz y la documentación que los nombres DNS no son prueba de identidad.
- Reordena el roadmap para desarrollar módulos independientes sin degradar el núcleo de inventario y monitorización.
- Agrega pruebas simuladas para el parser de resolv.conf, la detección por plataforma y el endpoint de configuración.
- Añade caché PTR en memoria, acotada por TTL y cantidad de entradas, con fecha de resolución y señalización de resultados cacheados; los fallos no se almacenan.

## 0.9.0 — 11 de octubre de 2026

- Permite exportar hasta 5000 incidentes en CSV, filtrados por abiertos o resueltos, con duración estimada, recuperación, cantidad de fallos y detalle final.
- Amplía las tendencias de latencia: una barra por hora para 24 horas y una por bloque de seis horas para los últimos siete días.
- Añade exportación CSV de métricas históricas agrupadas, con UTF-8, neutralización de fórmulas y cabeceras sin caché.
- Incorpora filtros visuales de incidentes y pruebas de agregación temporal, exportación segura y respuestas 404/422.

## 0.8.4 — 11 de octubre de 2026

- Añade duración desde la detección y tiempo hasta la recuperación a los incidentes, señalando que son estimaciones basadas en la cadencia de comprobaciones.
- Muestra la recuperación media de incidentes resueltos en el período seleccionado de 24 horas o 7 días.
- Incorpora un gráfico de la latencia en las últimas 15 comprobaciones por monitor, con media, mínimo y máximo de las mediciones disponibles.
- Amplía las pruebas de duraciones, agregados de recuperación y visualización accesible; no genera tráfico de red adicional.

## 0.8.3 — 11 de octubre de 2026

- Añade una secuencia visual de las 15 comprobaciones más recientes por monitor, ordenada cronológicamente y con distinción accesible entre éxitos y fallos.
- Mantiene el historial detallado debajo de la secuencia para facilitar la investigación de una caída.
- Amplía las pruebas de interfaz para verificar la presencia de la secuencia y sus estilos de estado.

## 0.8.2 — 11 de octubre de 2026

- Añade un índice SQLite por fecha de comprobación para acelerar los resúmenes de 24 horas y 7 días cuando crezca el historial.
- La creación del índice es idempotente y no modifica ni elimina chequeos existentes.
- Agrega una prueba que verifica el índice requerido para consultas por período.

## 0.8.1 — 11 de octubre de 2026

- Agrega la exportación CSV de informes de monitorización para el período seleccionado (24 horas o 7 días), con estado actual, resultados, tasa de éxito y métricas de latencia.
- Protege el CSV contra la interpretación de nombres con fórmulas por parte de hojas de cálculo y evita caché del navegador.
- Añade pruebas para contenido, fórmula CSV y cabeceras del endpoint.

## 0.8.0 — 11 de octubre de 2026

- Agrega un resumen de monitorización para las últimas 24 horas o los últimos 7 días, con comprobaciones correctas/fallidas, tasa de éxito basada en muestras, latencia media y número de incidentes abiertos.
- Añade métricas por monitor: cantidad de comprobaciones, fallos, tasa de éxito y latencia media/mínima/máxima.
- Presenta las tendencias directamente en el panel y actualiza el resumen al cambiar de período.
- Agrega pruebas sobre agregados, ventanas vacías, límites de período y el endpoint.

## 0.7.3 — 11 de octubre de 2026

- Añade una descarga SQLite consistente y comprobable, apta para conservar el inventario, los eventos, lecturas y monitorización en una copia real.
- Agrega el enlace de copia SQLite al panel junto a las exportaciones CSV y JSON.
- Prueba que las copias se puedan abrir y pasen `PRAGMA integrity_check`.
- Marca las descargas CSV, JSON y SQLite como `no-store` para evitar su almacenamiento en caché del navegador.

## 0.7.2 — 11 de octubre de 2026

- Los lanzadores recuerdan una huella de `pyproject.toml` y verifican las dependencias y la ruta editable del paquete antes de instalar.
- Las aperturas normales no vuelven a ejecutar `pip install`; la instalación se repite solo si cambian dependencias/metadatos o falta un módulo.
- Agrega pruebas para la comprobación de instalación incremental en Windows, macOS y Linux.

## 0.7.1 — 11 de octubre de 2026

- Añade protección de Host para bloquear nombres no autorizados y reducir el riesgo de DNS rebinding hacia la interfaz local.
- Bloquea mutaciones de navegador que provengan de otro origen o se identifiquen como `cross-site`; los clientes no navegador sin cabecera Origin siguen funcionando.
- Añade cabeceras HTTP defensivas contra MIME sniffing, framing y lectura de recursos desde otros orígenes.
- Permite configurar hostnames adicionales explícitamente mediante `NETSENTINEL_ALLOWED_HOSTS`.
- Agrega pruebas para hosts no autorizados, CSRF, hostnames explícitos y cabeceras de seguridad.

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
