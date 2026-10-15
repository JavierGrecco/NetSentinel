# Arquitectura de NetSentinel

NetSentinel sigue siendo una aplicación local de una sola instalación: el servidor FastAPI sirve el panel y la API en `127.0.0.1`, y SQLite conserva el inventario y el historial. La extensión del navegador es un cliente opcional; no es un proceso del servidor.

## Cómo está organizado hoy

- **Composición y API:** `main.py` crea la aplicación, configura los controles transversales y registra los routers. `api/inventory.py` compone tres routers: `api/inventory_assets.py` para consulta y cambios de activos/eventos, `api/inventory_discovery.py` para descubrimiento bajo demanda y `api/inventory_exports.py` para exportaciones; `api/activity.py` compone `api/activity_read.py` (consulta/exportación), `api/activity_sessions.py` (sesiones e ingreso), `api/activity_import.py` (importación CSV), `api/activity_deletion.py` (borrado selectivo) y `api/activity_retention.py` (retención), con contratos compartidos en `api/activity_models.py`; `api/monitoring.py` compone tres routers: `api/monitoring_monitors.py` para gestión de monitores, incidentes y notificaciones; `api/monitoring_reports.py` para resúmenes y exportaciones; y `api/diagnostics.py` para diagnóstico puntual; `api/pages.py` sirve las cinco páginas HTML locales; `api/findings.py` atiende hallazgos; `api/tools.py` compone `api/tools_dns.py` (configuración y consultas DNS) y `api/tools_tls.py` (inspección TLS puntual). `findings_service.py` coordina la consulta de evidencia sin depender del transporte HTTP.
- **Persistencia:** `database.py` es una fachada de compatibilidad; `database_storage.py` mantiene conexiones y permisos; `database_schema.py` es responsable del esquema y las migraciones aditivas; `inventory_repository.py` conserva las escrituras del inventario y sirve de fachada para `inventory_read_repository.py` (listado, direcciones, historial y exploraciones) y `inventory_repository_support.py` (normalización compartida de filas y orden de IP). `record_scan` mantiene una sola transacción para la exploración, los dispositivos, direcciones, observaciones y eventos asociados; `events_repository.py` posee las consultas de eventos generales. `monitoring_repository.py` es la fachada histórica de cuatro repositorios: `monitoring_config_repository.py` (CRUD de monitores), `monitoring_analytics_repository.py` (lecturas y métricas), `monitoring_state_repository.py` (checks y transiciones incidentes/eventos) y `monitoring_notifications_repository.py` (registro de avisos). `dashboard_repository.py` contiene el resumen transversal, y las exportaciones se mantienen en servicios de solo lectura. Los tipos compartidos de observación viven en `network_models.py`, sin hacer que la persistencia dependa del motor de descubrimiento.
- **Actividad:** la validación de dominios y hosts se unifica después de IDNA y aplica los límites DNS antes de guardar datos. `api/activity.py` conserva el punto de composición; `api/activity_models.py` define los contratos HTTP compartidos y los subrouters quedan agrupados por flujo. `activity_catalog.py` mantiene el catálogo de eventos y fuentes; `activity_privacy.py` sanea dominios, URLs y direcciones de correo; `activity_event_service.py` valida y normaliza eventos sin tocar SQLite; `activity_session_service.py` gestiona tokens de recopilación e ingestión autorizada; `activity_retention_service.py` centraliza el reloj UTC, la normalización temporal y la aplicación de retención; `activity_filters.py` valida filtros sin abrir la base de datos; `activity_import_service.py` valida cabeceras y filas CSV y arma la vista previa; `activity_read_service.py` compone las consultas del panel y genera el CSV seguro; `activity_deletion_service.py` coordina la vista previa y el borrado selectivo con confirmación exacta; `activity_tracking.py` mantiene la fachada compatible para las rutas existentes; el control de arquitectura declara sus dependencias permitidas y evita que la fachada acceda directamente a SQLite o a módulos ajenos; `activity_repository.py` conserva una fachada compatible sobre repositorios separados para retención, sesiones, importaciones, borrado y lectura. `activity_repository_support.py` reúne las comprobaciones compartidas. El detalle está en [ACTIVITY_PERSISTENCE.md](ACTIVITY_PERSISTENCE.md). Los contratos HTTP y el formato CSV existente se conservan.
- **Red y diagnóstico:** módulos separados atienden descubrimiento local, vecinos, DNS, TLS y fabricantes. DNS y TLS validan los nombres también después de IDNA; DNS comprueba además la respuesta PTR antes de exponerla; las consultas DNS y la inspección TLS aíslan el resolvedor en procesos terminables para no dejar un worker bloqueado indefinidamente. En TLS, la conexión TCP y el handshake comparten un plazo monotónico de hasta tres segundos; un límite externo terminable contempla también un posible bloqueo del resolvedor del sistema y permite hasta un segundo de margen para arrancar el proceso hijo y devolver JSON. `diagnostics.py` coordina sondas explícitas y acotadas; `diagnostics_assessment.py` convierte sus resultados en explicaciones y pasos prudentes sin depender de comandos del sistema.
- **Monitorización y hallazgos:** `monitoring.py` conserva el supervisor y la coordinación de comprobaciones; `monitoring_validation.py` valida objetivos sin efectos de red; `monitoring_probe.py` implementa las sondas acotadas; `monitoring_notifications.py` se ocupa del envío opcional de webhooks. Las operaciones de SQLite se distribuyen entre repositorios de configuración, lecturas analíticas, estado y notificaciones; `monitoring_repository.py` conserva los nombres históricos como fachada. `monitoring_state_repository.py` mantiene el check, la actualización del monitor, la apertura/cierre del incidente y el evento asociado dentro de una transacción. Los CSV permanecen en `monitoring_export_service.py`. La presentación normalizada de hallazgos tiene su servicio propio.
- **Interfaz:** cada pantalla mantiene su HTML, sus estilos y su JavaScript en archivos separados; los scripts se sirven desde `/static/`. La extensión vive en `browser-extension/`.

