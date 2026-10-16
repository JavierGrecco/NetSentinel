# Prueba manual de NetSentinel Forense

**Objetivo:** revisar el flujo inicial en una instalación local con datos sintéticos, sin tocar evidencia real.

**Estado:** guía preparada; la ejecución manual de esta nueva pantalla todavía debe registrarse. La prueba anterior de NetSentinel Red no cubre Forense.

## Preparación

1. Usá una copia de trabajo del repositorio en la rama `feat/reconcile-forensics-main-2026-10`. Para esta prueba, utilizá un directorio de datos separado del que usás habitualmente.
2. En una terminal, desde la raíz del repositorio, configurá ese directorio. El ejemplo también crea la carpeta en la que la aplicación buscará las copias.

**Windows (PowerShell):**

```powershell
$env:NETSENTINEL_DATA_DIR = Join-Path $HOME ".netsentinel-forensics-manual"
New-Item -ItemType Directory -Force -Path (Join-Path $env:NETSENTINEL_DATA_DIR "forensics-working-copies") | Out-Null
Push-Location (Join-Path $env:NETSENTINEL_DATA_DIR "forensics-working-copies")
py -c "from pathlib import Path; import hashlib; p=Path('netsentinel-forensic-sample.bin'); p.write_bytes(b'NetSentinel synthetic evidence v1'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
Pop-Location
.\run-windows.bat
```

**macOS o Linux:**

```bash
export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-forensics-manual"
mkdir -p "$NETSENTINEL_DATA_DIR/forensics-working-copies"
(
  cd "$NETSENTINEL_DATA_DIR/forensics-working-copies"
  python3 -c 'from pathlib import Path; import hashlib; p=Path("netsentinel-forensic-sample.bin"); p.write_bytes(b"NetSentinel synthetic evidence v1"); print(hashlib.sha256(p.read_bytes()).hexdigest())'
)
./run.sh
```

3. Guardá el SHA-256 que imprime la terminal. La aplicación permanece abierta en esa terminal. En el navegador, abrí `http://127.0.0.1:8765/forensics`.
4. La aplicación solo buscará el archivo por su nombre dentro de `forensics-working-copies`, bajo el directorio definido por `NETSENTINEL_DATA_DIR`. No admite rutas completas ni enlaces simbólicos. En macOS/Linux, antes de leer una copia restringirá la carpeta a permisos `0700`; si no puede hacerlo, bloqueará la lectura y registrará un error. En Windows se respetan las ACL nativas. En esta prueba se usa exclusivamente el archivo sintético.

## Recorrido

1. **Abrir un caso.** Usá un identificador como `MANUAL-2026-001`, una referencia sintética como `AUTORIZACION-DE-PRUEBA`, y escribí claramente que solo cubre el archivo sintético. Elegí un operador de prueba.
2. **Registrar el elemento.** Seleccioná “Copia de archivo”, usá el nombre `netsentinel-forensic-sample.bin`, indicá una descripción sintética, quién lo entrega, fecha/hora original en formato ISO-8601 con offset (por ejemplo `2026-10-15T09:30:00-03:00`), la zona horaria declarada y el tamaño si lo conocés. No ingreses una hora sin offset: el sistema no debe adivinarlo. Pegá el SHA-256 generado y anotá que su origen es el cálculo de la muestra de prueba.
3. **Comprobar coincidencia.** Abrí “Comparar con una copia de trabajo”, escribí solo el nombre `netsentinel-forensic-sample.bin`, sin ruta y marcá la confirmación de que es una copia autorizada, no el soporte original. La aplicación debería devolver **coincide**, mostrar tamaño y SHA-256 calculado y dejar una nueva entrada de auditoría.
4. **Comprobar diferencia.** En otra terminal, entrá en la misma carpeta `forensics-working-copies` y volvé a escribir el archivo con el texto `NetSentinel synthetic evidence v2`. Repetí la comprobación. Debería indicar que el hash no coincide, sin cambiar el valor declarado por la fuente.
5. **Comprobar errores y nombres inválidos.** Desde la pantalla, intentá leer `missing-sample.bin` sin crearlo; después probá una ruta (por ejemplo, `../fuera.bin`) y un nombre con separadores. El error debe explicar el problema y dejar el intento fallido en el historial sin mostrar ni guardar la ruta completa ni el texto rechazado; para un nombre rechazado, el historial debe usar `[nombre rechazado]`. La pantalla bloquea nombres vacíos con la validación del navegador y limita el campo a 255 caracteres, así que esos dos casos no se envían desde la interfaz. Para probarlos, enviá una solicitud directa a la API o ejecutá las pruebas de esos casos en `tests/test_forensics_api.py`; el endpoint permite hasta 4096 caracteres para que el servicio pueda registrar un rechazo seguro. No esperes una entrada de auditoría para un valor que el navegador no llegó a enviar.
6. **Probar controles.** Confirmá que no se puede comparar sin marcar la confirmación de copia; que no se puede agregar evidencia ni comprobar hashes una vez cerrado el caso; y que los registros previos siguen visibles.
7. **Probar la navegación.** Cambiá entre NetSentinel Red y Forense desde ambas áreas, recorré los tres temas visuales y comprobá que la navegación se mantenga clara en una ventana estrecha.
8. **Verificar el historial.** Confirmá que cada intento aparece en orden inverso, con operador, hora, resultado y versión, que el hash declarado no se sobrescribe y que la interfaz no muestra la ruta completa en la ficha ni en la auditoría. La API también debe mostrar el hash del evento, el hash anterior y `integrity_status: valid` para un historial intacto.
9. **Exportar y verificar el manifiesto.** Abrí `/api/forensics/cases/ID-DEL-CASO/audit/manifest` reemplazando el marcador por el UUID del caso. Guardá el JSON descargado fuera de la carpeta de datos y ejecutá `python -m netsentinel.forensics_audit_manifest ruta/al/manifiesto.json` en el entorno donde está instalado NetSentinel. La verificación debe aceptar el archivo intacto y rechazarlo si cambiás un campo sin recalcular el digest. Conservá por separado el SHA-256 si necesitás comparar el manifiesto con una copia recibida por otro canal.

## Qué anotar

- Fecha y zona horaria:
- Persona que hizo la prueba:
- Commit exacto de la rama reconciliada:
- Sistema operativo y versión:
- Navegador y versión:
- Resultado: aprobado / bloqueado:
- Observaciones de jerarquía visual, texto, accesibilidad y tamaño de ventana:
- Enlace a un issue si falla:

No marques la revisión como aprobada si alguna operación da un resultado distinto al esperado. Adjuntá solo capturas saneadas; no subas archivos, hashes de casos reales, rutas privadas ni información personal.

## Qué demuestra y qué no

Esta prueba verifica el comportamiento inicial del registro y la comparación de SHA-256 en datos sintéticos. Una coincidencia solo significa que los bytes leídos coinciden con el valor de referencia que se registró. No certifica la autenticidad de la evidencia, la legalidad de su recepción ni una cadena de custodia completa. La lectura del archivo puede actualizar metadatos de acceso; usá siempre una copia designada.
