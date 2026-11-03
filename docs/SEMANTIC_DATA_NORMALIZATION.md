# Normalización semántica y reconocimiento seguro de datos

- **Estado:** diseño de arquitectura con primera implementación parcial en la PR #212; todavía no integrada en `main`.
- **Fecha:** 2026-11-03.
- **Alcance:** interpretación de campos, alias, errores de tipeo, unidades, valores ausentes, calidad y preparación de métricas.
- **Compatibilidad:** conservar los contratos actuales de Actividad, Zeek, Monitorización, Inventario y SQLite durante la primera etapa.

## Estado de implementación — 3 de noviembre de 2026

La primera entrega está en [PR #212](https://github.com/JavierGrecco/NetSentinel/pull/212), rama `feat/semantic-data-registry-2026-11`. El HEAD actualmente en revisión es `f89c7654904ae9cd243a545477cbe2b610263151`. La implementación no se presenta como terminada ni como integrada en `main`.

### Ya implementado en la PR #212

- Paquete puro `src/netsentinel/semantics/` con modelos, catálogo, perfiles de origen, resolver y utilidades de inspección.
- 23 campos canónicos del contrato actual de Actividad y perfiles `activity_csv` y `zeek_conn_log`.
- CSV utiliza el perfil compartido en lugar de mantener una segunda lista de alias. Se verificó paridad exacta respecto del importador anterior: 23/23 campos, 47/47 alias con el mismo destino, 27/27 cabeceras ignoradas y 26/26 cabeceras sensibles.
- Zeek TSV/JSONL utiliza el perfil de origen para validar el esquema y señalar campos requeridos ausentes o con errores tipográficos, sin cambiar la interpretación específica de su timestamp Unix ni de los contadores.
- Las cabeceras duplicadas, inseguras o ambiguas se bloquean. Las sugerencias se limitan a una única inserción, eliminación o sustitución; varios candidatos se marcan como ambiguos. No hay autocorrección.
- La inspección de valores diferencia ausente, vacío, válido, tipo incompatible, inválido, ambiguo y campo desconocido. La conversión de unidades requiere una unidad explícita, compatible y no ambigua.
- El resolver limita las cabeceras a 256 y el análisis numérico limita la longitud y escala de entrada.
- El verificador de arquitectura declara el grafo permitido para el paquete semántico y prohíbe que dependa de API, servicios, repositorios o infraestructura.

### Límites actuales — no declararlos resueltos

- `inspect_field_value` es una utilidad tipada probada; no reemplaza la validación autoritativa de `activity_event_service.py`. Los importadores siguen usando sus validadores de dominio específicos.
- Las sugerencias y errores de cabecera se comunican en el resultado de validación del preview. Todavía no hay una pantalla dedicada de mapeo interactivo ni una tabla visual de calidad por columna.
- El catálogo aún no incluye todo el modelo objetivo de dominio, tipo de evento, política de agregación, cardinalidad, enriquecimiento y versionado de esquema.
- No existe todavía una política completa de `not_applicable` frente a `not_reported` para todos los campos. No se agregan valores por defecto ni se convierte ausencia en cero.
- Monitorización, Inventario y Forense no utilizan este catálogo. No se cambió SQLite, el contrato HTTP ni el esquema persistido.

Los principios y objetivos de las secciones siguientes siguen siendo el destino de diseño. La PR #212 implementa solo una base común de Actividad/CSV/Zeek, no el modelo completo descrito en esta propuesta.

## 1. Decisión propuesta

Incorporar un **registro semántico determinista** dentro del monolito modular. Su responsabilidad es convertir nombres y estructuras heterogéneas en un vocabulario interno pequeño, tipado y verificable. Los adaptadores de cada fuente siguen siendo responsables de interpretar su formato; el registro les proporciona definiciones comunes, alias, unidades y reglas de resolución.

No se propone un motor que adivine libremente campos a partir de números ni un servicio de IA. La resolución debe ser reproducible, local, explicable y conservadora: una entrada ambigua queda sin resolver, no se convierte en una certeza.

La primera entrega debe ser una refactorización acotada de la normalización de Actividad y de los importadores CSV/Zeek existentes. No debe agregar captura de paquetes, conectores remotos, una plataforma de plugins ni una migración masiva de SQLite.

## 2. Problema que resuelve

Actualmente hay lógica útil, pero distribuida:

- `activity_event_service.py` normaliza y valida valores del contrato de eventos.
- `activity_import_service.py` normaliza cabeceras CSV y mantiene alias.
- `activity_zeek_import_service.py` interpreta el esquema Zeek y traduce sus campos.
- `activity_catalog.py` define tipos de eventos y protocolos.

La solución debe evitar que cada importador mantenga su propio vocabulario y que dos fuentes asignen significados distintos al mismo nombre. También debe distinguir entre conocer el tipo de un valor y conocer su significado dentro de un evento.

## 3. Principios no negociables

1. **La semántica tiene prioridad sobre la similitud textual.** Un alias exacto y documentado para una fuente prevalece sobre cualquier sugerencia aproximada.
2. **El contexto limita la búsqueda.** Resolver dentro de fuente, versión, formato y tipo de evento; no comparar todos los nombres de todas las áreas.
3. **Inferir el tipo no equivale a inferir el rol.** Reconocer una IP no permite decidir si es origen o destino.
4. **La ausencia nunca se convierte en cero.** Cero es una medición; ausente es falta de observación.
5. **No mezclar magnitudes distintas.** Bytes IP, bytes de carga útil, paquetes, duración y tasa son conceptos diferentes.
6. **Los datos originales no se reescriben silenciosamente.** Conservar procedencia y una descripción de la transformación; no guardar valores desconocidos sensibles por defecto.
7. **Una coincidencia incierta no se importa como verdad.** Los casos ambiguos se presentan en la vista previa y requieren corrección o exclusión explícita.
8. **Sin dependencias operativas innecesarias.** La primera versión debe usar Python estándar y el catálogo interno; agregar una biblioteca de fuzzy matching requiere demostrar un beneficio medible.

## 4. Modelo de conocimiento

El registro distingue cuatro conceptos:

| Concepto | Ejemplo | Responsabilidad |
|---|---|---|
| Campo canónico | `source_ip` | Nombre interno estable y significado documentado |
| Alias de fuente | `id.orig_h`, `src_ip` | Traducción de un nombre concreto y contextualizado |
| Tipo de valor | IP, entero, fecha, duración | Validación estructural del valor |
| Unidad/dimensión | bytes, segundos, paquetes, porcentaje | Comparabilidad y conversión matemática |

Una definición de campo debe incluir como mínimo:

- Identificador canónico estable.
- Dominio y tipo de evento aplicables.
- Tipo de dato y validación.
- Dimensión y unidad canónica, cuando correspondan.
- Rol semántico (por ejemplo, extremo de origen, latencia observada o bytes IP enviados).
- Campos requeridos, opcionales o no aplicables por tipo de evento.
- Política de agregación permitida, si el dato es una métrica.
- Sensibilidad, cardinalidad esperada y posibilidad de enriquecimiento.
- Versión de la definición.

Los alias se registran separadamente y se acotan por `source_format`, `source_version` y `event_type` cuando se conozcan. Un alias global solo se permite cuando su significado no depende de la fuente.

## 5. Resolución de nombres y errores de tipeo

La resolución usa este orden, deteniéndose ante conflictos:

1. Campo canónico exacto.
2. Alias exacto de la fuente y versión.
3. Normalización léxica conservadora: BOM, Unicode NFKC, `casefold`, separación de camelCase y equivalencia de separadores (`.`, `_`, guion y espacio).
4. Alias alternativo explícitamente aprobado para el perfil de origen.
5. Detección aproximada para sugerir una corrección.
6. Campo desconocido.

La normalización léxica no debe eliminar indiscriminadamente caracteres ni reemplazar caracteres visualmente parecidos de alfabetos diferentes. Los caracteres confusables deben generar una advertencia, no una equivalencia silenciosa. Los acentos y transliteraciones se agregan como alias explícitos solo cuando una fuente real los necesita.

### Política fuzzy

La comparación aproximada se limita a cabeceras todavía no resueltas y a candidatos compatibles con el mismo formato/tipo de evento. No debe comparar contra todo el catálogo ni contra valores de celdas.

En la primera versión, fuzzy matching **solo recomienda**: muestra cabecera original, campo propuesto, diferencia y motivo. No corrige automáticamente campos críticos (IP, puertos, bytes, paquetes, marcas temporales, identificadores, severidad o estados).

Una futura autocorrección solo se habilita tras disponer de un corpus de cabeceras reales y errores sintéticos, con precisión medida, margen suficiente frente al segundo candidato, validación de tipo y ausencia de colisiones. Un puntaje de similitud es una medida textual, no una probabilidad de que la interpretación sea correcta. Umbrales y márgenes deben surgir de esa evaluación, no de una cifra universal arbitraria.

Alias conocidos como errores recurrentes pueden convertirse en reglas explícitas, revisadas y versionadas. Si dos cabeceras se resuelven al mismo campo canónico, se debe comprobar si sus valores coinciden; valores conflictivos bloquean la importación de ese registro/lote y se explican en el preview.

## 6. Inferencia a partir de valores y unidades

La inferencia basada en contenido es útil para validar o acotar tipos posibles, pero no debe usarse como sustituto universal de nombres, metadatos de formato y contexto.

### Señales fuertes

- Un valor que supera `ipaddress.ip_address` puede clasificarse como dirección IP.
- Una MAC válida puede clasificarse como dirección de enlace.
- Una fecha ISO 8601 con zona explícita puede clasificarse como marca temporal.
- Una unidad explícita y reconocida en el encabezado o metadato puede identificar una dimensión y habilitar conversiones.
- Un perfil/versionado de fuente puede declarar que `ts` es tiempo Unix en segundos, `duration` es duración en segundos y `orig_ip_bytes` son bytes a nivel IP.

### Señales insuficientes por sí solas

- Un entero entre 0 y 65535 no demuestra que sea un puerto.
- Un entero no permite distinguir bytes, paquetes, conexiones, identificadores ni milisegundos.
- Una dirección IP no indica por sí sola el papel de origen/destino.
- Un decimal entre 0 y 1 no demuestra que sea porcentaje, proporción, latencia o segundos.
- La longitud de un entero puede sugerir una escala de timestamp Unix, pero no debe decidirla sin contexto y un rango temporal plausible.
- Una columna llamada `size` no establece si se trata de bytes de archivo, mensaje, carga útil o paquetes.

Si faltan cabeceras, el adaptador puede reconocer un formato solo mediante una firma estructural suficientemente específica (por ejemplo, combinación de campos obligatorios de un formato conocido). Si la estructura no es única, se debe detener la interpretación automática y solicitar mapeo explícito. No inventar un rol para columnas anónimas.

### Conversión de unidades

Usar un subconjunto documentado de UCUM como representación interoperable de unidades. Las conversiones solo se permiten entre unidades de la misma dimensión y con una regla exacta. La unidad original y el valor de origen deben permanecer disponibles como procedencia.

- No interpretar `KB` como decimal o binario sin una convención declarada.
- No confundir bytes de capa IP con bytes de carga útil.
- No convertir duración a fecha ni frecuencia a contador.
- No redondear contadores enteros.
- No convertir porcentajes ambiguos entre 0–1 y 0–100 sin conocer la convención de la fuente.

## 7. Campos ausentes, desconocidos e inválidos

La capa debe distinguir semánticamente:

| Estado | Significado | Tratamiento |
|---|---|---|
| `not_reported` | La fuente no envió el campo | Mantener desconocido |
| `empty` | La columna existe, pero la celda está vacía | Mantener desconocido y reportar |
| `not_applicable` | El campo no corresponde a este evento | No exigir ni completar |
| `unsupported` | La fuente aporta un dato que aún no se interpreta | Mostrar como no mapeado |
| `invalid` | El valor no cumple tipo/rango/contrato | Rechazar ese registro o lote según atomicidad |
| `ambiguous` | Hay más de una interpretación válida | No normalizar automáticamente |
| `observed` | El valor fue informado y validado | Conservar, incluido el valor cero |

La ausencia de timestamp merece tratamiento específico: el instante de recepción no sustituye el instante de observación. Deben ser conceptos distintos (`received_at` y `observed_at`). Si el origen no aporta tiempo de observación y el caso de uso lo requiere, se rechaza o se importa como tiempo desconocido según el contrato; nunca se finge que ocurrió al momento de importar.

Los campos desconocidos se informan en el preview con nombre, cantidad de apariciones y sugerencias. Sus valores no se registran en logs ni se persisten por defecto, porque podrían contener tokens, datos personales o cargas útiles. El usuario podrá excluirlos o mapearlos de manera explícita. Los campos obligatorios no resueltos bloquean la importación.

## 8. Arquitectura y límites

Mantener un paquete pequeño y puro, sin acceso a FastAPI, SQLite ni red:

```text
src/netsentinel/semantics/
    models.py       # definiciones tipadas y estados de resolución
    catalog.py      # campos canónicos, alias y perfiles versionados
    resolver.py     # resolución exacta, sugerencias y conflictos
    normalize.py    # coerción y conversión de unidades explícitas
```

Los importadores continúan siendo adaptadores de formato:

- `activity_import_service.py` analiza CSV y solicita un plan de mapeo.
- `activity_zeek_import_service.py` interpreta TSV/JSONL Zeek y traduce nombres/unidades declarados por Zeek.
- `activity_event_service.py` sigue siendo la autoridad de validación del contrato de eventos de Actividad.
- Los dominios de Monitorización e Inventario incorporan el catálogo solo cuando sus tipos y contratos estén definidos; no deben compartir reglas de importación de Actividad.

Interfaz conceptual:

```python
plan = resolve_schema(
    headers,
    source_format="zeek_conn",
    source_version=detected_version,
    event_type="connection",
)

result = normalize_record(
    raw_record,
    plan=plan,
)

# result incluye:
# - valores canónicos validados
# - estado por campo
# - campos desconocidos y conflictos
# - reglas/versión del catálogo utilizadas
# - advertencias explicables
```

Es pseudocódigo de diseño, no una API implementada.

No crear una clase universal que incluya inventario, eventos, métricas, hallazgos y datos forenses. Compartir definiciones elementales y mantener los contratos de cada dominio.

## 9. Métricas, agregación y muestreo

Separar eventos de evidencia de mediciones de series temporales.

- **Eventos de seguridad, conexiones y auditoría:** no aplicar muestreo aleatorio o adaptativo a la evidencia que puede ser necesaria para investigar. Aplicar límites de tamaño, deduplicación, filtros explícitos y retención visible; no confundir esto con descartar observaciones.
- **Métricas tipo gauge:** conservar el significado del valor observado y agregar por ventana con conteo, mínimo, máximo y promedio cuando la agregación tenga sentido.
- **Contadores acumulativos:** calcular deltas y tasas solo con puntos consecutivos comparables; detectar resets, cambios de origen y huecos. No restar contadores de fuentes distintas.
- **Distribuciones/histogramas:** conservar buckets o estructura de distribución; no promediar percentiles ya calculados ni reconstruir p95 exacto desde un promedio.
- **Estados:** modelar transiciones y duración en estado; no promediarlos como si fueran magnitudes.

En una etapa posterior se pueden generar rollups por ventanas (por ejemplo, 10 s, 1 min y 5 min) con retención por resolución. La cardinalidad debe tener límites: IP, UID, URL completa, identificadores de sesión y valores libres permanecen en eventos/detalle, no se convierten automáticamente en dimensiones de todas las series métricas.

La frecuencia adaptativa de sondas no forma parte de la primera entrega. Antes debe demostrarse que no oculta interrupciones ni viola el intervalo configurado; cualquier ajuste futuro requiere límites, histéresis, estado observable y opción de control.

## 10. Rendimiento, seguridad y observabilidad

- Construir índices inmutables de alias una vez al cargar el catálogo. La resolución exacta debe ser búsqueda de diccionario, aproximadamente O(1) por cabecera.
- Ejecutar sugerencias fuzzy solo para nombres desconocidos, sobre candidatos del perfil y con límite explícito de candidatos; almacenar en caché resultados puros cuando sea útil.
- Mantener parsing en streaming y los límites actuales de tamaño/filas de importación; no introducir un proceso de inferencia por cada celda si el mapeo ya está resuelto por cabecera.
- Evitar expresiones regulares complejas sobre entradas no acotadas y conversiones costosas sobre cada registro.
- No enviar datos a servicios externos. No registrar valores originales sensibles, tokens ni payloads.
- La salida debe incluir códigos de advertencia estables, no mensajes internos ni trazas.
- Registrar métricas internas de calidad solo agregadas: campos mapeados, sugeridos, desconocidos, ambiguos y registros rechazados; no usar nombres/IP/UID como etiquetas de alta cardinalidad.

## 11. Plan de implementación y puertas de aceptación

### Fase A — catálogo y corpus de referencia

1. Inventariar campos actuales de Actividad, Zeek, inventario y monitorización.
2. Definir semántica, unidad, rol, tipo, opcionalidad y sensibilidad de cada campo.
3. Crear fixtures sanitizadas por formato y versiones conocidas.
4. Crear un corpus adversarial de typos, alias ambiguos, nombres confusables, columnas duplicadas, valores extremos y unidades contradictorias.

**Salida:** catálogo versionado, documentación de mapeos y pruebas sin cambio de runtime.

### Fase B — resolver determinista

1. Implementar normalización léxica y resolución por contexto.
2. Añadir sugerencias fuzzy sin autocorrección.
3. Detectar colisiones y duplicados contradictorios.
4. Devolver un plan de mapeo explicable por cabecera.

**Puerta:** exactitud total de alias explícitos, cero autocorrecciones fuzzy silenciosas y pruebas de ambigüedad/colisión.

### Fase C — adaptar CSV y Zeek

1. Migrar los alias existentes al catálogo sin cambiar formatos aceptados.
2. Conectar los adaptadores al resolver.
3. Extender preview para separar mapeado, sugerido, desconocido, ausente e inválido.
4. Mantener la normalización de dominio actual como última validación.
5. Preservar idempotencia, procedencia y comportamiento transaccional.

**Puerta:** mismas importaciones válidas anteriores, rechazos negativos conservados, cero cambios de significado y regresiones de duplicados/privacidad.

### Fase D — unidades y calidad transversal

1. Añadir unidades explícitas y conversiones comprobadas.
2. Incorporar métricas de calidad por fuente y campo.
3. Integrar gradualmente Monitorización e Inventario mediante contratos propios.
4. Exponer en interfaz la procedencia y limitaciones de las mediciones.

**Puerta:** equivalencia numérica demostrada, ausencia distinta de cero, unidades incompatibles rechazadas y cobertura de calidad visible.

### Fase E — agregación histórica

Diseñar rollups, retención por resolución y límites de cardinalidad solo después de disponer de mediciones reales y métricas de carga. No modificar tablas existentes ni muestrear evidencia como parte de las fases anteriores.

## 12. Matriz mínima de pruebas

- Alias canónico, alias de proveedor, camelCase, puntos, guiones, espacios, BOM y mayúsculas.
- Errores de una letra, transposición, alias ambiguos, similitud con otro campo y confusables Unicode.
- Dos columnas para un campo canónico con valores idénticos y contradictorios.
- IP válida/invalidada, MAC, timestamp ISO, timestamp Unix con unidad explícita y número sin unidad.
- Puerto dentro/fuera de rango; números que podrían significar bytes, paquetes o duración.
- Cero observado, vacío, nulo, ausente, no aplicable e inválido.
- Bytes IP frente a payload bytes; segundos frente a milisegundos; KB decimal frente a KiB binario.
- Cabeceras faltantes, archivos sin esquema, versiones desconocidas y campos obligatorios desconocidos.
- Archivos demasiado grandes, exceso de filas, claves JSON repetidas, importación duplicada y errores parciales.
- No persistencia de campos desconocidos sensibles ni exposición en errores/logs.
- Rendimiento medido en archivos cercanos al límite actual de importación.

## 13. Estándares estudiados y adaptación propia

- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/): vocabulario común para atributos de logs, métricas, trazas y recursos.
- [OpenTelemetry metric semantic conventions](https://opentelemetry.io/docs/specs/semconv/general/metrics/): tipos, unidades y convenciones de métricas.
- [Elastic Common Schema — Network](https://www.elastic.co/docs/reference/ecs/ecs-network), [Source](https://www.elastic.co/docs/reference/ecs/ecs-source), [Destination](https://www.elastic.co/docs/reference/ecs/ecs-destination): separación de extremos y semántica explícita de bytes/direcciones.
- [OCSF](https://github.com/ocsf/ocsf-schema) y [guía de conceptos](https://github.com/ocsf/ocsf-docs/blob/main/overview/understanding-ocsf.md): clasificación de eventos, atributos requeridos/recomendados/opcionales y extensibilidad.
- [UCUM 2.2](https://ucum.org/ucum): codificación inequívoca de unidades para intercambio electrónico.
- [Zeek conn.log](https://docs.zeek.org/en/lts/reference/logs/conn.html): definiciones de los campos de conexión; distingue bytes de payload y bytes a nivel IP.
- [Python difflib](https://docs.python.org/3/library/difflib.html): mecanismo estándar de comparación de secuencias; se considera solo como ayuda para sugerencias, no como autoridad semántica.

NetSentinel debe adoptar los conceptos que encajan y mantener su contrato interno pequeño. No copiar esquemas completos ni declarar compatibilidad formal con OTel, ECS u OCSF hasta implementar y probar sus mapeos.

## 14. Criterio de finalización

La capacidad estará lista para considerarse implementada cuando:

- los importadores compartan un catálogo único y versionado;
- las coincidencias exactas sean deterministas y los alias estén documentados;
- las sugerencias fuzzy no se conviertan en autocorrecciones silenciosas;
- las inferencias por valor no asignen roles semánticos ambiguos;
- ausencias, ceros, desconocidos e inválidos permanezcan diferenciados;
- las unidades y las agregaciones sean matemáticamente comparables;
- la procedencia permita explicar cada decisión;
- las pruebas cubran fuentes válidas y entradas adversariales;
- el rendimiento no degrade importaciones dentro de los límites soportados.

**La propuesta no habilita todavía un motor de inferencia en producción.** El primer incremento debe ser el catálogo y el resolver exacto con sugerencias, integrado sin cambios de esquema ni pérdida de compatibilidad.
