# Publicación y colaboración en GitHub

Repositorio del proyecto: <https://github.com/JavierGrecco/NetSentinel>.

## Desarrollo local

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest
```

## Flujo recomendado

1. Crear una rama enfocada en la mejora (`feat/...`, `fix/...` o `docs/...`).
2. Incluir pruebas para cambios funcionales y actualizar documentación.
3. Ejecutar `python -m pytest` y `python -m compileall -q src tests`.
4. Abrir un pull request con alcance, pruebas, limitaciones y riesgos.
5. Revisar los resultados de GitHub Actions en Windows, macOS y Linux antes de fusionar.

## CI

El flujo de `.github/workflows/ci.yml` instala el paquete de forma editable y ejecuta la suite en una matriz de sistemas operativos y versiones de Python. No marcar una plataforma como verificada hasta que su ejecución remota de Actions termine correctamente.
