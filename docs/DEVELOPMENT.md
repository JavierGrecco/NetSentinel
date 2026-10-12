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
- Para probar la API con TestClient, usá `base_url="http://127.0.0.1"` y cubrí tanto peticiones same-origin como orígenes/hosts rechazados.
- Escribí la documentación en lenguaje sencillo y actualizá el historial de cambios.

GitHub Actions comprueba el proyecto en Windows, macOS y Ubuntu con varias versiones de Python. Además, un job separado instala el conjunto mínimo de dependencias directas declarado en `ci/constraints-min.txt` sobre Python 3.10 para detectar regresiones de compatibilidad con las versiones más antiguas que el proyecto promete soportar. Cuando cambie una cota mínima en `pyproject.toml`, actualizá también el archivo de constraints y verificá esa combinación.
