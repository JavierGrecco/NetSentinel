# NetSentinel

**Una herramienta local para conocer tu red, registrar cambios y comprobar si tus servicios responden.**

NetSentinel reúne inventario de dispositivos, historial y monitorización en un panel web. Se ejecuta en tu computadora; no necesita una cuenta ni un servidor externo.

El módulo **NetSentinel Forense** está en desarrollo como área separada. Esta primera entrega incorpora el registro de casos y una comparación de SHA-256 limitada a copias de trabajo locales designadas. Sigue en validación: no autentica la identidad del operador ni constituye, por sí sola, una cadena de custodia validada. El plan detalla los límites y los siguientes pasos.

## Primeros pasos

1. **Iniciá NetSentinel.** En Windows, ejecutá `run-windows.bat`; en macOS, abrí `run-macos.command`; en Linux, ejecutá `./run.sh`. La [sección de instalación](#instalación-y-primer-inicio) explica cada opción.
2. **Abrí el panel.** Entrá en [http://127.0.0.1:8765](http://127.0.0.1:8765). En el primer inicio necesitás conexión a Internet para instalar las dependencias que falten.
3. **Conocé tu red.** Pulsá **Descubrir dispositivos**, revisá los resultados y marcá como conocidos los equipos que reconocés. Después podés crear un control en **Monitorización** para comprobar un servicio.

La búsqueda solo se ejecuta cuando la pedís y tiene límites para reducir el tráfico. Usá NetSentinel únicamente en redes que administrás o tenés autorización para revisar. Un equipo que no aparece no está necesariamente desconectado.

## Índice

- [Qué podés hacer](#qué-podés-hacer)
- [Instalación y primer inicio](#instalación-y-primer-inicio)
- [Descubrimiento de la red](#descubrimiento-de-la-red)
- [Herramientas DNS](#herramientas-dns) y [inspección TLS](#inspección-tls)
- [Hallazgos con evidencia](#hallazgos-con-evidencia)
- [Monitorización](#monitorización)
- [Copias de seguridad y datos](#copias-de-seguridad-y-datos)
- [Actividad y privacidad](#historial-y-telemetría-autorizada)
- [Preguntas frecuentes](docs/FAQ.md)
- [Seguimiento del proyecto](docs/PROJECT_STATUS.md) y [roadmap](docs/ROADMAP.md)
- [NetSentinel Forense: alcance y etapas](docs/FORENSIC_MODE.md)
- [Prueba manual de NetSentinel Forense](docs/FORENSIC_MANUAL_TEST.md)
- [Escenarios sintéticos guiados](docs/MANUAL_TEST_SCENARIOS.md)
- [Mapa mundial de IP](docs/WORLD_IP_MAP.md)
- [Pruebas](#pruebas) y [documentación para mantenimiento](#documentación)

## Qué podés hacer

- Detectar automáticamente subredes IPv4 privadas RFC 1918 activas (10/8, 172.16/12 y 192.168/16) y buscar dispositivos en ellas, sin que tengas que conocer el rango de IPs.
- Consultar dispositivos con sus direcciones IP y MAC, buscar por cualquiera de sus direcciones IPv4/IPv6 y revisar la procedencia de cada observación.
- Marcar dispositivos de confianza y agregarles un nombre o una nota.
- Guardar un historial de lecturas y cambios observados.
- Consultar el mapa mundial de IP públicas observadas en eventos guardados mediante la vista `/world-map`. Las coordenadas son aproximadas y requieren una base GeoLite2-City local válida; no se inventan ubicaciones cuando falta esa base.
- Revisar **actividad y telemetría autorizada** en `/activity`: sesiones temporales por dispositivo, eventos de metadatos, importación de CSV y retención configurable. No captura tráfico automáticamente ni registra contraseñas.
- Supervisar un host con ping, un puerto TCP o una URL HTTP/HTTPS.
- Ejecutar un diagnóstico guiado que explica los resultados de red y sugiere qué revisar.
- Consultar y filtrar incidentes abiertos/resueltos, exportar su historial y las duraciones estimadas a CSV, y revisar tendencias de latencia por hora (24 h) o por bloques de seis horas (7 días), también exportables.
- Exportar el inventario a CSV compatible con Excel, el historial a JSON y una copia SQLite consistente que puede guardarse como respaldo.
- Enviar avisos externos opcionales mediante un webhook HTTPS.
- Consultar registros DNS A/AAAA por nombre y resolución inversa PTR por IP bajo demanda, usando el resolvedor del sistema. Cada consulta A/AAAA o PTR tiene un límite estricto de 3 segundos: el resolvedor se ejecuta en un proceso hijo que se puede terminar si el resolvedor del sistema se queda bloqueado. La pantalla `/tools` también muestra una lectura orientativa de la configuración DNS local sin modificarla. Los resultados DNS no verifican la identidad de un dispositivo; el comportamiento puede variar con VPN, split DNS e interfaces activas. Las respuestas PTR exitosas usan una caché en memoria acotada por tamaño y duración.
- Inspeccionar bajo demanda un endpoint TLS autorizado: validez de certificado, vencimiento, versión TLS y cifrado negociado, sin descargar contenido web.

> **Importante:** la búsqueda local se inicia cuando la solicitás. Detecta automáticamente hasta dos subredes IPv4 privadas y puede consultar hasta 254 direcciones por subred, mediante una sola prueba de ping por dirección. Esto genera tráfico en la red local, no modifica equipos y no garantiza encontrar todos los dispositivos: algunos no responden al ping, pueden filtrar ICMP o usar solo IPv6. Usalo únicamente en redes que administrás o tenés autorización para revisar. El diagnóstico también es orientativo: un ping fallido no demuestra por sí solo que Internet esté caído.


## Requisitos

- Python 3.10 o posterior.
- Windows, macOS o Linux.

## Instalación y primer inicio

Descargá el ZIP desde **Code → Download ZIP** y descomprimilo.

### Inicio con un clic

- **Windows:** ejecutá `run-windows.bat`.
- **macOS:** abrí `run-macos.command`. Si macOS muestra una advertencia, usá clic derecho → **Abrir**.
- **Linux o terminal de macOS:** ejecutá `./run.sh`.

El primer inicio crea un entorno virtual local `.venv` e instala las dependencias del proyecto; necesitás conexión a Internet para descargar las dependencias si todavía no están disponibles. En los siguientes inicios, el lanzador comprueba el estado local y solo reinstala si cambió `pyproject.toml` o faltan dependencias; por eso no necesita consultar Internet en cada apertura. La aplicación se inicia en `http://127.0.0.1:8765`. La base de datos y la configuración no se borran al volver a abrir el programa. El lanzador de línea de comandos solo admite direcciones loopback: rechaza `--host 0.0.0.0`, IP de la LAN y nombres de host remotos porque todavía no hay autenticación ni control de acceso para otros equipos. También se rechazan puertos fuera del rango TCP válido. Por seguridad, la interfaz rechaza nombres de host no autorizados y solicitudes de modificación iniciadas desde otro sitio web.

### Instalación manual (alternativa)

Abrí una terminal dentro de la carpeta del proyecto.

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
netsentinel
```

Si PowerShell no permite activar el entorno, después de instalar podés ejecutar `.venv\Scripts\python.exe -m netsentinel.cli`.

### macOS o Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
netsentinel
```

Se abrirá el panel en **http://127.0.0.1:8765**. Si no se abre automáticamente, copiá esa dirección en el navegador.

## Descubrimiento de la red

En el panel, pulsá **Descubrir dispositivos** y confirmá la operación. NetSentinel detecta automáticamente las subredes IPv4 privadas RFC 1918 (10/8, 172.16/12 y 192.168/16) de interfaces activas compatibles; no necesitás escribir una dirección IP ni calcular una máscara de red. Para limitar el tráfico, busca como máximo dos subredes y hasta 254 direcciones por cada una. Después consulta la tabla local de vecinos de macOS, Windows o Linux y guarda las entradas que coinciden con las redes detectadas. El historial conserva también el rango, la cantidad de direcciones consultadas, las respuestas a ping y la duración total, para comparar lecturas después de que desaparezca el aviso temporal.

Algunos equipos no responderán al ping, las redes aisladas de invitados pueden ocultar dispositivos y el escaneo IPv4 no cubre redes exclusivamente IPv6. Por eso, un resultado vacío o incompleto no prueba que no haya otros equipos conectados. NetSentinel no bloquea dispositivos ni cambia la configuración del router.

## Herramientas DNS

Las consultas DNS A/AAAA por nombre y PTR inverso por IP están disponibles en `/tools` y en las acciones del inventario. Se ejecutan solo cuando las solicitás y no cambian la configuración de red. Cada consulta de nombre o PTR tiene un límite estricto de 3 segundos en un proceso hijo terminable, para que un resolvedor del sistema bloqueado no retenga indefinidamente una solicitud del panel. La consulta A/AAAA acepta nombres de host, no URLs ni direcciones IP literales. La API ofrece `GET /api/tools/dns/lookup?hostname=example.com` y `GET /api/devices/{device_id}/dns-reverse`. Los resultados indican resolución, no identidad verificada; la detección de DNS local puede ser parcial según el sistema operativo, las VPN y el split DNS.

## Inspección TLS

En **Herramientas** podés comprobar un único host/IP y puerto TLS. La herramienta valida el certificado con el almacén de confianza del sistema e informa fechas de validez, nombre del certificado, versión TLS y cifrado negociado. Solo realiza el handshake TLS; no solicita páginas, no lee contenido HTTP y no guarda el resultado. Usala únicamente sobre endpoints que administrás o tenés autorización para evaluar. No reemplaza una auditoría completa de TLS.

## Hallazgos con evidencia

Abrí **Hallazgos** en el panel o visitá `/findings` para revisar la bandeja visual del inventario y la disponibilidad. Podés filtrar pendientes, revisados, incidentes recuperados o todos los estados; expandir la evidencia y procedencia; marcar eventos de inventario como revisados; y exportar la consulta a JSON. Las cifras indican los registros devueltos (máximo 200), no un total histórico.

La API local `GET /api/findings` normaliza los cambios observados del inventario y los incidentes de monitorización, con procedencia, evidencia, estado, severidad y confianza separadas. Admite `state=active|acknowledged|resolved|all` y un `limit` de hasta 200. `GET /api/export/findings.json` exporta la misma vista en JSON sin modificar los datos. Esta primera iteración no correlaciona causas raíz ni incluye resultados puntuales DNS/TLS, porque esas inspecciones no se persisten. No es un SIEM ni confirma por sí sola una intrusión.

## Monitorización

En el panel, elegí **Monitorización** y agregá un control:

- **Ping:** comprueba si responde un host.
- **TCP:** comprueba si se puede conectar a un puerto, por ejemplo `192.168.1.1:443`.
- **HTTP/HTTPS:** consulta una URL de estado, por ejemplo `https://example.com/health`.

Los intervalos permitidos van de 15 segundos a 24 horas. Al detectar una caída se abre un incidente; los fallos siguientes actualizan ese mismo incidente y el primer resultado correcto lo cierra.

El historial detallado de comprobaciones se conserva 90 días por defecto. Podés ajustar la política con `NETSENTINEL_MONITOR_HISTORY_DAYS` (1–3650 días) o usar `0` para desactivar la limpieza y conservarlo indefinidamente. La limpieza elimina solo muestras antiguas de comprobación, no incidentes, estados actuales ni el inventario. Consultá la [guía de monitorización](docs/MONITORING.md) para ejemplos y límites.

### Avisos opcionales

NetSentinel funciona sin notificaciones externas. Para enviar avisos de caída y recuperación, configurá la variable `NETSENTINEL_WEBHOOK_URL` con la URL HTTPS de tu webhook antes de iniciar el programa. Tratá esa URL como una contraseña y no la subas al repositorio.

La [guía de monitorización](docs/MONITORING.md) explica los límites y la configuración.

## Copias de seguridad y datos

Desde el pie del inventario podés descargar una copia completa SQLite con el historial de dispositivos, eventos, lecturas y monitorización. A diferencia de la exportación JSON, esa copia es una base SQLite utilizable para recuperación. Para restaurarla, cerrá NetSentinel, guardá aparte la base actual y reemplazá `netsentinel.sqlite3` por el archivo descargado renombrado con ese nombre. La ruta predeterminada es `~/.netsentinel/netsentinel.sqlite3` (en Windows, dentro de tu carpeta de usuario); si configuraste `NETSENTINEL_DATA_DIR`, usá ese directorio en su lugar. Volvé a iniciar NetSentinel después de reemplazar el archivo. Los respaldos incluyen metadatos de tu red; almacenalos en un lugar seguro.

## Historial y telemetría autorizada

Desde el inventario, **Historial** muestra cuándo se observó un dispositivo y qué IP tenía. La pantalla **Actividad y telemetría** (`/activity`) permite consultar registros de red, navegación y metadatos de correo importados.

Para registrar **páginas y búsquedas del navegador**, instalá la extensión Chromium de [`browser-extension/`](browser-extension/README.md) en cada dispositivo/navegador a supervisar y activala expresamente. Guarda localmente visitas y búsquedas compatibles, exporta un CSV y permite importarlo en `/activity` asociándolo al dispositivo correcto. Está apagada por defecto, solo registra navegación futura y no lee formularios ni contraseñas. La transferencia es manual por CSV; la sincronización automática entre equipos sigue pendiente.

Para **correo electrónico**, NetSentinel acepta una importación manual de metadatos de registros de auditoría autorizados: fecha, proveedor, emisor, destinatarios y asunto opcional. No se conecta a bandejas, no captura mensajes ni adjuntos y rechaza columnas de cuerpo/contenido. No hay todavía un adaptador específico para Google Workspace, Microsoft 365 ni cuentas personales; eso depende de las capacidades y permisos del proveedor.

El backend por sí solo no ve todas las conexiones de otros equipos ni conoce las páginas que se abren. La extensión no registra búsquedas internas de aplicaciones nativas ni formatos que no aparecen en una URL compatible. No recolectamos contraseñas, cookies ni contenido de páginas, y no intentamos interceptar TLS. Consultá la [guía de actividad y telemetría autorizada](docs/FAMILY_ACTIVITY.md) y la [guía de la extensión](browser-extension/README.md).

## Datos y privacidad

Los datos se guardan localmente en SQLite. Las notificaciones externas solo se intentan si configurás un webhook. No publiques inventarios, direcciones reales, credenciales ni tokens en incidencias.

Leé la [política de seguridad](SECURITY.md) y la [guía técnica de seguridad](docs/SECURITY.md) antes de habilitar integraciones o supervisar sistemas compartidos. No reportes vulnerabilidades mediante issues públicos.

## Laboratorio integrado de validación

Esta rama de laboratorio reúne en una sola instalación el mapa mundial de IP, el espacio NetSentinel Forense y los datos de prueba sintéticos.

- **Mapa mundial:** abrí `/world-map`. La página siempre está disponible, pero los marcadores reales necesitan una base GeoLite2-City autorizada instalada localmente.
- **Datos sintéticos:** seguí [los escenarios guiados](docs/MANUAL_TEST_SCENARIOS.md). El generador escribe archivos de ejemplo; el auxiliar de base prepara una base de prueba separada. La importación CSV se confirma desde Actividad, no automáticamente.
- **Forense:** abrí `/forensics` y seguí [la prueba manual de Forense](docs/FORENSIC_MANUAL_TEST.md). El módulo sigue siendo experimental; los hashes y manifiestos no prueban por sí solos la identidad del operador ni reemplazan una cadena de custodia validada.

Los datos sintéticos se identifican como tales y no deben confundirse con observaciones reales.

## Pruebas

Para ejecutar las pruebas automatizadas:

```bash
python -m pip install -e ".[test]"
python -m pytest
```

## Documentación

- [Preguntas frecuentes y solución de problemas](docs/FAQ.md)
- [Arquitectura](docs/ARCHITECTURE.md)
- [Guía de actividad y telemetría autorizada](docs/FAMILY_ACTIVITY.md)
- [Instalación de la extensión para páginas y búsquedas](browser-extension/README.md)
- [Plan de versiones](docs/ROADMAP.md)
- [Detalles de monitorización](docs/MONITORING.md)
- [Guía para desarrolladores](docs/DEVELOPMENT.md) — solo si querés modificar el código.
- [Prueba responsive de la interfaz](docs/RESPONSIVE_UI_TESTING.md) — revisar tamaños de ventana y guardar capturas.
- [Plan de implementación](docs/IMPLEMENTATION_PLAN.md)
- [Dirección del producto y criterios de calidad empresarial](docs/PRODUCT_DIRECTION.md)
- [Base local de fabricantes OUI](docs/OUI_DATABASE.md)
- [Mantenimiento del repositorio](docs/GITHUB_SETUP.md)
- [Historial de cambios](CHANGELOG.md)

## Licencia

MIT. Las condiciones de las bases OUI y de cualquier herramienta externa opcional se revisan por separado.
