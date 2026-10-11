#!/bin/sh
# NetSentinel launcher for macOS and Linux.
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

PYTHON_BIN=$(command -v python3 || true)
if [ -z "$PYTHON_BIN" ]; then
    echo "No encuentro python3. Instalá Python 3.10 o posterior e intentá de nuevo." >&2
    exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "NetSentinel necesita Python 3.10 o posterior." >&2
    exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
    if ! "$PYTHON_BIN" -m venv .venv; then
        echo "No pude crear el entorno virtual .venv. Revisá tu instalación de Python." >&2
        exit 1
    fi
fi

if ! ".venv/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "El entorno .venv existente usa una versión vieja de Python. Renombrá o eliminá .venv y volvé a ejecutar este script." >&2
    exit 1
fi

if ! ".venv/bin/python" -m pip install -e .; then
    echo "No pude instalar las dependencias. Revisá tu conexión a Internet e intentá de nuevo." >&2
    exit 1
fi

exec ".venv/bin/python" -m netsentinel
