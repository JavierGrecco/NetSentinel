# Prueba responsive de la interfaz

Esta guía permite comprobar las seis pantallas de NetSentinel en ventanas de distintos tamaños. El verificador usa Chromium y Playwright, levanta una instancia local temporal y escribe el informe fuera del código del producto.

La prueba no hace descubrimiento de dispositivos, no ejecuta diagnósticos de red y no usa la base de datos habitual. Para la revisión visual, las capturas son opcionales y se guardan dentro de `.netsentinel-test-artifacts/responsive-ui/`.

## 1. Actualizar el repositorio

Desde la carpeta local del proyecto:

```bash
git switch main
git fetch origin
git pull --ff-only origin main
git status --short --branch
git log -1 --format='Commit: %H%nFecha: %cI%nAsunto: %s'
```

Antes de continuar, confirmá que se descargó el último commit esperado y que no hay cambios propios que necesites guardar. Si Git informa que hay cambios sin confirmar, no los borres para forzar la actualización.

## 2. Preparar el entorno

Se necesita Python 3.10 o posterior. Creá el entorno virtual solo si todavía no existe.

### macOS o Linux

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,ui-test]"
python -m playwright install chromium
```

### Windows (PowerShell)

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test,ui-test]"
python -m playwright install chromium
```

Si el entorno `.venv` ya existe, no hace falta crearlo de nuevo. Activá ese entorno y ejecutá las dos instrucciones de instalación para actualizar las dependencias.

En Linux, si Chromium informa que faltan bibliotecas del sistema, podés instalar sus dependencias con `python -m playwright install --with-deps chromium`. Ese paso puede necesitar permisos de administrador para los paquetes del sistema.

## 3. Ejecutar las comprobaciones automáticas

Con el entorno virtual activo y situado en la raíz del repositorio:

```bash
python -m pytest -q
python scripts/check_responsive_ui.py
```

El verificador abre una instancia local temporal y recorre las seis secciones —Inventario, Hallazgos, Monitorización, Herramientas, Actividad y Forense— en quince tamaños representativos, desde 320×640 hasta 1920×1080. Comprueba que las páginas carguen, que la sección activa sea única, que los tres temas aparezcan, que no se expanda horizontalmente toda la página y que el Inventario cambie a una columna cuando corresponde.

La ejecución termina con código distinto de cero si encuentra fallos. El detalle queda en:

```text
.netsentinel-test-artifacts/responsive-ui/report.json
```

## 4. Guardar capturas para revisar el diseño

```bash
python scripts/check_responsive_ui.py --screenshots
```

Guarda una captura del Inventario para cada tamaño de la matriz y una captura de cada una de las seis secciones en 1440×900. Abrí esas imágenes y revisá especialmente la cabecera, la navegación, el selector de temas, la segunda fila del Inventario, los márgenes y cualquier texto cortado.

Para probar otros tamaños personalizados, usá el formato `ancho x alto`, separados por comas:

```bash
python scripts/check_responsive_ui.py --viewports "375x667,820x1180,1366x768"
```

Para usar una instancia que ya tenés iniciada, la dirección debe ser local y loopback:

```bash
python scripts/check_responsive_ui.py --base-url http://127.0.0.1:8765
```

El servidor pasado con `--base-url` no será reiniciado por el verificador. Por defecto, en cambio, el propio verificador inicia y detiene su instancia temporal.

## 5. Levantar NetSentinel para probarlo manualmente

La verificación responsive termina al cerrar su instancia temporal. Para recorrer después la aplicación en el navegador, abrí una segunda terminal.

### macOS o Linux

```bash
cd /ruta/a/NetSentinel
source .venv/bin/activate
export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-responsive-manual"
mkdir -p "$NETSENTINEL_DATA_DIR"
python -m netsentinel --host 127.0.0.1 --port 8765
```

### Windows (PowerShell)

```powershell
Set-Location C:\ruta\a\NetSentinel
.\.venv\Scripts\Activate.ps1
$env:NETSENTINEL_DATA_DIR = Join-Path $HOME ".netsentinel-responsive-manual"
New-Item -ItemType Directory -Force -Path $env:NETSENTINEL_DATA_DIR | Out-Null
python -m netsentinel --host 127.0.0.1 --port 8765
```

Abrí [http://127.0.0.1:8765](http://127.0.0.1:8765). Para detener NetSentinel, volvé a la terminal y pulsá **Control+C**. El directorio `NETSENTINEL_DATA_DIR` es específico de esta prueba; no lo apuntes a una base que quieras conservar.

Si el puerto 8765 ya está ocupado, usá 8766 y abrí `http://127.0.0.1:8766`. No hace falta cerrar otros programas. Mantené la aplicación vinculada a loopback; no la expongas a la red para esta prueba.

## 6. Qué registrar

Guardá la fecha, el commit probado, el sistema operativo, la versión de Python, la matriz ejecutada y el resumen del informe. Si hay un fallo visual, vinculá la captura de ese tamaño y anotá el resultado esperado. No adjuntes bases de datos ni inventarios reales.

La prueba automática ayuda a encontrar regresiones de tamaño y estructura; una revisión humana en pantalla sigue siendo necesaria para juzgar el equilibrio visual, la legibilidad y la facilidad de uso. Registrá el resultado final en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