La separación por archivos ya existe, pero no todas las fronteras representan responsabilidades completas. La API y la persistencia concentran varios dominios, y las rutas conocen detalles de servicios y almacenamiento. Al crecer las fuentes de evidencia, esa estructura puede hacer que un cambio de una función afecte a otras que no deberían depender de ella.

## Mantenimiento de la interfaz

Cada vista tiene un archivo HTML para la estructura y un JavaScript propio para su comportamiento:

| Vista | HTML | JavaScript |
| --- | --- | --- |
| Inventario | `static/index.html` | `static/index.js` |
| Monitorización | `static/monitors.html` | `static/monitors.js` |
| Actividad | `static/activity.html` | `static/activity.js` |
| Hallazgos | `static/findings.html` | `static/findings.js` |
| Herramientas | `static/tools.html` | `static/tools.js` |

Los HTML cargan el archivo correspondiente con `defer`. Así el navegador termina de leer la página antes de ejecutar el código y no hace falta insertar bloques JavaScript dentro del HTML. Los archivos se sirven desde el mismo origen, permitido por la política CSP; no se habilita `unsafe-inline`.

Al modificar una pantalla, cambiá su archivo JavaScript salvo que también necesites cambiar la estructura o los estilos. Si agregás un recurso nuevo, verificá que esté incluido en `pyproject.toml`, en la comprobación de archivos del wheel y en la validación de sintaxis de CI. Las pruebas HTTP comprueban que la página y su script se sirven con las cabeceras defensivas habituales.

## Dirección propuesta

La decisión de arquitectura se documenta en [ADR-001: aplicación modular de despliegue único](ADR-001-MODULAR-MONOLITH.md). El término *monolito* describe aquí cómo se instala y ejecuta el producto, no el tamaño interno de sus módulos: cada módulo debe ser cohesionado, tener una interfaz pública pequeña y proteger sus detalles privados. La meta es separar responsabilidades sin cambiar la instalación local.

| Módulo | Responsabilidad principal | No debería hacer |
| --- | --- | --- |
| **API y presentación** | Validar entradas, aplicar el contrato HTTP y traducir errores a respuestas claras | Ejecutar SQL o contener reglas de negocio |
| **Inventario y descubrimiento** | Gestionar activos, observaciones de red, direcciones, procedencia y cambios | Decidir por sí solo que un activo es malicioso |
| **Monitorización** | Definir controles, ejecutar comprobaciones, registrar transiciones e incidentes | Consultar directamente las tablas internas de otros dominios |
| **Actividad** | Administrar sesiones autorizadas, metadatos recibidos, privacidad, saneamiento, retención e importación/exportación | Recopilar contenido de mensajes, credenciales o cuerpos HTTP |
| **Herramientas de red** | Encapsular las consultas DNS/TLS y diagnósticos puntuales, con límites y timeouts | Iniciar sondeos arbitrarios o guardar datos sin política explícita |
| **Hallazgos** | Unificar evidencia, explicar procedencia, límites y grado de certeza | Inventar señales, elevar confianza sin evidencia o convertirse en dueño de los datos de origen |
| **Persistencia SQLite** | Gestionar conexiones, transacciones, versión del esquema y consultas por dominio | Convertirse en una capa global de reglas de negocio |

