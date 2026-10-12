# Seguridad y límites

## Alcance de la versión 0.10.0

NetSentinel es una herramienta de observación local. El panel escucha en `127.0.0.1` de forma predeterminada y la base SQLite permanece en la computadora del usuario. La lectura pasiva de tablas de vecinos solo muestra direcciones que el sistema ya conoce; el descubrimiento activo comienza únicamente cuando se solicita desde el panel.

En sistemas POSIX, el directorio predeterminado `~/.netsentinel` se mantiene privado (`0700`), los directorios que NetSentinel crea se restringen a permisos de usuario y el archivo SQLite se ajusta a `0600` cuando el sistema lo permite. Para rutas personalizadas de `NETSENTINEL_DATA_DIR`, no se cambian los permisos de directorios preexistentes: elegí una carpeta dedicada de la aplicación, no un directorio compartido como `/tmp`. En Windows, protegé la carpeta de datos con los permisos de tu cuenta.

Las consultas interactivas DNS A/AAAA y PTR ejecutan el resolvedor del sistema en un proceso hijo con límite de 3 segundos; si la resolución queda bloqueada, el proceso termina y la API devuelve un error temporal en lugar de retener indefinidamente el worker. El diagnóstico general ya usa el mismo enfoque aislado. El límite de tiempo no significa que todos los resolutores o registros DNS tengan idéntico comportamiento en cada sistema operativo.

El descubrimiento activo solo examina subredes IPv4 privadas RFC 1918: `10.0.0.0/8`, `172.16.0.0/12` y `192.168.0.0/16`. Analiza como máximo dos subredes y, si una es mayor que /24, reduce el alcance a un /24. Envía como máximo un ping por dirección y acepta una sola ejecución de descubrimiento simultánea. No explora Internet ni modifica la configuración de los equipos. Un equipo puede no responder al ping, por lo que los resultados no garantizan un inventario completo y no cubren redes exclusivamente IPv6.

Las interfaces Apple de enlace local como AWDL/LLW no se consideran dispositivos de una LAN convencional en nuevas lecturas. Los registros históricos se conservan automáticamente; las observaciones antiguas de AWDL/LLW se etiquetan como interfaces locales virtuales sin borrarlas. Una MAC puede aleatorizarse o suplantarse, y un dispositivo desconocido no demuestra una intrusión.

## Protección de la interfaz local

El servidor valida `Host` para bloquear nombres arbitrarios, acepta loopback y direcciones privadas de LAN, y permite hostnames propios solo si se declaran en `NETSENTINEL_ALLOWED_HOSTS` (lista separada por comas). Las operaciones de modificación rechazan peticiones con origen diferente o marcadas como `cross-site`. Las rutas GET que pueden iniciar consultas DNS/PTR también rechazan peticiones de otro origen usando Fetch Metadata y, cuando está presente, `Origin`; esto evita que una página externa dispare consultas al resolvedor local mediante una URL incrustada. La navegación directa y las consultas iniciadas desde la propia interfaz siguen permitidas. Todas las respuestas, incluso los rechazos, incluyen `Cache-Control: no-store`, `Pragma: no-cache` y cabeceras defensivas. La política CSP limita por defecto los recursos al mismo origen, bloquea objetos, frames y formularios externos, y fija `frame-ancestors 'none'`. En las cinco pantallas principales, cada bloque JavaScript inline queda autorizado mediante su hash SHA-256 exacto; `script-src` ya no usa `unsafe-inline`, y la política se calcula para que los hashes de una página no autoricen scripts de otra. La CI prueba que los hashes coinciden y evita que vuelvan a aparecer manejadores inline `onclick`/similares. Los cinco módulos principales cargan sus hojas CSS desde `/static/`; `style-src` no permite `unsafe-inline`, y las pruebas rechazan tanto elementos `<style>` como atributos `style` en las pantallas. `/api/docs` también prohíbe estilos inline y admite su CSS desde jsDelivr en una política separada. `/api/docs` genera una política CSP por respuesta y autoriza el inicializador JavaScript de Swagger UI con su hash SHA-256 exacto; la excepción CDN para JavaScript, CSS y favicon sigue limitada a esa ruta. `script-src` y `style-src` no necesitan `unsafe-inline` en ninguna pantalla. `Permissions-Policy` deshabilita cámara, micrófono, geolocalización, pagos y USB.

