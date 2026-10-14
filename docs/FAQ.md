# Preguntas frecuentes

Esta guía responde dudas comunes con palabras simples. Para detalles técnicos, seguí los enlaces del [README](../README.md).

## No aparece ningún dispositivo. ¿Está desconectado?

No necesariamente. Primero, comprobá que esta computadora esté conectada a la red que querés revisar y volvé a pulsar **Descubrir dispositivos**. NetSentinel consulta un máximo de dos subredes IPv4 privadas y hace una prueba de ping por dirección. Algunos equipos no responden a esa prueba, las redes de invitados pueden aislar dispositivos y una red que usa solo IPv6 puede quedar fuera del descubrimiento actual. Un resultado vacío no demuestra que no haya otros equipos.

## ¿Qué significa «Pendiente» o «De confianza»?

Es una clasificación que vos asignás para organizar el inventario. **Pendiente no significa que el dispositivo sea malicioso** y «De confianza» no significa que NetSentinel haya certificado que es seguro. Si no reconocés un equipo, revisá su nombre, fabricante, dirección y el contexto de la red antes de sacar conclusiones.

## ¿Dónde se guardan los datos?

Por defecto, NetSentinel guarda sus registros en una base SQLite de esta computadora, dentro de la carpeta `~/.netsentinel/` (en Windows, en tu carpeta de usuario). Si configuraste `NETSENTINEL_DATA_DIR`, usa esa ubicación. No se necesita una cuenta ni un servidor externo para el uso local. Las copias de seguridad contienen datos de tu red: guardalas en un lugar protegido y no las adjuntes a un issue público.

## ¿NetSentinel ve todo lo que hacen los demás dispositivos?

No. El inventario muestra datos que esta computadora puede observar en la red y los resultados de las comprobaciones solicitadas. No captura automáticamente todo el tráfico ni descubre toda la navegación de otros equipos.

La extensión Chromium es opcional y queda apagada al instalarse. Si la activás, registra navegación futura compatible en ese navegador, en ese equipo. La transferencia a NetSentinel se realiza de forma manual mediante CSV. No lee contraseñas, cookies, formularios ni contenido de páginas. El saneamiento de URLs es preventivo, pero no puede identificar todos los datos personales que un sitio incluya en rutas o parámetros desconocidos; por eso, usá únicamente información autorizada y revisá los archivos antes de importarlos o compartirlos.

## ¿Puede leer mis correos?

No se conecta a tu bandeja de entrada. Permite importar manualmente metadatos de auditoría autorizados, como fecha, emisor, destinatarios y asunto opcional. No almacena cuerpos de mensajes ni adjuntos y rechaza columnas de contenido. No hay todavía un conector automático para proveedores de correo.

## ¿Un fallo de ping o un hallazgo significa que me atacaron?

No. Un ping fallido puede deberse a filtros, una red aislada, una ruta caída o un equipo apagado. Los hallazgos muestran observaciones e incidentes que conviene revisar; no confirman por sí solos una intrusión. DNS tampoco demuestra la identidad real de un dispositivo, y la inspección TLS puntual no reemplaza una auditoría completa.

## ¿Por qué no recibo avisos externos?

NetSentinel funciona sin notificaciones externas. Para enviar avisos necesitás configurar explícitamente `NETSENTINEL_WEBHOOK_URL` con un endpoint HTTPS compatible antes de iniciar la aplicación. Esa dirección puede contener credenciales: no la compartas ni la subas al repositorio.

## ¿Qué hago si el panel no abre?

1. Comprobá que la ventana o terminal donde iniciaste NetSentinel siga abierta.
2. Abrí `http://127.0.0.1:8765` en el navegador de esa misma computadora.
3. Si el programa muestra un error de arranque, guardá el mensaje y consultá la [guía de desarrollo y diagnóstico](DEVELOPMENT.md). No publiques datos sensibles de la salida.

El panel está limitado a esta computadora. No está preparado para que otras computadoras accedan a él por la red local.

## ¿Cómo reporto un problema?

Abrí un issue en GitHub con el sistema operativo, la versión de NetSentinel, los pasos para repetir el problema y el mensaje de error sin datos privados. No adjuntes bases de datos, inventarios reales, direcciones de clientes, tokens, contraseñas, cookies, correos ni URLs privadas. Si creés haber encontrado una vulnerabilidad de seguridad, seguí la [política de reporte](../SECURITY.md) y no publiques detalles explotables en un issue público.

## ¿Dónde están las instrucciones técnicas?

- [Instalación y uso](../README.md)
- [Guía de monitorización](MONITORING.md)
- [Actividad y telemetría autorizada](FAMILY_ACTIVITY.md)
- [Guía de la extensión Chromium](../browser-extension/README.md)
- [Arquitectura](ARCHITECTURE.md)
- [Roadmap de implementación](ROADMAP.md)

## ¿Cómo informo un error de NetSentinel?

Cuando una solicitud falla, el panel muestra un código estable y, si el servidor recibió la solicitud, una referencia de seguimiento. Copiá ambos datos al informar el problema. Los fallos internos y de herramientas locales que requieren investigación intentan guardarse en `netsentinel-errors.jsonl`, dentro de la carpeta de datos de NetSentinel (`~/.netsentinel/` por defecto o la indicada por `NETSENTINEL_DATA_DIR`). El archivo se rota y está limitado en tamaño. Si una falla inesperada impide escribirlo, el panel lo indica y la aplicación también emite un resumen seguro a su salida de registro.

El registro solo contiene campos técnicos permitidos, como código, categoría, ruta de API sin parámetros de consulta, tipo de excepción y ubicación del código. No conserva cuerpos de solicitud, tokens ni el texto original de las excepciones. Validaciones normales, rechazos de seguridad y pings sin respuesta no se guardan como fallos internos. Si el panel dice que no pudo escribir el registro, revisá el espacio disponible y los permisos de la carpeta de datos.

