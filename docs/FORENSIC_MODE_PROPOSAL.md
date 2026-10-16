# Propuesta: análisis forense digital en NetSentinel

**Estado:** propuesta de alcance; no es una función implementada ni una certificación forense.  
**Objetivo:** decidir si NetSentinel puede sumar un módulo útil para examinar evidencia digital con un flujo reproducible, preservación verificable y límites claros.

## Resumen ejecutivo

NetSentinel nació para observar una red local, descubrir dispositivos y registrar metadatos de actividad procedentes de fuentes autorizadas. Eso no equivale a adquirir ni analizar forénsicamente el disco de una computadora.

Si queremos cubrir un equipo incautado, la recomendación es crear un **módulo de casos y análisis forense separado**. Debe trabajar sobre imágenes forenses verificadas o copias de trabajo y resultados importados desde herramientas especializadas. No debería arrancar intentando reemplazar las herramientas que adquieren discos, descifran artefactos protegidos o recuperan archivos borrados.

La prioridad no es recolectar la mayor cantidad posible de datos. Es poder explicar qué se obtuvo, de qué fuente, con qué herramienta y versión, cómo se preservó, qué transformación se aplicó y qué limitaciones tiene cada resultado.

## Principios no negociables

1. **Autoridad y alcance documentados.** Cada caso identifica quién lo solicita, quién está autorizado, el objetivo y las categorías de datos permitidas. La aplicación no decide si una incautación autoriza analizar cualquier cuenta o contenido.
2. **Separar original, adquisición y copia de análisis.** La adquisición debe realizarse con procedimientos y herramientas adecuados al dispositivo. El análisis posterior se ejecuta sobre una copia de trabajo verificada; el módulo no debe escribir en la evidencia original.
3. **Integridad comprobable.** Guardar SHA-256 (y permitir algoritmos adicionales si un laboratorio los exige) de cada imagen o archivo incorporado, tamaño, hora de incorporación, herramienta/versión, operador y resultado de verificación. Calcular hashes otra vez al verificar copias. Un hash aislado no demuestra por sí mismo una cadena de custodia completa.
4. **Registro de custodia.** Registrar recepción, traslados, accesos, creación de copias, verificaciones, exportaciones y cualquier incidente. Los registros deben llevar hora con zona horaria, actor y motivo; las correcciones se agregan como nuevas entradas, no se sobrescribe silenciosamente el historial.
5. **Trazabilidad por artefacto.** Cada fila del resultado debe señalar el archivo o imagen de origen, ruta/perfil, identificador de registro u offset cuando corresponda, herramienta/parser y versión, campos originales, normalización aplicada y advertencias.
6. **No confundir indicios con conclusiones.** Una URL, nombre de usuario, IP, archivo o marca de tiempo no prueba por sí solo quién actuó ni la intención. Diferenciar dato observado, dato derivado, hipótesis y conclusión del examinador.
7. **Minimización y privacidad.** Recoger solo lo autorizado y relevante. Contraseñas, cookies de sesión, tokens, claves privadas y otros secretos no deben aparecer en claro en paneles, índices de búsqueda, exportaciones normales ni reportes.
8. **Herramientas validadas.** Antes de usarlas en casos reales, comprobar los resultados con conjuntos sintéticos/conocidos, documentar fallos y limitaciones y repetir la validación ante cambios significativos de versión.

Estos principios siguen las guías de SWGDE para recogida, adquisición y examen de evidencia, las recomendaciones para probar herramientas forenses y la guía de NIST sobre técnicas forenses integradas al manejo de incidentes. Las políticas aplicables y la autoridad legal deben confirmarse con el organismo y su asesoría jurídica.

## Qué categorías podrían analizarse

