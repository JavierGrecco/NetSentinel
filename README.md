# NetSentinel

**Una herramienta local para conocer tu red, registrar cambios y comprobar si tus servicios responden.**

NetSentinel reúne inventario de dispositivos, historial y monitorización en un panel web. Se ejecuta en tu computadora; no necesita una cuenta ni un servidor externo.

## Qué podés hacer

- Detectar automáticamente subredes IPv4 privadas RFC 1918 activas (10/8, 172.16/12 y 192.168/16) y buscar dispositivos en ellas, sin que tengas que conocer el rango de IPs.
- Consultar dispositivos con sus direcciones IP y MAC, buscar por cualquiera de sus direcciones IPv4/IPv6 y revisar la procedencia de cada observación.
- Marcar dispositivos de confianza y agregarles un nombre o una nota.
- Guardar un historial de lecturas y cambios observados.
- Supervisar un host con ping, un puerto TCP o una URL HTTP/HTTPS.
- Ejecutar un diagnóstico guiado que explica los resultados de red y sugiere qué revisar.
- Consultar incidentes y ver cuándo se recupera un servicio.
- Exportar el inventario y los datos a CSV o JSON.
- Enviar avisos externos opcionales mediante un webhook HTTPS.

> **Importante:** la búsqueda local se inicia cuando la solicitás. Detecta automáticamente hasta dos subredes IPv4 privadas y puede consultar hasta 254 direcciones por subred, mediante una sola prueba de ping por dirección. Esto genera tráfico en la red local, no modifica equipos y no garantiza encontrar todos los dispositivos: algunos no responden al ping, pueden filtrar ICMP o usar solo IPv6. Usalo únicamente en redes que administrás o tenés autorización para revisar. El diagnóstico también es orientativo: un ping fallido no demuestra por sí solo que Internet esté caído.

## Requisitos

- Python 3.10 o posterior.
- Windows, macOS o Linux.

## Instalación y primer inicio

Descargá el ZIP desde **Code → Download ZIP** y descomprimilo. Abrí una terminal dentro de la carpeta del proyecto.

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

En el panel, pulsá **Descubrir dispositivos** y confirmá la operación. NetSentinel detecta automáticamente las subredes IPv4 privadas RFC 1918 (10/8, 172.16/12 y 192.168/16) de interfaces activas compatibles; no necesitás escribir una dirección IP ni calcular una máscara de red. Para limitar el tráfico, busca como máximo dos subredes y hasta 254 direcciones por cada una. Después consulta la tabla local de vecinos de macOS, Windows o Linux y guarda las entradas que coinciden con las redes detectadas. El historial conserva también el rango, la cantidad de direcciones consultadas y las respuestas a ping, para comparar lecturas después de que desaparezca el aviso temporal.

Algunos equipos no responderán al ping, las redes aisladas de invitados pueden ocultar dispositivos y el escaneo IPv4 no cubre redes exclusivamente IPv6. Por eso, un resultado vacío o incompleto no prueba que no haya otros equipos conectados. NetSentinel no bloquea dispositivos ni cambia la configuración del router.

## Monitorización

En el panel, elegí **Monitorización** y agregá un control:

- **Ping:** comprueba si responde un host.
- **TCP:** comprueba si se puede conectar a un puerto, por ejemplo `192.168.1.1:443`.
- **HTTP/HTTPS:** consulta una URL de estado, por ejemplo `https://example.com/health`.

Los intervalos permitidos van de 15 segundos a 24 horas. Al detectar una caída se abre un incidente; los fallos siguientes actualizan ese mismo incidente y el primer resultado correcto lo cierra.

### Avisos opcionales

NetSentinel funciona sin notificaciones externas. Para enviar avisos de caída y recuperación, configurá la variable `NETSENTINEL_WEBHOOK_URL` con la URL HTTPS de tu webhook antes de iniciar el programa. Tratá esa URL como una contraseña y no la subas al repositorio.

La [guía de monitorización](docs/MONITORING.md) explica los límites y la configuración.

## Datos y privacidad

Los datos se guardan localmente en SQLite. Las notificaciones externas solo se intentan si configurás un webhook. No publiques inventarios, direcciones reales, credenciales ni tokens en incidencias.

Leé la [política de seguridad](docs/SECURITY.md) antes de habilitar integraciones o supervisar sistemas compartidos.

## Pruebas

Para ejecutar las pruebas automatizadas:

```bash
python -m pip install -e ".[test]"
python -m pytest
```

## Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Plan de versiones](docs/ROADMAP.md)
- [Detalles de monitorización](docs/MONITORING.md)
- [Guía para desarrolladores](docs/DEVELOPMENT.md) — solo si querés modificar el código.
- [Plan de implementación](docs/IMPLEMENTATION_PLAN.md)
- [Base local de fabricantes OUI](docs/OUI_DATABASE.md)
- [Mantenimiento del repositorio](docs/GITHUB_SETUP.md)
- [Historial de cambios](CHANGELOG.md)

## Licencia

MIT. Las condiciones de las bases OUI y de cualquier herramienta externa opcional se revisan por separado.
