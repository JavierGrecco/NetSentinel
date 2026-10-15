# Extensión Chromium de NetSentinel: páginas y búsquedas

Esta extensión registra navegación futura en el dispositivo donde está instalada. Funciona con Chrome y navegadores Chromium compatibles, como Edge. Está apagada al instalarse y requiere activación explícita desde su panel.

## Instalación

1. Descargá y descomprimí el ZIP completo del repositorio en el equipo cuyo navegador querés observar.
2. Abrí chrome://extensions en Chrome o edge://extensions en Edge.
3. Activá el modo de desarrollador y elegí **Cargar descomprimida**.
4. Seleccioná la carpeta browser-extension del repositorio.
5. Abrí el ícono de NetSentinel. Revisá los permisos y activá **Activar seguimiento**.
6. Elegí si querés registrar páginas, búsquedas, exclusiones de dominio y retención de 1 a 90 días.

La extensión solicita solo los permisos `storage` y `webNavigation`: el primero conserva la configuración y los eventos en este navegador, y el segundo recibe notificaciones de navegación. No solicita permisos de host, cookies, historial web ni interceptación de solicitudes. El seguimiento está apagado por defecto y queda visible en el popup.

## Qué registra

Registra eventos de navegación de nivel superior y cambios de URL que comunica la API de navegación del navegador. La extensión reconoce consultas en Google, Bing, DuckDuckGo, Yahoo, Ecosia, Brave Search, Yandex, Baidu, YouTube, Wikipedia, Amazon, Reddit y TikTok.

La URL de página se normaliza antes de guardarse; no es una copia exacta de la URL original. Se elimina el fragmento, parámetros típicos de autenticación/sesión, OAuth/redirect, búsqueda y seguimiento; los nombres de parámetros se inspeccionan con decodificación repetida y se descartan si permanecen ambiguamente codificados. Los segmentos de ruta reconocibles como correos, teléfonos, UUID e identificadores opacos largos se sustituyen por `[redacted]`; también se redactan los segmentos cuyo contenido no puede inspeccionarse con seguridad por codificación anidada o inválida. No se registran destinos de loopback, RFC1918, enlace local, CGNAT (`100.64.0.0/10`), rangos IPv4 seleccionados de uso especial (incluidos documentación, benchmarking, `192.0.0.0/24` salvo las excepciones globales `.9` y `.10`, el bloque legado `192.88.99.0/24`, multicast y reservado) ni prefijos IPv6 seleccionados de multicast, documentación, benchmarking, transición, dummy/local-use y enrutamiento especial; tampoco hostnames locales/de prueba habituales (`.local`, `.lan`, `.localhost`, `.test`, `.example`, `.invalid`, `.arpa`). El host de otros sitios, segmentos de ruta y parámetros no reconocidos pueden mantenerse y contener datos personales. La extensión omite URLs saneadas con más de 200 parámetros de consulta o más de 2048 caracteres, usando los mismos límites que el importador del backend; el backend vuelve a validar y sanear las URLs al importar el CSV.

El saneamiento de rutas es heurístico: puede ocultar segmentos largos que no sean secretos y no puede detectar nombres de usuario arbitrarios ni cualquier identificador que un sitio incluya en una ruta o en parámetros desconocidos. Los términos de búsqueda reconocidos se guardan aparte del URL saneado. Al abrir el panel o actualizar la extensión, el service worker vuelve a validar los eventos históricos antes de mostrarlos o exportarlos: sanea de nuevo las URLs, reconstruye el dominio a partir del host canónico, descarta destinos privados/locales, formatos inválidos y tipos de evento desconocidos, y elimina campos que no pertenecen al contrato de metadatos. La limpieza usa la misma cola de escritura que la captura para no sobrescribir navegación concurrente. Los eventos válidos dentro de retención se conservan; la migración no recupera contenido que ya fue descartado ni envía datos a servidores externos. La CI también ejecuta pruebas de comportamiento del service worker: apagado por defecto, activación explícita, límites de navegación, exclusiones de dominio, captura independiente de páginas/búsquedas, retención, deduplicación y persistencia serializada de eventos concurrentes, limpieza inicial y borrado explícito a través del service worker para evitar que contextos separados sobrescriban registros recientes con snapshots obsoletos de `chrome.storage.local`. Estas pruebas automáticas no sustituyen el ensayo manual en Chrome y Edge.

No lee el historial previo, contenidos de páginas, campos de formularios, pulsaciones de teclado, contraseñas, cookies, tokens ni mensajes. No captura búsquedas internas de aplicaciones nativas ni formatos de búsqueda que la extensión no reconoce. La navegación privada no está habilitada de forma predeterminada; no actives ese permiso si no lo necesitás.

## Importar registros en NetSentinel

1. En el navegador supervisado, abrí la extensión y pulsá **Exportar CSV para NetSentinel**.
2. Abrí NetSentinel en la computadora que administra el inventario y visitá /activity.
3. Seleccioná el dispositivo correspondiente y, en **Importar registros CSV**, elegí netsentinel-browser-activity.csv.
4. Revisá los registros page_visit y search_query en la tabla de actividad.

La transferencia entre dispositivos es manual en esta versión. El CSV permanece bajo tu control; la extensión no sube datos a la nube ni se conecta automáticamente a otra computadora. La sincronización central en vivo requiere autenticación y transporte seguro, y sigue pendiente.

## Privacidad y límites

Las URLs y los términos de búsqueda pueden revelar información personal sensible. Usá la extensión solo en dispositivos que administrás con autorización, informá a las personas responsables y usuarias del dispositivo, según las políticas y autorizaciones aplicables, configurá dominios excluidos y conserva los datos solo el tiempo necesario. El almacenamiento permanece local hasta que exportás o borrás registros.

Los filtros eliminan parámetros comunes sensibles y redactan tipos reconocibles de identificador en la ruta, pero ningún filtro genérico puede identificar todos los secretos que una web podría incluir en una ruta o en parámetros desconocidos. La CI incluye pruebas automatizadas para OAuth/tokens, claves doblemente codificadas, seguimiento, IPv6 y segmentos de ruta; siguen pendientes pruebas manuales con sitios reales. No intercepta HTTPS ni intenta descifrar TLS. La navegación observada describe el navegador, no demuestra quién estaba frente al dispositivo ni qué hizo dentro de una cuenta.