| Categoría | Ejemplos de artefactos | Utilidad | Cautelas |
|---|---|---|---|
| Navegadores | Historial, búsquedas registradas, descargas, marcadores, sesiones/pestañas, caché, extensiones y su configuración | Construir una línea de tiempo de navegación y descargas | El historial puede faltar, haberse borrado, sincronizarse o pertenecer a perfiles distintos. Una búsqueda puede registrarse en la URL o en una base separada, según navegador y versión. |
| Otros datos del navegador | Autocompletado, preferencias, permisos de sitios, almacenamiento local y cookies | Dar contexto técnico a una actividad observada | Pueden contener información privada o tokens de sesión. Por defecto mostrar solo presencia, metadatos minimizados y referencias, nunca secretos en claro. |
| Sistema operativo | Cuentas y eventos de inicio de sesión, logs de seguridad, dispositivos USB, archivos recientes, accesos directos, programas instalados y cuarentena | Contextualizar uso del equipo, medios conectados y eventos de sistema | Las fuentes dependen del sistema operativo, configuración, retención y permisos. |
| Ejecución y persistencia | Registros de ejecución disponibles, servicios, tareas programadas, elementos de inicio, extensiones y aplicaciones instaladas | Investigar posibles programas ejecutados o mecanismos de inicio | Ningún artefacto aislado confirma ejecución o actividad maliciosa; validar semántica y versión del sistema. |
| Archivos y metadatos | Rutas, fechas, tamaño, tipo, hashes, metadatos de documentos e imágenes y archivos relevantes | Buscar grupos de documentos y establecer relaciones temporales | Las fechas pueden copiarse, manipularse o interpretarse de forma distinta. El análisis de eliminados o espacio no asignado requiere herramientas forenses probadas. |
| Correo y mensajería | Fechas, emisores/destinatarios, asunto, identificadores, rutas de almacenamiento, adjuntos y sus hashes, cuando estén autorizados | Correlacionar comunicaciones con eventos y documentos | Contenido y metadatos son datos sensibles; formatos, cifrado y sincronización hacen que la cobertura dependa de cada aplicación. No prometer un recolector universal. |
| Red y seguridad | Logs de DNS, router, firewall, VPN, EDR, DHCP, conexiones, alertas y capturas existentes | Relacionar el equipo con infraestructura o actividad observada | Los registros pueden estar incompletos; NAT, VPN, DNS cifrado, relojes y retención limitan la atribución. NetSentinel no debe presentar metadatos como contenido HTTPS. |
| Actividad en nube | Exportaciones de auditoría o registros suministrados legalmente por el proveedor | Vincular sesiones, cambios o accesos con tiempos locales | Es una fuente separada, con su propia autoridad, alcance, integridad y retención; no asumir acceso a cuentas por tener el equipo. |
| Memoria y estado volátil | Procesos, conexiones abiertas, sesiones activas o una adquisición de memoria efectuada por especialistas | Puede conservar contexto que desaparece al apagar o cerrar el equipo | Requiere una decisión temprana de un especialista: la adquisición en vivo cambia el estado del sistema y debe documentarse. |

## Navegadores: propuesta de cobertura

En la primera etapa, priorizar artefactos de navegadores y perfiles que puedan exportarse o adquirirse de forma verificable:

- **Chromium:** Chrome, Edge, Brave, Opera y otros navegadores de esa familia, a medida que se compruebe la compatibilidad real. No dar por supuesto que todos tienen la misma ruta, esquema o protección de datos.
- **Firefox:** historial, descargas, marcadores, datos de formularios y cookies a partir del perfil y los archivos correspondientes.
- **Safari:** tratarlo como una integración diferenciada del ecosistema macOS, con adquisición y análisis adaptados al sistema, versiones y protecciones de Apple.

El primer conjunto de resultados de navegador debería incluir historial y tiempos de visita, búsquedas cuando estén disponibles, descargas, marcadores, perfiles detectados, sesiones y extensiones. Después se pueden sumar caché, autocompletado y otros artefactos específicos. Cada parser debe indicar si un elemento no existe, está cifrado/no disponible, está dañado, no es compatible o simplemente no se encontró.

### Contraseñas, cookies y secretos

Las contraseñas guardadas pueden ser relevantes en una investigación autorizada, pero **no recomiendo que NetSentinel extraiga ni muestre contraseñas en texto claro**. Firefox, por ejemplo, mantiene datos de inicios de sesión cifrados y una base de claves separada; otros navegadores dependen del sistema operativo y de protecciones que cambian entre versiones.

