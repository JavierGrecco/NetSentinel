# NetSentinel

**Una herramienta local para conocer tu red, registrar cambios y comprobar si tus servicios responden.**

NetSentinel reúne inventario de dispositivos, historial y monitorización en un panel web. Se ejecuta en tu computadora; no necesita una cuenta ni un servidor externo.

## Qué podés hacer

- Consultar dispositivos que el sistema operativo ya conoce, con sus direcciones IP y MAC.
- Marcar dispositivos de confianza y agregarles un nombre o una nota.
- Guardar un historial de lecturas y cambios observados.
- Supervisar un host con ping, un puerto TCP o una URL HTTP/HTTPS.
- Ejecutar un diagnóstico guiado que explica los resultados de red y sugiere qué revisar.
- Consultar incidentes y ver cuándo se recupera un servicio.
- Exportar el inventario y los datos a CSV o JSON.
- Enviar avisos externos opcionales mediante un webhook HTTPS.

> **Importante:** el inventario inicial no garantiza descubrir todos los equipos de la red. El diagnóstico es orientativo: una prueba de ping fallida no demuestra por sí sola que Internet esté caído. Los monitores generan conexiones hacia los objetivos que configures; usalos solo con sistemas que administrás o estás autorizado a comprobar.

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
pytest
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
