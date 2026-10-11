# Contribuir a NetSentinel

¡Gracias por ayudar! El proyecto está en una etapa temprana y prioriza una herramienta local, explicable y segura.

## Antes de empezar

1. Abrí un issue describiendo el problema o la propuesta y su alcance.
2. Para cambios grandes, esperá a acordar el diseño antes de invertir trabajo.
3. No incluyas direcciones reales, MAC privadas, credenciales, tokens ni capturas con datos sensibles en issues o tests.

## Preparar el entorno

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -e '.[test]'
pytest
```

## Reglas de contribución

- Incluí pruebas para cambios funcionales y regresiones.
- Usá fixtures sintéticas para direcciones IP, MAC y salidas de comandos.
- No hagas que los tests dependan de una red real, Internet o privilegios de administrador.
- Mantené el host local como configuración predeterminada.
- Documentá requisitos, permisos, tráfico generado y limitaciones de cada nueva integración.
- No agregues acciones que cambien la red, intercepten tráfico o envíen telemetría sin una propuesta explícita y revisión de seguridad.
- Actualizá README y documentación técnica cuando cambie el comportamiento.

## Pull requests

Explicá el problema, la solución, cómo se probó y las limitaciones conocidas. Mantené los cambios enfocados; evitá combinar refactorizaciones amplias con funciones nuevas.
