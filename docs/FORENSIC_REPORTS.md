# Informes de examen en NetSentinel Forense

## Qué genera la aplicación

NetSentinel crea un **borrador de informe de examen**, versionado e inmutable, basado en una captura del expediente del caso. El borrador contiene:

- Identificador y versión del informe, caso y referencia de autoridad registrada.
- Fecha de solicitud, solicitante y organización solicitante.
- Propósito y alcance realmente realizado.
- Organización examinadora y autor declarados.
- Elementos de evidencia y comprobaciones que figuran en la captura base, con sus metadatos y estado de la cadena de auditoría.
- Procedimientos realizados, resultados, conclusiones y su fundamento cuando corresponda, limitaciones, desviaciones y material de apoyo declarado.
- Disposición de originales y derivados.
- Referencia y digest SHA-256 del expediente base, digest SHA-256 del informe y un estado claro de autorización.

El informe se exporta como JSON autocontenido y como Markdown legible. El archivo JSON se puede verificar en el entorno donde se instaló NetSentinel:

    python -m netsentinel.forensics_report ruta/al/informe.json

El comando valida el digest del informe y el expediente base incluido. Una modificación del documento invalida la comprobación si no se recalculan los digests. Un digest calculado por el propio archivo no es una firma digital ni demuestra quién creó el informe.

## Versiones y enmiendas

La primera entrega crea la versión V1. Los informes guardados no se pueden editar ni borrar desde la aplicación. Para corregirlos se crea una nueva versión que referencia la versión más reciente e incluye un motivo de enmienda. La anterior permanece disponible para comparar el historial. El evento de creación se agrega a la auditoría encadenada; la captura base dentro del informe representa el expediente en el momento en que se generó esa versión.

Si la auditoría de esa captura tiene faltantes o alteraciones, el informe conserva y muestra el estado observado. No intenta reparar la cadena ni declara válido lo que no lo está.

## Lo que este borrador no significa

- No está firmado ni autorizado automáticamente, aunque incluya un nombre declarado de autor o autorizador.
- No autentica identidades, competencias, firmas o la autoridad de una solicitud.
- No reemplaza las notas de examen, los registros de herramientas especializadas, anexos ni los procedimientos de la organización.
- No adquiere discos o dispositivos y no convierte un hash informado en prueba de autenticidad.
- No demuestra por sí solo que la base local no haya sido alterada fuera de la aplicación.

La versión actual cubre la estructura del informe, el snapshot del expediente, la trazabilidad de cambios y la verificación de integridad. Antes de usarlo como informe oficial se requiere, como mínimo, identidad autenticada, revisión independiente, autorización/firma verificable, y la información institucional/jurisdiccional que corresponda.

## Referencia técnica

SWGDE, *Requirements for Report Writing in Digital and Multimedia Forensics*, documento 18-Q-002-1.0, define requisitos mínimos de informe como identificador de caso y solicitante, propósito, procesos y resultados, conclusiones con base si se incluyen, disposición de evidencias y autorización del informe: https://www.swgde.org/documents/published-complete-listing/18-q-002-swgde-requirements-for-report-writing-in-digital-and-multimedia-forensics/

Esta referencia sirve como orientación técnica. No supone aprobación, certificación ni respaldo de SWGDE a NetSentinel.
