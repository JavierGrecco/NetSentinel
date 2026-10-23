# Prueba manual de NetSentinel Forense

**Objetivo:** revisar el flujo inicial en una instalación local con datos sintéticos, sin tocar evidencia real.

**Estado:** guía preparada; la ejecución manual de esta nueva pantalla todavía debe registrarse. La prueba anterior de NetSentinel Red no cubre Forense.

## Preparación

Esta guía complementa la pantalla `/guided-test`. Si ya seguiste allí la preparación, **no vuelvas a sembrar la base, no cambies de `NETSENTINEL_DATA_DIR` y no arranques una segunda instancia de NetSentinel**.

1. Usá la rama integrada `qa/integrated-map-forensics-scenarios-2026-10`. La preparación de la prueba guiada imprime el valor exacto de `NETSENTINEL_DATA_DIR`, crea `forensics-working-copies/netsentinel-forensic-sample.bin` con el contenido sintético `NetSentinel synthetic evidence v1` y muestra su SHA-256.
2. Mantené abierta la terminal en la que ya se está ejecutando NetSentinel. En el navegador, abrí `http://127.0.0.1:8765/forensics`.
3. Si el archivo sintético no existe, abrí una **segunda terminal** y usá la misma ruta que imprimió la preparación. En macOS o Linux:

   ```bash
   export NETSENTINEL_DATA_DIR="PEGAR_AQUI_LA_RUTA_IMPRESA"
   mkdir -p "$NETSENTINEL_DATA_DIR/forensics-working-copies"
   test -e "$NETSENTINEL_DATA_DIR/forensics-working-copies/netsentinel-forensic-sample.bin" || \
     python3 -c 'from pathlib import Path; import os, hashlib; p=Path(os.environ["NETSENTINEL_DATA_DIR"])/"forensics-working-copies"/"netsentinel-forensic-sample.bin"; p.write_bytes(b"NetSentinel synthetic evidence v1"); print("SHA-256:", hashlib.sha256(p.read_bytes()).hexdigest())'
   ```

   Reemplazá `PEGAR_AQUI_LA_RUTA_IMPRESA` por la ruta exacta. No ejecutes `./run.sh` desde esa segunda terminal. Si el archivo ya existe, no lo recrees: usá el SHA-256 que imprimió la preparación original.
4. La aplicación solo consulta el archivo por nombre dentro de `forensics-working-copies`, bajo el directorio de datos. No admite rutas completas ni enlaces simbólicos. En macOS/Linux, antes de leer una copia restringe la carpeta a permisos `0700`; si no puede hacerlo, bloquea la lectura y registra un error. En Windows se respetan las ACL nativas. Esta prueba utiliza exclusivamente el archivo sintético.

## Recorrido

