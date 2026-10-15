# Prueba manual de NetSentinel Forense

**Objetivo:** revisar el flujo inicial en una instalación local con datos sintéticos, sin tocar evidencia real.

**Estado:** guía preparada; la ejecución manual de esta nueva pantalla todavía debe registrarse. La prueba anterior de NetSentinel Red no cubre Forense.

## Preparación

1. Usá una copia de trabajo del repositorio en la rama de la PR #113 y un directorio de datos separado para esta prueba. No mezcles estos registros con los datos cotidianos de NetSentinel.
2. Iniciá NetSentinel y abrí `http://127.0.0.1:8765/forensics`.
3. Creá un archivo sintético en una carpeta temporal. Desde esa misma computadora, abrí una terminal y ejecutá:

**Windows (PowerShell):**

```powershell
py -c "from pathlib import Path; import hashlib; p=Path('netsentinel-forensic-sample.bin'); p.write_bytes(b'NetSentinel synthetic evidence v1'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

**macOS o Linux:**

```bash
python3 -c "from pathlib import Path; import hashlib; p=Path('netsentinel-forensic-sample.bin'); p.write_bytes(b'NetSentinel synthetic evidence v1'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

Guardá el hash que imprime la terminal. El archivo es de prueba; no pongas datos personales en él.

## Recorrido

1. **Abrir un caso.** Usá un identificador como `MANUAL-2026-001`, una referencia sintética como `AUTORIZACION-DE-PRUEBA`, y escribí claramente que solo cubre el archivo sintético. Elegí un operador de prueba.
2. **Registrar el elemento.** Seleccioná “Copia de archivo”, usá el nombre `netsentinel-forensic-sample.bin`, indicá una descripción sintética, quién lo entrega, fecha/hora original en formato ISO-8601 con offset (por ejemplo `2026-10-15T09:30:00-03:00`), la zona horaria declarada y el tamaño si lo conocés. No ingreses una hora sin offset: el sistema no debe adivinarlo. Pegá el SHA-256 generado y anotá que su origen es el cálculo de la muestra de prueba.
3. **Comprobar coincidencia.** Abrí “Comparar con una copia de trabajo”, escribí la ruta local completa de ese archivo y marcá la confirmación de que es una copia autorizada, no el soporte original. La aplicación debería devolver **coincide**, mostrar tamaño y SHA-256 calculado y dejar una nueva entrada de auditoría.
4. **Comprobar diferencia.** Volvé a generar el mismo archivo con contenido distinto, por ejemplo cambiando `v1` por `v2`. Repetí la comprobación. Debería indicar que el hash no coincide, sin cambiar el valor declarado por la fuente.
5. **Comprobar error de lectura.** Intentá leer un nombre de archivo que no exista. Debería explicar el problema y guardar una comprobación fallida con código, sin mostrar ni persistir la ruta completa en el historial.
6. **Probar controles.** Confirmá que no se puede comparar sin marcar la confirmación de copia; que no se puede agregar evidencia ni comprobar hashes una vez cerrado el caso; y que los registros previos siguen visibles.
7. **Probar la navegación.** Cambiá entre NetSentinel Red y Forense desde ambas áreas, recorré los tres temas visuales y comprobá que la navegación se mantenga clara en una ventana estrecha.
8. **Verificar el historial.** Confirmá que cada intento aparece en orden inverso, con operador, hora, resultado y versión, que el hash declarado no se sobrescribe y que la interfaz no muestra la ruta completa en la ficha ni en la auditoría.

## Qué anotar

- Fecha y zona horaria:
- Persona que hizo la prueba:
- Commit exacto de la PR:
- Sistema operativo y versión:
- Navegador y versión:
- Resultado: aprobado / bloqueado:
- Observaciones de jerarquía visual, texto, accesibilidad y tamaño de ventana:
- Enlace a un issue si falla:

No marques la revisión como aprobada si alguna operación da un resultado distinto al esperado. Adjuntá solo capturas saneadas; no subas archivos, hashes de casos reales, rutas privadas ni información personal.

## Qué demuestra y qué no

Esta prueba verifica el comportamiento inicial del registro y la comparación de SHA-256 en datos sintéticos. Una coincidencia solo significa que los bytes leídos coinciden con el valor de referencia que se registró. No certifica la autenticidad de la evidencia, la legalidad de su recepción ni una cadena de custodia completa. La lectura del archivo puede actualizar metadatos de acceso; usá siempre una copia designada.
