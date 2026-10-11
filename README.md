# NetSentinel

**NetSentinel** es una aplicación local para observar y diagnosticar una red desde un panel web en español. Su objetivo es registrar dispositivos y cambios con suficiente contexto para que el usuario pueda investigarlos, sin convertir automáticamente indicios en conclusiones de seguridad.

> **Estado:** v0.2.0 — inventario pasivo, múltiples fuentes del sistema, historial de direcciones, consulta OUI local opcional y exportación. No bloquea dispositivos ni realiza barridos activos.

## Funciones incluidas

- Panel web local y API documentada con FastAPI.
- Lectura de tablas de vecinos con proveedores intercambiables: `ip neigh`, fallback `arp` y `ndp` donde estén disponibles.
- Combinación de resultados sin duplicar la misma pareja IP/MAC; un fallo de un proveedor no detiene las demás fuentes.
- Inventario SQLite, múltiples direcciones IPv4/IPv6 asociadas a una MAC y marcas de primera/última observación.
- Evento inicial para una MAC nueva y evento de revisión cuando cambia la IPv4 principal en lecturas consecutivas. Los cambios se presentan como observaciones a verificar, no como prueba de suplantación.
- Resolución opcional de fabricantes desde `oui.csv` local. No se envían MAC a servicios externos.
- Indicador de MAC localmente administrada, que puede corresponder a aleatorización o a una MAC configurada manualmente.
- Lista de confianza manual, nombres y notas por dispositivo, historial de lecturas y exportación CSV/JSON.
- Diagnóstico manual de gateway, DNS y conectividad IP, con aviso de que las pruebas generan tráfico.
- CI con pruebas automáticas en Windows, macOS y Linux.

## Requisitos

- Python 3.10 o posterior.
- Para el inventario básico no hace falta una base de datos externa ni privilegios de administrador.
- Las herramientas disponibles para leer vecinos dependen del sistema operativo; NetSentinel usa las que encuentre.

## Instalación y uso

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
netsentinel
```

Si PowerShell bloquea la activación del entorno, se puede ejecutar directamente `\.venv\Scripts\python.exe -m pip install -e ".[test]"` y luego `\.venv\Scripts\netsentinel.exe`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
netsentinel
```

El navegador abre `http://127.0.0.1:8765`. También se puede ejecutar `netsentinel --no-browser`, elegir otro puerto mediante `--port 8766` o cambiar el directorio de datos con la variable `NETSENTINEL_DATA_DIR`.

Por defecto, el servidor escucha solo en `127.0.0.1`. No lo expongas a una red compartida sin añadir autenticación, protección de origen y una configuración de despliegue revisada.

### Ejecutar las pruebas

```bash
python -m pytest
```

## Identificación local de fabricantes (OUI)

La función es opcional y no consulta Internet. Si disponés de un registro de asignaciones OUI autorizado, guardalo como:

- Windows: `%USERPROFILE%\.netsentinel\oui.csv`
- macOS / Linux: `~/.netsentinel/oui.csv`

Se admiten dos formatos CSV:

```csv
prefix,vendor
AABBCC,Ejemplo de fabricante
```

O el formato de registro IEEE con columnas `Assignment` y `Organization Name`. Se aceptan prefijos MA-L (6 dígitos hexadecimales), MA-M (7) y MA-S (9), con o sin separadores. La aplicación muestra la fuente local y cuándo consultó la base. **La base OUI no se incluye**: su distribución, licencia y fecha de actualización dependen del registro que elijas utilizar.

## API

- `GET /api/health` — estado y versión.
- `GET /api/summary` — métricas generales.
- `GET /api/devices?q=...` — inventario (incluye fabricante, indicador de MAC local y direcciones conocidas).
- `GET /api/devices/{id}/addresses` — historial agregado de direcciones de un dispositivo.
- `GET /api/events?limit=50` — eventos revisables.
- `GET /api/scans?limit=30` — historial de lecturas y fuentes.
- `POST /api/scan` — leer las tablas locales de vecinos.
- `POST /api/diagnostics` — ejecutar diagnóstico manual.
- `PATCH /api/devices/{id}` — modificar confianza, nombre y notas.
- `PATCH /api/events/{id}` — marcar evento revisado.
- `GET /api/export/devices.csv` y `GET /api/export/data.json` — exportaciones.
- `GET /api/docs` — documentación interactiva de la API.

## Privacidad y límites

- La información se guarda localmente en SQLite dentro de `~/.netsentinel` (o en `NETSENTINEL_DATA_DIR`). En sistemas POSIX el directorio y el archivo se restringen al usuario cuando el sistema de archivos lo permite.
- NetSentinel no hace solicitudes externas durante el inventario pasivo. El diagnóstico opcional consulta DNS y prueba conectividad IP, algo que se explica en el panel antes de ejecutarse.
- Una tabla de vecinos es una caché parcial. La ausencia de un dispositivo no demuestra que esté desconectado.
- Un fabricante identificado por prefijo OUI no verifica la identidad de un dispositivo. Una MAC localmente administrada puede ser aleatoria, personalizada o pertenecer a un entorno virtual.
- Un cambio de IP puede tener causas legítimas (DHCP, IPv6, movilidad). Los eventos son pistas para revisar.
- En v0.2 no se bloquean equipos, no se escribe en routers, no se inspeccionan contenidos HTTPS y no se realiza escaneo activo de puertos.

## Estructura del proyecto

```text
src/netsentinel/
├── cli.py                 # Inicio y opciones de ejecución
├── config.py              # Directorio de datos
├── database.py            # SQLite, historial y exportaciones
├── diagnostics.py         # Pruebas de conectividad explícitas
├── discovery.py           # Proveedores del sistema y parsers de vecinos
├── vendor.py              # Base OUI local opcional y bits de la MAC
├── main.py                # API FastAPI
└── static/index.html      # Panel web local
```

## Plan de versiones

Consultar [`docs/ROADMAP.md`](docs/ROADMAP.md), [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) y [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). La próxima etapa prioriza diagnóstico con evidencias, alertas sin duplicados y exportación de informes.

## Contribuir y seguridad

- [Guía de contribución](CONTRIBUTING.md)
- [Política de seguridad](SECURITY.md)
- [Arquitectura](docs/ARCHITECTURE.md)

Las pruebas no necesitan una red real. No adjuntes a issues datos reales de direcciones, MAC, dominios internos, credenciales ni exportaciones de inventario.

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Revisá las condiciones de los registros OUI y cualquier dependencia opcional por separado.