Estas medidas reducen riesgos de DNS rebinding y CSRF en navegadores, pero no constituyen autenticación para acceso desde otros equipos. No expongas el panel sin controles adicionales. Si accedés por un hostname propio, configurá explícitamente `NETSENTINEL_ALLOWED_HOSTS`.

## Operación segura

- El CLI oficial ahora rechaza cualquier `--host` que no sea loopback, incluidos `0.0.0.0`, direcciones de LAN y hostnames remotos. Esta barrera evita una exposición accidental al usar `netsentinel`; no equivale a autenticación ni protege despliegues alternativos iniciados directamente con otro servidor ASGI. No desplegar NetSentinel en otras interfaces hasta implementar y revisar autenticación, autorización, protección CSRF/origen y transporte HTTPS.
- Mantener el host en `127.0.0.1`. No exponer el servidor a otras interfaces sin autenticación, protección CSRF/origen, HTTPS y una revisión de seguridad específica.
- El descubrimiento, el diagnóstico y las comprobaciones de monitorización generan tráfico cuando se solicitan o se habilitan expresamente. El panel rechaza descubrimientos simultáneos para no duplicar el sondeo de la LAN.
- Los comandos se ejecutan con argumentos separados y no interpolan valores del inventario como comandos.
- Los fabricantes, si se habilitan, se consultan únicamente en un CSV OUI local; no se envían direcciones MAC a servicios externos.
- La base SQLite, el respaldo descargable y las exportaciones pueden revelar topología y hábitos de red. Protegé el equipo y revisá los archivos antes de compartirlos. El respaldo se crea con la API de copia de SQLite para mantener una imagen consistente.
- Usá NetSentinel únicamente en redes y sobre objetivos que administrás o tenés autorización para revisar.
- Los webhooks externos están deshabilitados por defecto. Si configurás uno, protegé su URL como un secreto y usá HTTPS.

## Seguimiento de actividad por dispositivo

La telemetría de actividad autorizada puede proceder del backend de metadatos o de la extensión Chromium explícita de `browser-extension/`. La extensión, apagada al instalarse, observa navegación futura en el navegador donde se instala; no lee contenido de páginas, formularios, pulsaciones, contraseñas, cookies o tokens. Las URLs HTTP(S) aceptadas por el modelo de visitas se normalizan: se eliminan fragmentos, parámetros conocidos de autenticación/sesión, búsqueda y seguimiento, y se rechazan credenciales embebidas y esquemas no HTTP(S). Los términos de búsqueda se guardan en un campo separado para motores que la extensión reconoce. Ningún filtro puede garantizar eliminar todos los datos personales que un sitio incruste en rutas o parámetros atípicos.

Las sesiones del backend son opt-in, se limitan a un dispositivo y un máximo de 12 horas, y la ingestión requiere un token aleatorio de sesión; en SQLite solo se conserva su hash. La retención es configurable entre 1 y 90 días. El backend no captura paquetes por sí mismo ni instala agentes. El token se muestra una sola vez y nunca se incluye en listados ni exportaciones. Los eventos importados desde la extensión se asocian manualmente al dispositivo que el operador elige; no se sincronizan automáticamente entre equipos.

En redes conmutadas o Wi-Fi, un equipo ordinario no suele ver todo el tráfico unicast de otros clientes; puede requerirse telemetría del router/AP o un puerto espejo administrado y autorizado. DNS/SNI/conexiones son indicios de actividad, no prueba de identidad ni de páginas vistas. No se debe intentar interceptar/deshacer TLS para obtener credenciales. La API está prevista para uso local: no expongas el panel en la LAN o Internet sin autenticación, TLS y revisión de seguridad adicionales.

## Auditoría TLS puntual

La inspección TLS de Herramientas se inicia explícitamente con un host/IP y puerto introducidos por el operador. Realiza una única conexión TLS con la validación normal de certificados del sistema; muestra solo metadatos del certificado y del handshake. No envía solicitudes HTTP, no descarga páginas, no captura credenciales, no intercepta tráfico y no persiste los resultados. Un error de conexión no demuestra por sí solo que un servicio esté comprometido o mal configurado. Ejecutá pruebas solo contra endpoints propios o autorizados; los hallazgos son orientación técnica, no una certificación de cumplimiento.