Estos límites son una dirección de diseño, no una afirmación de que todas las carpetas o interfaces ya estén implementadas.

## Reglas verificadas automáticamente

El script `scripts/check_architecture_boundaries.py` se ejecuta en CI y comprueba que no haya ciclos de importación, definiciones de nivel superior duplicadas que se oculten entre sí, que cada router declare sus dependencias permitidas y que los servicios/repositorios con dependencias internas tengan una lista explícita. También fija una allowlist para la fachada `activity_tracking.py`: puede delegar en los servicios y utilidades de Actividad, pero no importar directamente `database.py` ni el repositorio. La persistencia solo puede importar un conjunto pequeño y declarado de apoyos compartidos: `config.py` para la ubicación del archivo de datos, `csv_safety.py` para exportaciones seguras, `network_models.py` para el contrato de vecinos y `vendor.py` para consultar la base OUI local sin red. Cualquier otro módulo interno requiere una decisión explícita. Además, todo módulo nuevo fuera de la API y del punto de composición se revisa automáticamente para evitar dependencias de FastAPI o Starlette. Estas reglas refuerzan las fronteras implementadas, pero no significan que todo el backend ya esté desacoplado.

## Cómo se comunican los módulos

- Dentro del proceso, un módulo ofrece servicios de aplicación con entradas y salidas tipadas. Los demás módulos usan esa interfaz pública; no importan funciones internas ni escriben las tablas ajenas.
- Las fronteras siguen capacidades funcionales y reglas de negocio, no una carpeta por cada función ni una capa técnica genérica que mezcle todos los dominios.
- Los paquetes internos no se invocan entre sí mediante HTTP: los límites en memoria usan interfaces tipadas. La comunicación de red se reserva para clientes o procesos realmente separados.
- Las dependencias deben formar un grafo dirigido sin ciclos. La composición conecta las piezas; la lógica de dominio no debe importar FastAPI ni conocer el transporte HTTP.
- Cada dominio es responsable de sus operaciones de persistencia, aunque inicialmente todos utilicen la misma SQLite. Compartir motor no significa compartir la propiedad de las consultas internas.
- Los routers HTTP traducen solicitudes a llamadas de servicio. No hacen llamadas HTTP entre sí.
- El panel, la CLI y la extensión usan los contratos públicos que les corresponden. La extensión sigue siendo opt-in y usa los endpoints de actividad previstos para ella.
- Las fuentes variables —por ejemplo, tablas de vecinos del sistema o futuras integraciones de router— se conectan mediante adaptadores pequeños. Solo se generaliza una interfaz cuando existe una necesidad concreta de soportar más de una implementación.
- La evidencia compartida lleva procedencia y hora, y conserva la diferencia entre dato observado e interpretación.

## Catálogo de errores y diario local

La clasificación y el almacenamiento son responsabilidades distintas. `error_reporting.py` asigna códigos estables, mensajes y acciones sugeridas sin devolver el texto crudo de una excepción. `error_journal.py` se ocupa del archivo JSONL local, los campos permitidos, los límites de tamaño y la rotación.

Los manejadores HTTP siguen importando `record_error_event` desde `error_reporting.py`; esa fachada se conserva para no cambiar los contratos internos. El diario solo depende de `config.py` para conocer la ubicación de los datos. El control de arquitectura verifica esta frontera y evita que el módulo de persistencia importe dominios ajenos.

Al cambiar el formato del registro, sus límites o sus permisos, actualizá `tests/test_error_journal.py` y la guía de seguridad. Las pruebas deben confirmar que no se guardan cuerpos de solicitud ni campos que no formen parte de la lista permitida, y que un fallo de escritura se informa como tal.

## Límites de seguridad y privacidad

