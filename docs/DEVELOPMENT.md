# Guía para desarrolladores

Esta guía es para quienes quieran modificar NetSentinel. **No hace falta leerla para instalar ni para usar la aplicación.**

## Preparar el entorno

Necesitás Python 3.10 o posterior. Desde la carpeta del repositorio:

```bash
python -m venv .venv
```

Activá el entorno virtual (PowerShell de Windows: `.venv\\Scripts\\Activate.ps1`; macOS/Linux: `source .venv/bin/activate`) y ejecutá:

```bash
python -m pip install -e ".[test]"
pytest
```

## Criterios para los cambios

- Agregá pruebas para cada función nueva y para los errores que pueda producir.
- Usá datos sintéticos; las pruebas no deben depender de una red real ni de privilegios elevados.
- No agregues secretos, direcciones privadas reales ni capturas con información sensible.
- Describí el tráfico de cualquier control activo.
- Escribí la documentación en lenguaje sencillo y actualizá el historial de cambios.

GitHub Actions comprueba el proyecto en Windows, macOS y Ubuntu con varias versiones de Python.