## Funciones que exigen revisión específica

Las consultas SNMP, las integraciones con routers, los cambios de DNS, el bloqueo de dispositivos y la interceptación de proxy requieren una revisión de autorización, alcance, límites de tasa, auditoría, almacenamiento de secretos, reversión de cambios y tratamiento de datos sensibles antes de implementarse.

## Controles automatizados del repositorio

El workflow `.github/workflows/security.yml` ejecuta dos controles:
- **CodeQL** analiza estáticamente el código Python con consultas de seguridad ampliadas y publica resultados en GitHub Code Scanning.
- **pip-audit** comprueba las dependencias de ejecución frente a avisos de vulnerabilidades conocidos; el job falla cuando detecta vulnerabilidades notificadas.

El workflow se ejecuta en cambios a `main`, solicitudes de cambio y semanalmente. Sus permisos están limitados por job y las acciones externas se fijan a SHA completos para evitar depender de una etiqueta mutable. `.github/dependabot.yml` propone actualizaciones semanales para dependencias Python y GitHub Actions.

Estos controles reducen riesgos conocidos, pero no demuestran que el software sea seguro ni reemplazan revisión manual, pruebas, gestión de versiones ni respuesta a vulnerabilidades. El análisis de dependencias depende de los avisos públicos disponibles en el momento de la ejecución.

## Cadena de suministro y detección de secretos

El workflow `.github/workflows/supply-chain.yml` ejecuta Gitleaks contra el historial completo del repositorio en pull requests, cambios en `main`, etiquetas `v*` y una revisión semanal. Los comentarios automáticos y la carga de artefactos que pudieran contener fragmentos de secretos están desactivados. Si se detecta una credencial real, revocala o rotala inmediatamente; quitarla de la versión actual no invalida una credencial que ya se publicó en el historial. No copies valores secretos en issues públicos.

El mismo workflow construye el wheel y genera un SBOM CycloneDX 1.6 desde un entorno aislado que instala ese wheel y sus dependencias de ejecución resueltas. Comprueba que el SBOM contiene el producto y las dependencias principales, genera `SHA256SUMS` y verifica el manifiesto antes de publicar un artefacto de CI. El SBOM describe las versiones resueltas durante esa compilación; no sustituye un archivo de bloqueo ni garantiza que una dependencia sea segura.

Para etiquetas de versión que comienzan con `v`, GitHub Actions verifica los checksums y crea atestaciones firmadas con Sigstore para la procedencia de compilación y la relación entre wheel y SBOM. Una vez publicada una versión, se puede comprobar la atestación con GitHub CLI:

```bash
gh attestation verify netsentinel-<version>-py3-none-any.whl --repo JavierGrecco/NetSentinel
gh attestation verify netsentinel-sbom.cdx.json --repo JavierGrecco/NetSentinel
```

Los checksums detectan cambios accidentales cuando se comparan con el manifiesto de origen; no autentican el origen por sí solos. Para autenticidad y procedencia se debe verificar la atestación. La generación y atestación de versiones etiquetadas depende de que el flujo se ejecute con permisos de GitHub Actions compatibles y de que se publique la etiqueta de versión esperada.

## Reporte de vulnerabilidades

No publiques detalles explotables, credenciales, tokens, exportaciones ni datos de usuarios en issues, discusiones o pull requests públicos. Si GitHub ofrece **Security → Report a vulnerability** para este repositorio, utiliza ese canal privado. Si no aparece la opción, contacta al mantenedor mediante el canal público indicado en su [perfil de GitHub](https://github.com/JavierGrecco) y solicita un canal privado; no incluyas detalles explotables en el primer contacto. No se promete un SLA de respuesta. La política de entrada para reportes está en la [política de seguridad raíz](../SECURITY.md).


### Importación de correo
La funcionalidad de correo es exclusivamente una importación explícita de metadatos desde una exportación de auditoría autorizada. Guarda fecha/proveedor/emisor/destinatarios/asunto opcional, nunca cuerpos ni adjuntos. La aplicación no se autentica en buzones, no extrae mensajes desde webmail y rechaza columnas de contenido. Los CSV importados deben tratarse como datos sensibles y mantenerse solo el tiempo necesario.
