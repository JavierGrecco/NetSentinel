# Seguimiento familiar: páginas, búsquedas y metadatos de correo

## Implementado en esta rama

- `/activity`: sesiones de metadatos temporales, resumen de dominios, importación CSV y retención de 1 a 90 días.
- `browser-extension/`: extensión Chromium visible, apagada por defecto, que registra navegación futura y búsquedas compatibles en el dispositivo donde se instala.
- Importación manual desde CSV de metadatos de correo de registros de auditoría autorizados: proveedor, emisor, destinatarios, fecha y asunto opcional.
- Validación estricta del CSV y rechazo de campos de cuerpo de mensaje, contenido y adjuntos.
- Importación idempotente: se omiten y contabilizan filas normalizadas idénticas ya importadas para el mismo dispositivo, incluso si se repite el archivo completo.

## Páginas y búsquedas del navegador

Instalá la [extensión Chromium](../browser-extension/README.md) en cada dispositivo/navegador a supervisar y activala desde su panel. Registra navegación de nivel superior y URLs de motores conocidos como Google, Bing, DuckDuckGo, Yahoo, Ecosia, Brave Search, Yandex, Baidu, YouTube, Wikipedia, Amazon, Reddit y TikTok. Está apagada por defecto, conserva hasta 1.000 eventos localmente y permite exportar CSV para importarlo manualmente en `/activity`.

No lee el historial previo, contenido de páginas, formularios, pulsaciones, contraseñas ni cookies. No puede reconocer necesariamente búsquedas que ocurren dentro de aplicaciones nativas o en motores desconocidos. Antes de guardar una URL se eliminan fragmentos y parámetros conocidos de sesión, autenticación, búsqueda y seguimiento. Ningún saneador genérico puede reconocer todos los datos personales que un sitio podría incluir en rutas o parámetros atípicos.

## Correo electrónico: solo metadatos de auditoría

NetSentinel **no abre bandejas de entrada, no inicia sesión en cuentas de correo y no intercepta sesiones HTTPS**. En una conexión webmail normal, el tráfico cifrado no permite que el monitor de red vea emisor, destinatarios, asunto ni contenido. DNS o una conexión al dominio de un proveedor solo indican contacto con el servicio, no que se haya leído o enviado un correo.

Sí se pueden importar metadatos de una exportación explícita de auditoría/seguimiento que el operador esté autorizado a consultar. El formato normalizado es:

```csv
observed_at,event_type,email_provider,email_from,email_to,email_subject
2026-10-11T18:30:00Z,email_metadata,Gmail,parent@example.com,child@example.com,"Pedido de ayuda"
```

El emisor y al menos un destinatario son obligatorios; se aceptan hasta diez destinatarios. El asunto es opcional y se limita a 200 caracteres. La importación se etiqueta como `manual_import`. Las columnas `message`, `email_body`, `body_text`, `body_html`, `content`, `attachments` y equivalentes se rechazan.

El importador normaliza algunas cabeceras habituales de Google Workspace Email Log Search (Date, Sender, Recipient, Subject or Message ID) y Microsoft 365 Message Trace (receivedDateTime, senderAddress, recipientAddress, subject). El campo de Google "Subject or Message ID" puede contener un identificador en vez del asunto real. Esto solo normaliza CSV exportados manualmente: no es un conector API ni inicia sesión en cuentas, y la cobertura depende de la edición y permisos del proveedor. No se guardan cuerpos de mensajes ni archivos adjuntos; para una preocupación concreta sobre contenido, es preferible utilizar las herramientas oficiales de seguridad y controles parentales de la cuenta de forma transparente, no extraer comunicaciones desde el navegador.

## Flujo de uso actual

1. Activá la extensión en el navegador supervisado, si querés registro de navegación.
2. Exportá el CSV desde la extensión.
3. En NetSentinel, abrí `/activity`, elegí el dispositivo e importá el archivo. La interfaz informa cuántos eventos agregó y cuántas filas duplicadas omitió; volver a cargar el mismo CSV no duplica los eventos idénticos.
4. Para correo, prepará/importá el CSV a partir de un registro de auditoría autorizado. Asociá el registro con el dispositivo correspondiente solo si la fuente realmente lo permite; no inferir identidad por el mero destinatario.

La transferencia de los datos de la extensión a NetSentinel es manual. No hay sincronización central en vivo ni un conector de correo automático. Las sesiones de red del backend tampoco capturan tráfico por sí solas: necesitan una fuente compatible; aún no hay adaptador de router/AP ni agente de uso de aplicaciones.

## Retención y alcance

NetSentinel usa siete días por defecto y permite retención de 1 a 90 días. La extensión también tiene retención local de 1 a 90 días y un máximo de 1.000 eventos. Los CSV y respaldos SQLite pueden revelar hábitos, intereses y relaciones; protegé los archivos y borrá los datos cuando ya no hagan falta.

Una visita o una fila de auditoría describe el evento reportado por su fuente, pero no prueba por sí sola quién estaba frente a la pantalla ni qué hizo dentro de una cuenta.