Como alcance inicial, NetSentinel debería informar que encontró un almacén protegido, qué perfil y navegador lo contienen, qué herramienta validada lo identificó y si el material estaba disponible para el parser. Los secretos en sí permanecen fuera del índice normal y del informe. Si una investigación necesita acceder a ellos, el laboratorio deberá usar un procedimiento especializado y autorizado, en un entorno segregado, con acceso auditado y sin replicar el secreto en la base de casos.

La misma regla aplica a cookies de sesión, tokens, credenciales de API, claves privadas y datos de autenticación en almacenamiento local.

## Herramientas externas evaluadas como candidatas

| Herramienta | Papel potencial | Recomendación para NetSentinel |
|---|---|---|
| **Autopsy + The Sleuth Kit** | Plataforma existente para casos, imágenes de disco, sistemas de archivos y artefactos; su módulo de integridad puede verificar hashes o calcularlos cuando faltan | Candidato principal para adquisición/análisis general. Al principio, importar manifestaciones y resultados autorizados; no intentar reemplazar su motor forense. |
| **Hindsight** | Parser especializado en artefactos de navegador Chromium y Firefox; correlaciona registros en una línea de tiempo | Candidato para adaptador de análisis de navegadores, sujeto a revisión de licencia, compatibilidad por versión, tratamiento de secretos y pruebas sobre conjuntos conocidos. No mostrar contraseñas o tokens que el parser pueda identificar. |
| **Velociraptor, colecciones offline** | Recolección definida de artefactos en un sistema operativo en ejecución, con salida portable y opciones de protección del archivo | Útil para escenarios de recolección viva autorizada y respuesta a incidentes. No es sustituto de una imagen de disco apagado; cualquier ejecución local puede alterar el sistema y debe quedar documentada. |
| **Herramientas de adquisición específicas del laboratorio** | Imágenes forenses, adquisición de medios, memoria, móviles o formatos de proveedor | Mantener como responsabilidad de examinadores y herramientas especializadas. NetSentinel debería verificar e importar resultados, no improvisar funciones de adquisición críticas. |

La elección definitiva requiere revisar licencias y dependencias, formatos de entrada/salida, mantenimiento, plataformas, procedencia de los datos, controles de secretos y resultados de pruebas independientes o internas. Los nombres de herramientas en esta tabla son candidatos, no una certificación de su validez para cada caso.

## Arquitectura recomendada

Mantener separados los dos usos del producto:

- **NetSentinel Red:** inventario local, monitorización, diagnóstico y metadatos de red autorizados.
- **NetSentinel Forense (propuesta):** casos, evidencia, manifiestos, verificación, importación de artefactos, línea de tiempo y reportes reproducibles.

Se pueden compartir diseño visual, componentes de tabla, filtros y generación de reportes. No se deberían compartir sin límites las bases de datos ni la retención entre la monitorización diaria y los casos forenses. Una base de caso necesita identidad propia, control de acceso, copias, retención, exportación y auditoría independiente.

### Primera entrega viable

1. Abrir un caso con identificador, solicitante, examinador, alcance y zona horaria.
2. Incorporar una imagen forense o un paquete exportado sin tocar el original; registrar tamaño, tipo, hashes y manifiesto.
3. Verificar que una copia coincide con su manifiesto antes del análisis y volver a verificarla cuando corresponda.
4. Importar resultados exportados por una herramienta forense validada, guardando fuente, hashes, versión y avisos.
5. Construir una línea de tiempo unificada sin eliminar el valor original del timestamp ni ocultar conversiones horarias.
6. Buscar y filtrar artefactos, abrir la procedencia de cada resultado y distinguir hechos observados de datos normalizados.
7. Generar un reporte reproducible con alcance, fuentes, hashes, procedimientos, versiones, resultados, limitaciones y anexos.

No incluiría en esa primera entrega: descifrado de contraseñas, extracción masiva de cookies/tokens, bypass de cifrado, recuperación propia de espacio no asignado, adquisición de memoria, extracción móvil ni recolección silenciosa remota. Son capacidades de mayor riesgo y complejidad, que requieren validación y procesos específicos antes de considerarlas.