La app continúa enlazada a loopback y usa SQLite local. La modularización no justifica abrir la API a la red, añadir telemetría externa, capturar contenido sensible, cambiar la configuración del router ni activar automáticamente la extensión. Cada nueva fuente debe tener alcance, autorización, límite de tiempo, tratamiento de errores, política de retención y forma de desactivación documentados.

## Migración y pruebas

La reorganización será incremental y deberá preservar el contrato visible. Antes de mover consultas o cambiar tablas, hay que formalizar la versión del esquema SQLite y probar migraciones, copias de seguridad, importación y restauración. Las rutas actuales, formatos exportados, encabezados de seguridad, protección de origen y respuestas de error se cubren con pruebas de contrato.

No se considera terminada una extracción solo porque el código haya cambiado de archivo: debe reducir acoplamiento, mantener compatibilidad y demostrarlo con pruebas. El plan gradual y sus criterios de aceptación están en [ADR-001](ADR-001-MODULAR-MONOLITH.md) y en el [roadmap](ROADMAP.md).

## Pruebas actuales

Las pruebas automatizadas usan datos sintéticos y no requieren una red real. GitHub Actions valida la instalación y la suite de pruebas en Windows, macOS y Ubuntu con distintas versiones de Python. Las comprobaciones automatizadas no sustituyen la validación manual de sistemas y navegadores reales descrita en la matriz de validación.


La composición de FastAPI se mantiene en `main.py`. El middleware y las reglas de host/origen viven en `api/security.py`; las cabeceras defensivas, la CSP y las respuestas de error correlacionadas están en `api/security_headers.py`. `api/validation_errors.py` prepara las respuestas 422 sin reflejar valores enviados; `api/error_handling.py` mantiene los manejadores de excepciones HTTP y fallos inesperados, y reexporta el manejador de validación para conservar el punto de registro histórico. La API de seguridad conserva los nombres históricos como reexportaciones para no cambiar el arranque ni los puntos de prueba existentes.


### Persistencia por responsabilidad

| Módulo | Para qué sirve | Qué no debe absorber |
| --- | --- | --- |
| `database.py` | Mantener la API interna histórica y delegar operaciones | SQL nuevo o reglas de negocio |
| `database_storage.py` | Abrir/cerrar conexiones y proteger el archivo | SQL de negocio y cambios de esquema |
| `database_schema.py` | Crear tablas, índices y migrar versiones anteriores dentro de una transacción | Consultas de inventario o reglas de negocio |
| `inventory_repository.py` | Mantener la fachada histórica y las escrituras transaccionales del inventario | Acumular consultas de lectura o generar estadísticas de otros dominios |
| `inventory_read_repository.py` | Consultar activos, direcciones, historial y exploraciones sin efectos de escritura | Alterar el inventario |
| `inventory_repository_support.py` | Normalizar filas del inventario y ordenar direcciones IP con reglas compartidas | Abrir conexiones SQLite o aplicar cambios de estado |
| `events_repository.py` | Crear, listar y reconocer eventos del sistema | Reglas de sesión de navegador o lógica de checks |
| `monitoring_repository.py` | Mantener las funciones históricas como fachada | Implementar nuevas consultas/escrituras o reglas de negocio |
| `monitoring_config_repository.py` | Crear, listar, editar y eliminar monitores | Calcular métricas de ventanas históricas |
| `monitoring_analytics_repository.py` | Leer comprobaciones, incidentes y métricas agregadas | Cambiar el estado de incidentes |
| `monitoring_state_repository.py` | Guardar checks y transiciones de incidentes/eventos atómicamente; limpiar el historial de checks | Separar una transición en varias transacciones |
| `monitoring_notifications_repository.py` | Registrar intentos y resultados de avisos | Enviar webhooks o construir exportaciones |
| `dashboard_repository.py` | Consultar el resumen que combina indicadores de distintos dominios | Convertirse en repositorio de escritura de cada dominio |
| `data_export_service.py` / `monitoring_export_service.py` | Producir exportaciones seguras y copias consistentes | Modificar las tablas de origen |

Las tablas y migraciones siguen juntas en `database_storage.py` en esta etapa: cambiarlas de sitio a la vez que las consultas elevaría demasiado el riesgo para los datos existentes. Se revisará esa frontera por separado después de consolidar la extracción de consultas y conservar pruebas de migración/backup.
