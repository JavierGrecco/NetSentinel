# Extensión Chromium de NetSentinel: páginas y búsquedas

Esta extensión registra navegación futura en el dispositivo donde está instalada. Funciona con Chrome y navegadores Chromium compatibles, como Edge. Está apagada al instalarse y requiere activación explícita desde su panel.

## Instalación

1. Descargá y descomprimí el ZIP completo del repositorio en el equipo cuyo navegador querés observar.
2. Abrí chrome://extensions en Chrome o edge://extensions en Edge.
3. Activá el modo de desarrollador y elegí **Cargar descomprimida**.
4. Seleccioná la carpeta browser-extension del repositorio.
5. Abrí el ícono de NetSentinel. Revisá los permisos y activá **Activar seguimiento**.
6. Elegí si querés registrar páginas, búsquedas, exclusiones de dominio y retención de 1 a 90 días.

El permiso de host cubre sitios HTTP(S); el navegador lo solicita porque una extensión necesita permiso para consultar URLs de distintas webs. El seguimiento está apagado por defecto y queda visible en el popup.

## Qué registra

Registra eventos de navegación de nivel superior y cambios de URL que comunica la API de navegación del navegador. La extensión reconoce consultas en Google, Bing, DuckDuckGo, Yahoo, Ecosia, Brave Search, Yandex, Baidu, YouTube, Wikipedia, Amazon, Reddit y TikTok.

La URL de página se sanea antes de guardarse: se elimina el fragmento, los parámetros típicos de autenticación/sesión, identificadores de seguimiento y parámetros de consulta que se guardan por separado como search_terms. El backend vuelve a validar y sanear las URLs al importar el CSV.

No lee el historial previo, contenidos de páginas, campos de formularios, pulsaciones de teclado, contraseñas, cookies, tokens ni mensajes. No captura búsquedas internas de aplicaciones nativas ni formatos de búsqueda que la extensión no reconoce. La navegación privada no está habilitada de forma predeterminada; no actives ese permiso si no lo necesitás.

## Importar registros en NetSentinel

1. En el navegador supervisado, abrí la extensión y pulsá **Exportar CSV para NetSentinel**.
2. Abrí NetSentinel en la computadora que administra el inventario y visitá /activity.
3. Seleccioná el dispositivo correspondiente y, en **Importar registros CSV**, elegí netsentinel-browser-activity.csv.
4. Revisá los registros page_visit y search_query en la tabla de actividad.

La transferencia entre dispositivos es manual en esta versión. El CSV permanece bajo tu control; la extensión no sube datos a la nube ni se conecta automáticamente a otra computadora. La sincronización central en vivo requiere autenticación y transporte seguro, y sigue pendiente.

## Privacidad y límites

Las URLs y los términos de búsqueda pueden revelar información personal sensible. Usá la extensión solo en dispositivos que administrás con autorización, informá apropiadamente el seguimiento familiar, configurá dominios excluidos y conserva los datos solo el tiempo necesario. El almacenamiento permanece local hasta que exportás o borrás registros.

Los filtros eliminan parámetros comunes sensibles, pero ningún filtro genérico puede identificar todos los secretos que una web podría incluir en una ruta o en parámetros desconocidos. No intercepta HTTPS ni intenta descifrar TLS. La navegación observada describe el navegador, no demuestra quién estaba frente al dispositivo ni qué hizo dentro de una cuenta.
