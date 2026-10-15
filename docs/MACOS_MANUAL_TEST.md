# Prueba manual en macOS (PR #111)

Esta guía prepara una prueba de la rama de modularización sin tocar `main` ni reutilizar la base de datos de una instalación anterior. La aplicación es local y no descubre dispositivos hasta que se lo pedís desde la interfaz.

La prueba manual sigue pendiente hasta registrar los resultados reales en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) y en el [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).

## 1. Descargar la rama correcta

Abrí Terminal. Estos comandos descargan la rama que contiene los cambios propuestos en la PR #111, no `main`:

```bash
cd "$HOME"
git clone --single-branch --branch refactor/activity-persistence-modules https://github.com/JavierGrecco/NetSentinel.git NetSentinel-manual-test
cd "$HOME/NetSentinel-manual-test"
git fetch origin
git pull --ff-only origin refactor/activity-persistence-modules
git status --short --branch
git log -1 --format='Commit: %H%nFecha: %cI%nAsunto: %s'
```

Guardá el SHA completo del commit que aparece. Si `git clone` avisa que la carpeta ya existe, no borres nada: elegí otro nombre para la carpeta y repetí el comando de descarga con ese nombre. Antes de probar, `git status` debe mostrar una copia limpia, sin cambios locales.

## 2. Preparar Python sin modificar la instalación del Mac

Se necesita Python 3.10 o posterior. Primero comprobalo:

```bash
python3 --version
python3 -c 'import sys; print("Versión compatible" if sys.version_info >= (3, 10) else "Necesita Python 3.10 o posterior")'
```

Dentro de la carpeta `NetSentinel-manual-test`, prepará un entorno aislado e instalá las dependencias de ejecución y de prueba:

```bash
cd "$HOME/NetSentinel-manual-test"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

No hace falta usar `sudo` ni instalar paquetes globalmente. Cuando vuelvas a abrir Terminal, activá de nuevo el entorno con `source .venv/bin/activate`.

## 3. Ejecutar las pruebas automáticas en el Mac

Con el entorno virtual activado y dentro de la carpeta del repositorio:

```bash
python -m pytest -q
```

Dejá que termine. Si hay fallos, copiá el nombre de cada prueba fallida y el mensaje final; no hace falta enviar inventarios, bases de datos ni registros que contengan información real. No continúes con la prueba de uso hasta anotar cualquier fallo.

Registrá también estos datos:

```bash
sw_vers
python --version
git log -1 --format='%H'
```

## 4. Iniciar la aplicación con datos de prueba separados

Esta variable crea un directorio de datos nuevo para esta sesión, en lugar de usar la base de datos habitual de NetSentinel. No la cambies por la ruta de una instalación previa.

```bash
export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-manual-test-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$NETSENTINEL_DATA_DIR"
printf 'Datos de prueba aislados en: %s\n' "$NETSENTINEL_DATA_DIR"
./run.sh
```

El proceso queda activo en esa Terminal y el navegador debería abrir `http://127.0.0.1:8765`. Si no se abre, copiá esa dirección en el navegador. Para detener la aplicación, volvé a la Terminal y pulsá **Control+C**.

Si el puerto 8765 ya está ocupado, no cierres ni finalices otros procesos. Detené esta ejecución con Control+C y usá el puerto alternativo:

```bash
./.venv/bin/python -m netsentinel --port 8766
```

En ese caso, abrí `http://127.0.0.1:8766`. Mantené abierta la Terminal mientras probás la aplicación.

## 5. Recorrido básico de la interfaz

Usá datos ficticios y registrá qué ocurre en cada paso:

- [ ] La aplicación inicia sin errores y el panel local abre en el navegador.
- [ ] Las pantallas principales se abren desde el menú y no quedan en blanco: inventario, Monitorización, Herramientas, Hallazgos y Actividad.
- [ ] El panel responde al actualizar la página y al detener/reiniciar la aplicación.
- [ ] Los mensajes de error, cuando aparecen, explican el problema sin mostrar tokens ni datos sensibles.
- [ ] La aplicación escucha solo en loopback; no configures acceso desde otros equipos.
- [ ] La copia de seguridad o exportación SQLite puede descargarse y abrirse como base SQLite válida.
- [ ] Si probás descubrimiento de red, hacelo solo en una red propia o expresamente autorizada. La búsqueda empieza cuando la solicitás y puede generar tráfico local; no es necesaria para verificar el arranque.

Para las pruebas de DNS/TLS, usá destinos de prueba públicos y tené en cuenta que dependen de la conexión disponible. Anotá timeout, error de certificado o respuesta inesperada; no los presentes como fallos del producto sin registrar el contexto de red.

## 6. Comprobar un respaldo SQLite (opcional, recomendado)

Después de descargar una copia desde la interfaz, podés validar el archivo sin modificarlo. Reemplazá la ruta de ejemplo por la ubicación real del archivo descargado:

```bash
python - <<'PY'
import sqlite3
from pathlib import Path
from urllib.parse import quote

path = Path(input("Ruta del respaldo SQLite descargado: ")).expanduser().resolve()
if not path.is_file():
    raise SystemExit("No encuentro el archivo indicado; revisá la ruta.")
uri = f"file:{quote(str(path), safe='/')}?mode=ro"
with sqlite3.connect(uri, uri=True) as connection:
    print("PRAGMA integrity_check:", connection.execute("PRAGMA integrity_check").fetchone()[0])
PY
```

El resultado esperado es `ok`. Esta comprobación no reemplaza una restauración completa; no reemplaces la base de datos habitual con un archivo de prueba.

## 7. Prueba manual de la extensión Chromium (opcional)

Usá Chrome o Edge y solo datos ficticios. La guía específica está en [browser-extension/README.md](../browser-extension/README.md).

1. Abrí `chrome://extensions` o `edge://extensions`, activá el modo de desarrollador y elegí **Cargar descomprimida**.
2. Seleccioná la carpeta `browser-extension` dentro de esta descarga.
3. Confirmá que el seguimiento esté apagado al instalarla. No lo actives hasta haber revisado sus permisos y el propósito de la prueba.
4. Si hacés una prueba de captura, usá una página pública y parámetros falsos como `access_token=FAKE_TOKEN_123` y `sessionid=FAKE_SESSION_456`; comprobá localmente que esos valores no aparezcan en el CSV exportado.
5. Probá pausar y desactivar el seguimiento, y confirmá que deja de registrar nuevas visitas. No subas el CSV: puede contener metadatos de navegación aunque uses una cuenta de prueba.

La extensión no debe usarse para recolectar información de otras personas sin autorización adecuada. No habilites navegación privada para esta prueba.

## 8. Enviar el resultado

Al terminar, compartí solo:

- fecha de la prueba, versión de macOS y versión de Python;
- SHA completo que anotaste en el paso 1;
- resultado de `pytest` (correcto o pruebas que fallaron);
- si la aplicación abrió y qué pantallas recorriste;
- número de pasos aprobados/fallidos y descripción breve de cada fallo.

No envíes bases SQLite, CSV, inventarios reales, IP públicas del cliente, cookies, tokens, credenciales, URLs privadas ni capturas sin revisar. Anotá la evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) y vinculá los problemas al [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75).