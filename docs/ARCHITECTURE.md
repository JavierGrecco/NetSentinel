# Arquitectura de NetSentinel

NetSentinel sigue siendo una aplicación local de una sola instalación: el servidor FastAPI sirve el panel y la API en `127.0.0.1`, y SQLite conserva el inventario y el historial. La extensión del navegador es un cliente opcional; no es un proceso del servidor.

## Cómo está organizado hoy

- **Composición y API:** `main.py` crea la aplicación y sus controles transversales. Los routers `api/activity.py`, `api/findings.py` y `api/tools.py` agrupan actividad autorizada, hallazgos y herramientas DNS/TLS. `findings_service.py` coordina la consulta de evidencia para los hallazgos sin depender del transporte HTTP.
- **Persistencia:** `database.py` contiene conexiones, inicialización del esquema y consultas de varios dominios. Los tipos de observación que comparten descubrimiento e inventario se definen en `network_models.py`, sin hacer que la persistencia dependa del motor de descubrimiento.
- **Actividad:** `api/activity.py` define los contratos HTTP. `activity_tracking.py` conserva las reglas de privacidad, normalización, importación y exportación; `activity_repository.py` empieza a concentrar las consultas SQLite de retención y limpieza. La extracción es incremental: otros flujos de actividad todavía usan la conexión compartida y no se consideran migrados.
- **Red y diagnóstico:** módulos separados atienden descubrimiento local, vecinos, DNS, TLS, fabricantes y diagnósticos.
- **Monitorización y hallazgos:** hay lógica separada para comprobaciones periódicas, incidentes, notificaciones y la presentación normalizada de hallazgos.
- **Interfaz:** páginas HTML y estilos están separados por pantalla; la extensión vive en `browser-extension/`.

La separación por archivos ya existe, pero no todas las fronteras representan responsabilidades completas. La API y la persistencia concentran varios dominios, y las rutas conocen detalles de servicios y almacenamiento. Al crecer las fuentes de evidencia, esa estructura puede hacer que un cambio de una función afecte a otras que no deberían depender de ella.

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

El script `scripts/check_architecture_boundaries.py` se ejecuta en CI y comprueba que no haya ciclos de importación, que cada router declare sus dependencias permitidas y que los servicios/repositorios con dependencias internas tengan una lista explícita. La persistencia solo puede importar un conjunto explícito y pequeño de apoyos compartidos: `config.py` para la ubicación del archivo, `csv_safety.py` para exportaciones seguras, `network_models.py` para el contrato de vecinos y `vendor.py` para consultar la base OUI local sin red. Cualquier otro módulo interno requiere una decisión explícita. Además, todo módulo nuevo fuera de la API y del punto de composición se revisa automáticamente para evitar dependencias de FastAPI o Starlette. Así las nuevas extracciones no quedan fuera de las reglas por olvidar agregarlas a una lista manual. Estas verificaciones refuerzan las fronteras implementadas, pero no significan que todo el backend ya esté desacoplado.

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

## Límites de seguridad y privacidad

La app continúa enlazada a loopback y usa SQLite local. La modularización no justifica abrir la API a la red, añadir telemetría externa, capturar contenido sensible, cambiar la configuración del router ni activar automáticamente la extensión. Cada nueva fuente debe tener alcance, autorización, límite de tiempo, tratamiento de errores, política de retención y forma de desactivación documentados.

## Migración y pruebas

La reorganización será incremental y deberá preservar el contrato visible. Antes de mover consultas o cambiar tablas, hay que formalizar la versión del esquema SQLite y probar migraciones, copias de seguridad, importación y restauración. Las rutas actuales, formatos exportados, encabezados de seguridad, protección de origen y respuestas de error se cubren con pruebas de contrato.

No se considera terminada una extracción solo porque el código haya cambiado de archivo: debe reducir acoplamiento, mantener compatibilidad y demostrarlo con pruebas. El plan gradual y sus criterios de aceptación están en [ADR-001](ADR-001-MODULAR-MONOLITH.md) y en el [roadmap](ROADMAP.md).

## Pruebas actuales

Las pruebas automatizadas usan datos sintéticos y no requieren una red real. GitHub Actions valida la instalación y la suite de pruebas en Windows, macOS y Ubuntu con distintas versiones de Python. Las comprobaciones automatizadas no sustituyen la validación manual de sistemas y navegadores reales descrita en la matriz de validación.