1. **Abrir un caso.** Usá `LAB-SINTETICO-001`, el título `Verificación de archivo sintético`, la referencia `AUTORIZACION-DE-PRUEBA`, el objetivo `Probar coincidencia y discrepancia SHA-256 de una muestra sintética.` y el alcance `Solo netsentinel-forensic-sample.bin en forensics-working-copies; sin evidencia real.` Indicá `Examinador sintético` como examinador y `Operador sintético de prueba` como persona que realiza la operación.
2. **Registrar el elemento.** Usá la descripción breve `Muestra sintética de integridad`, seleccioná “Copia de archivo”, ingresá `netsentinel-forensic-sample.bin`, la descripción `Archivo artificial para validar el control de integridad; no es evidencia real.`, `Generador local de pruebas` como fuente que entrega y `Examinador sintético` como persona que recibe y queda a cargo. La hora y zona horaria del formulario se completan automáticamente; el tamaño es opcional. Pegá el SHA-256 que imprimió la preparación y escribí `SHA-256 calculado por el generador local al crear la muestra` como origen del hash informado.
3. **Comprobar coincidencia.**** Abrí “Comparar con una copia de trabajo”, escribí solo el nombre `netsentinel-forensic-sample.bin`, sin ruta y marcá la confirmación de que es una copia autorizada, no el soporte original. La aplicación debería devolver **coincide**, mostrar tamaño y SHA-256 calculado y dejar una nueva entrada de auditoría.
4. **Comprobar diferencia.** En otra terminal, entrá en la misma carpeta `forensics-working-copies` y volvé a escribir el archivo con el texto `NetSentinel synthetic evidence v2`. Repetí la comprobación. Debería indicar que el hash no coincide, sin cambiar el valor declarado por la fuente.
5. **Comprobar errores y nombres inválidos.** Desde la pantalla, intentá leer `missing-sample.bin` sin crearlo; después probá una ruta (por ejemplo, `../fuera.bin`) y un nombre con separadores. El error debe explicar el problema y dejar el intento fallido en el historial sin mostrar ni guardar la ruta completa ni el texto rechazado; para un nombre rechazado, el historial debe usar `[nombre rechazado]`. La pantalla bloquea nombres vacíos con la validación del navegador y limita el campo a 255 caracteres, así que esos dos casos no se envían desde la interfaz. Para probarlos, enviá una solicitud directa a la API o ejecutá las pruebas de esos casos en `tests/test_forensics_api.py`; el endpoint permite hasta 4096 caracteres para que el servicio pueda registrar un rechazo seguro. No esperes una entrada de auditoría para un valor que el navegador no llegó a enviar.
6. **Registrar una transferencia de custodia.** En la tarjeta de evidencia, abrí “Registrar transferencia de custodia”. El remitente propuesto debe ser `Examinador sintético` (persona receptora indicada en el formulario de recepción); registrá como destinatario `Custodio sintético receptor`, método `Entrega presencial simulada`, motivo `Entrega autorizada para revisión del archivo sintético`, y una fecha/hora ISO-8601 con offset. Podés escribir `Embalaje sintético íntegro` como condición y `SELLO-LAB-001` como identificador ficticio de precinto. La operación debe aparecer en la auditoría con integridad válida y conservar destinatario, hora declarada, motivo y método en ambos manifiestos.
7. **Probar controles.** Confirmá que no se puede comparar sin marcar la confirmación de copia; que no se puede agregar evidencia ni comprobar hashes una vez cerrado el caso; y que los registros previos siguen visibles.
8. **Probar la navegación.** Cambiá entre NetSentinel Red y Forense desde ambas áreas, recorré los tres temas visuales y comprobá que la navegación se mantenga clara en una ventana estrecha.
9. **Verificar el historial.** Confirmá que cada intento aparece en orden inverso, con operador, hora, resultado y versión, que el hash declarado no se sobrescribe y que la interfaz no muestra la ruta completa en la ficha ni en la auditoría. La API también debe mostrar el hash del evento, el hash anterior y `integrity_status: valid` para un historial intacto.
10. **Exportar y verificar el manifiesto.** Abrí `/api/forensics/cases/ID-DEL-CASO/audit/manifest` reemplazando el marcador por el UUID del caso. Guardá el JSON descargado fuera de la carpeta de datos y ejecutá `python -m netsentinel.forensics_audit_manifest ruta/al/manifiesto.json` en el entorno donde está instalado NetSentinel. La verificación debe aceptar el archivo intacto y rechazarlo si cambiás un campo sin recalcular el digest. Conservá por separado el SHA-256 si necesitás comparar el manifiesto con una copia recibida por otro canal.
11. **Exportar el expediente consolidado.** Desde el mismo caso, usá “Exportar expediente” o abrí `/api/forensics/cases/ID-DEL-CASO/manifest`. Guardá el JSON fuera de la carpeta de datos y ejecutá `python -m netsentinel.forensics_case_manifest ruta/al/expediente.json`. Debe verificar tanto el digest externo del expediente como el digest del manifiesto de auditoría incluido. Confirmá que aparecen la ficha, la evidencia, todas las comprobaciones de hash y la auditoría completa, sin contenido binario ni rutas absolutas. Si el estado de la cadena de auditoría no es `valid`, el verificador debe informar el problema y salir con código distinto de cero. Un digest válido no es una firma digital ni autentica el origen.

12. **Crear el informe de examen.** En el caso sintético, completá la sección “Informe de examen” con los valores propuestos en la prueba guiada. Indicá propósito, alcance realmente realizado, procedimientos, resultados, limitaciones y disposición del original/derivados. Si escribís conclusiones, completá su fundamento; no agregues afirmaciones no observadas.
13. **Exportar y verificar.** Descargá JSON y Markdown. El JSON debe decir que es un borrador sin firma, incluir el digest del informe y una captura del expediente base. Ejecutá `python -m netsentinel.forensics_report ruta/al/informe.json`; la verificación debe informar éxito y el estado borrador. Conservá el JSON intacto.
14. **Comprobar una enmienda.** Creá una versión nueva indicando el informe más reciente y el motivo. Debe aparecer como V2, conservar referencia a V1 y generar una exportación distinta. Nunca se debe sobrescribir ni editar la versión anterior. En una copia separada del JSON, cambiá un campo y verificá que el comando rechace esa copia.

Consultá también la [matriz de preparación pericial](FORENSIC_READINESS_MATRIX.md): esta prueba sintética valida el registro de transferencias, no autentica identidades ni convierte el módulo en un sistema de custodia certificado.

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
