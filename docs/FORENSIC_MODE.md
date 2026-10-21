# NetSentinel Forense

**Estado:** primera base funcional en desarrollo. Registra casos, metadatos de recepción y operaciones principales. Todavía no es un sistema de custodia validado ni una herramienta de análisis forense completa.

Seguimiento de la primera entrega funcional: [issue #114](https://github.com/JavierGrecco/NetSentinel/issues/114). Las tareas y sus criterios se actualizan desde el issue y el [roadmap maestro](ROADMAP.md).

NetSentinel Red sigue siendo el módulo de inventario, observabilidad y diagnóstico de red. NetSentinel Forense tendrá su propia entrada, identidad visual y flujo de trabajo, pero compartirá el marco de navegación para que se pueda pasar de un producto al otro desde cualquier sección.

## Qué significa la versión actual

La página `/forensics` permite cambiar entre Red y Forense y ahora incluye un primer espacio de trabajo para casos.

Esta versión ya puede:
- Abrir y listar casos con identificador, referencia de autorización, objetivo, alcance, examinador y estado.
- Registrar metadatos de recepción de elementos de evidencia: tipo de fuente, nombre original (sin ruta), procedencia, persona o fuente que entrega, fecha/hora con offset, zona horaria y tamaño.
- Conservar, como dato **declarado**, un hash informado por una fuente y el nombre del manifiesto o herramienta que lo reportó. Registrar ese dato no lo verifica.
- Añadir eventos de apertura, cierre y registro de evidencia a un historial de solo anexado, con protecciones SQLite contra la edición o eliminación de esas filas desde la aplicación. Los eventos quedan enlazados mediante una cadena SHA-256; la consulta devuelve `integrity_status` (`valid`, `invalid` o `missing`) y detecta cambios, faltantes o filas de cadena asociadas al caso equivocado. La consulta no recompone eslabones ausentes. Se puede descargar el historial completo como un manifiesto JSON versionado desde `/api/forensics/cases/{case_id}/audit/manifest`; incluye los eventos en orden cronológico, el estado global de la cadena y un SHA-256 canónico del propio manifiesto. Para comprobar ese digest fuera de SQLite, ejecutá `python -m netsentinel.forensics_audit_manifest ruta/al/manifiesto.json`. Guardá una copia del digest por otro canal si necesitás detectar sustituciones. El digest no es firma digital: una persona que pueda modificar el archivo puede recalcularlo. Esto no es una garantía absoluta frente a quien pueda reescribir la base completa; para elevar la confianza hará falta un anclaje externo firmado o una firma con una clave gestionada fuera de la aplicación.
- Descargar el **manifiesto consolidado del expediente** desde `/api/forensics/cases/{case_id}/manifest`: ficha del caso, metadatos de evidencia, intentos/comprobaciones de integridad y la auditoría completa en orden cronológico. Incluye un digest SHA-256 del expediente y el manifiesto interno de auditoría; no incluye contenido de los archivos ni rutas completas. Verificá el JSON con `python -m netsentinel.forensics_case_manifest ruta/al/expediente.json`. Conservá la huella por otro canal si necesitás detectar sustituciones; el digest no es una firma.
- Cerrar un caso sin borrar lo registrado.
- Comparar el SHA-256 de una copia local elegida expresamente con el hash declarado por la fuente. El sistema registra cada intento como coincidencia, diferencia o fallo, sin reemplazar el valor declarado.

La pantalla y el flujo de casos nuevos todavía requieren una revisión manual propia. La guía para hacerlo con datos sintéticos está en [FORENSIC_MANUAL_TEST.md](FORENSIC_MANUAL_TEST.md). La confirmación de pruebas de NetSentinel Red no se toma como validación de esta área nueva.

El operador se identifica con un nombre declarado en cada operación; la aplicación todavía no autentica su identidad. La pantalla no copia ni sube el archivo. Para comparar un hash, el servicio solo acepta el nombre de un archivo que ya está dentro de `forensics-working-copies`, en el directorio de datos local de NetSentinel. En sistemas POSIX, la carpeta reservada se restringe a permisos `0700` antes de leer una copia, incluso si ya existía con permisos más amplios; si no se puede asegurar esa protección, la lectura se rechaza. En Windows se utilizan los permisos nativos del sistema. Rechaza rutas completas, separadores, intentos de salir de esa carpeta, nombres de dispositivo de Windows y enlaces simbólicos. Los intentos con nombres no válidos —incluidos vacíos, demasiado largos o con caracteres de control— quedan registrados como fallidos con un marcador genérico, sin guardar el texto rechazado. No guarda la ubicación completa; conserva el nombre seguro, el resultado y los datos mínimos de la operación. La interfaz exige confirmar que se eligió una copia autorizada, no el soporte original.

Cada comparación conserva el hash declarado, el hash calculado, el tamaño, la hora, el operador, la versión de NetSentinel y el resultado. Las fichas de recepción exigen una fecha ISO-8601 que incluya su offset, y guardan por separado la zona horaria declarada; NetSentinel no infiere ese offset a partir del reloj local. Una coincidencia significa que esos bytes producen el mismo SHA-256 que el valor informado; una diferencia no demuestra por sí sola manipulación ni autenticidad. Los intentos de lectura fallidos también se registran sin incluir la ruta completa.

Siguen faltando la autenticación de operadores, los importadores de artefactos y los informes forenses reproducibles. El manifiesto consolidado v1 ya se implementó en esta rama y todavía debe pasar sus pruebas y revisión manual. El componente `netsentinel.forensics_integrity` lee en bloques y comprueba cambios básicos del archivo durante la operación. La lectura puede actualizar metadatos de acceso del sistema operativo; usá una copia designada y no el soporte original. Esta función inicial requiere pruebas manuales específicas antes de poder considerarla lista.

No uses esta versión como registro oficial de una investigación ni para afirmar que una evidencia fue preservada o verificada.

## Alcance de la primera entrega funcional

1. **Casos y autorización.** Identificador estable, responsable, examinador, autoridad, objetivo, alcance permitido y estado del caso.
2. **Registro de evidencia.** Tipo de fuente, origen, persona que la entrega, fecha/hora y zona horaria, tamaño, formato, ubicación de la adquisición y relación con la copia de trabajo.
3. **Integridad verificable.** Manifiesto con algoritmo, hash, fecha, operador y herramienta. Comprobación reproducible sobre una adquisición ya realizada, sin escribir en el original.
4. **Registro de operaciones.** Cada cambio relevante debe guardar quién lo hizo, cuándo, qué objeto afectó y el resultado. Los errores deben explicar qué falló sin exponer datos sensibles.
5. **Importación controlada.** Adaptadores pequeños para formatos exportados por herramientas evaluadas, conservando campos originales, parser/versión, transformación y advertencias.
6. **Pruebas con evidencia conocida.** Conjuntos sintéticos y hashes esperados para validar los procedimientos antes de usarlos en casos reales.

La adquisición de discos, memoria o móviles no forma parte de esta primera entrega. NetSentinel no debe montar por su cuenta un recolector genérico ni reemplazar las herramientas especializadas que adquieren evidencia.

## Etapas posteriores

- Analizar artefactos de navegadores y perfiles, según sistema operativo y versión.
- Importar artefactos de sistema, archivos, correo y registros de red que estén disponibles y autorizados.
- Correlacionar eventos en una línea de tiempo que conserve tiempos originales, zona horaria y conversiones.
- Generar informes con fuentes, hashes, herramientas y versiones, resultados, límites y anexos reproducibles.
- **Siguiente integración recomendada: Hindsight JSONL.** Su exportación actual documenta JSON Lines con un registro por línea y campos como `data_type`, `datetime`, `parser` y `source_long`. El adaptador deberá conservar el tipo de artefacto, la procedencia, la versión del parser y el timestamp original; solo importará tipos y campos incluidos en una lista permitida y validada. No debe copiar registros crudos: el JSONL de origen también puede contener cookies, autocompletado, almacenamiento local/de sesión y otros valores sensibles. Esos tipos y campos quedan fuera del índice común por defecto. Referencias: [salidas JSONL de Hindsight](https://github.com/RyanDFIR/hindsight#command-line) y [codificador del formato](https://github.com/RyanDFIR/hindsight/blob/main/pyhindsight/analysis.py).

- Evaluar Autopsy/The Sleuth Kit para exportar resultados e integridad, y más adelante colecciones offline de Velociraptor. Cada integración requiere revisar licencia, compatibilidad, tratamiento de secretos y resultados con muestras conocidas.

## Reglas que no deben romperse

- No modificar el soporte original ni llamarlo “copia de trabajo”.
- No confundir un hash con prueba de autenticidad: el hash sirve para comparar integridad contra una referencia y debe registrarse cómo se obtuvo.
- No convertir un indicio en conclusión automática.
- No mostrar ni exportar contraseñas, cookies de sesión, tokens o claves privadas en los flujos comunes.
- No inventar que un artefacto no existe: distinguir entre no encontrado, fuente no disponible, archivo dañado, formato no compatible y análisis incompleto.
- No cerrar una tarea solo porque el código o CI estén verdes. Las funciones forenses requieren pruebas con datos conocidos, revisión de seguridad y documentación de límites.

## Criterio para considerar lista la primera entrega

Se puede comenzar con casos de prueba, no con investigaciones reales, cuando estén disponibles las funciones de casos, registro e integridad, la auditoría de operaciones, los controles de privacidad, las pruebas de regresión y los informes de prueba. El uso real requiere además procedimientos y autorización del organismo responsable.