## Pruebas que deben existir antes de usarlo con evidencia real

- Casos sintéticos con resultados esperados, diferentes zonas horarias, cambios de horario estacional y relojes incorrectos.
- Perfiles de varios navegadores, versiones, perfiles múltiples, artefactos ausentes, bases SQLite dañadas y registros parcialmente recuperables.
- Verificación de hash con casos correctos e intencionalmente modificados.
- Comprobación de que importar o visualizar no escribe en el original; registrar toda operación inevitable sobre una fuente en vivo.
- Repetición del análisis con la misma herramienta, versión y entradas, comparando resultados.
- Pruebas de datos sensibles en logs, informes, errores y exportaciones.
- Validación documentada de cada herramienta/adaptador antes de actualizaciones significativas.

No afirmar que un programa es “forense” o que sus resultados serán aceptados judicialmente solo por generar hashes y reportes. El laboratorio debe validar herramientas, procedimientos, personal y cumplimiento de las reglas del organismo y jurisdicción.

## Referencias para profundizar

1. [NIST SP 800-86 — Guide to Integrating Forensic Techniques into Incident Response](https://www.nist.gov/publications/guide-integrating-forensic-techniques-incident-response).
2. [SWGDE — Best Practices for Digital Evidence Collection, versión 2.0 (2025)](https://www.swgde.org/documents/published-complete-listing/18-f-002-2-0/).
3. [SWGDE — Best Practices for Computer Forensic Acquisition, versión 2.1 (2025)](https://www.swgde.org/documents/published-complete-listing/17-f-002-2-1/).
4. [SWGDE — Best Practices for Computer Forensic Examinations, versión 2.0 (2025)](https://www.swgde.org/documents/published-complete-listing/18-f-001-2/).
5. [SWGDE — Best Practices Apple macOS Forensic Acquisition](https://www.swgde.org/documents/published-complete-listing/23-f-005-swgde-best-practices-apple-macos-forensic-acquisition/).
6. [SWGDE — Minimum Requirements for Testing Tools Used in Digital and Multimedia Forensics, versión 2.1](https://www.swgde.org/documents/published-complete-listing/18-q-001-minimum-requirements-for-testing-tools-used-in-digital-and-multimedia-forensics/).
7. [SWGDE — Requirements for Report Writing in Digital and Multimedia Forensics](https://www.swgde.org/documents/published-complete-listing/18-q-002-swgde-requirements-for-report-writing-in-digital-and-multimedia-forensics/).
8. [Autopsy — Web Artifact Analysis](https://sleuthkit.org/autopsy/web_artifacts.php) y [Data Source Integrity Module](https://www.sleuthkit.org/autopsy/docs/user-docs/4.17.0/data_source_integrity_page.html).
9. [Hindsight — Browser forensics](https://github.com/obsidianforensics/hindsight).
10. [Velociraptor — Offline Collections](https://docs.velociraptor.app/docs/deployment/offline_collections/).
11. [Mozilla — Archivos importantes de los perfiles de Firefox](https://support.mozilla.org/es/kb/about-your-important-data-and-their-files).

Las guías SWGDE y NIST describen prácticas generales y limitaciones; no sustituyen la autorización legal, los procedimientos del laboratorio ni el asesoramiento jurídico aplicable al caso concreto.

## Decisión pendiente

Antes de escribir recolectores, conviene validar tres decisiones:

1. Que el objetivo inicial sea **analizar evidencia ya adquirida**, no hacer adquisiciones forenses completas desde NetSentinel.
2. Que la primera integración de navegador use artefactos de prueba y resultados de Hindsight/Autopsy u otros exportadores validados, con secretos excluidos por defecto.
3. Que la custodia y los informes formen el cimiento del módulo, antes de ampliar la lista de artefactos.

Hasta tomar esas decisiones, esta documentación es una propuesta. No implica que NetSentinel ya tenga capacidades forenses ni que pueda examinar dispositivos incautados de manera validada.
