# NetSentinel — caso de estudio técnico

**Categoría:** inventario, observabilidad y diagnóstico local de redes autorizadas.  
**Estado:** versión de desarrollo `0.10.0.dev0`; no declarada estable.  
**Arquitectura:** aplicación local de despliegue único, organizada como monolito modular.

## Resumen

NetSentinel reúne en una aplicación local el inventario de dispositivos, la observación de cambios, las comprobaciones de disponibilidad y el diagnóstico de servicios. Conserva los datos en SQLite y presenta la procedencia y las limitaciones de cada observación para no confundir una señal técnica con una conclusión de seguridad.

El objetivo de diseño es resolver tareas iniciales de visibilidad y diagnóstico sin exigir primero una plataforma central, una cuenta en la nube o agentes permanentes. El descubrimiento y las comprobaciones se ejecutan bajo demanda o según monitores configurados; la actividad externa se importa expresamente o llega mediante una extensión opcional.

NetSentinel no es un SIEM, NDR, EDR, escáner integral de vulnerabilidades ni plataforma SOC.

## El problema que aborda

En una revisión de red autorizada, el inventario, las pruebas de disponibilidad, los diagnósticos y los registros disponibles suelen quedar repartidos entre distintas herramientas y archivos. Eso dificulta responder preguntas operativas básicas:

- ¿Qué dispositivos se observaron y en qué momento?
- ¿Qué cambió entre dos lecturas comparables?
- ¿Qué servicios responden y cuáles registraron incidentes?
- ¿Qué evidencia respalda un hallazgo y de dónde proviene?
- ¿Qué información se importó de una fuente externa y qué no se observó?

NetSentinel busca reunir esas tareas en una experiencia local, manteniendo acotado el alcance de las acciones y explícita la diferencia entre datos observados e interpretaciones.

## Decisiones de diseño

### 1. Una aplicación local, no una plataforma distribuida prematura

FastAPI sirve la interfaz y la API en loopback. SQLite conserva el estado local. Los módulos internos se comunican mediante interfaces Python dentro del proceso; no se agregan llamadas HTTP entre componentes internos ni microservicios que introduzcan despliegue, autenticación y operación adicionales.

La decisión no implica un backend monolítico sin límites: el código separa composición, routers, servicios, repositorios y adaptadores. La evolución de esos límites se registra en [ADR-001](ADR-001-MODULAR-MONOLITH.md).

### 2. Acciones explícitas y acotadas

El descubrimiento local se limita a redes privadas compatibles y comienza cuando la persona operadora lo solicita. Las comprobaciones de disponibilidad se configuran de forma explícita. Las consultas DNS y TLS tienen límites de tiempo y validación de entradas.

No se abre el servidor a la LAN como atajo, no se sondea automáticamente al iniciar y no se altera la configuración del router.

### 3. Evidencia antes que conclusiones

Los registros guardan fuente, momento y contexto. Los hallazgos organizan eventos de inventario e incidentes sin convertir una observación ambigua en prueba de compromiso. La topología LAN representa relaciones basadas en observaciones históricas; no demuestra por sí sola conexiones físicas ni tráfico entre equipos.

### 4. Privacidad y fuentes opcionales

La actividad se incorpora mediante importación explícita de CSV/Zeek o una extensión Chromium opcional habilitada por la persona usuaria. NetSentinel no ejecuta Zeek ni captura paquetes automáticamente. Las funciones de geolocalización dependen de una base GeoIP local y muestran ubicaciones aproximadas.

### 5. Simplicidad de instalación con límites internos verificables

Se mantiene una sola distribución y una base SQLite, pero los módulos tienen responsabilidades y dependencias declaradas. Las reglas de arquitectura se verifican en CI mediante análisis AST, sin añadir una herramienta de ejecución al producto.

## Arquitectura implementada

| Área | Responsabilidad | Evidencia en el código |
|---|---|---|
| Composición y API | Ciclo de vida, controles transversales y routers por capacidad | [main.py](../src/netsentinel/main.py), [api/](../src/netsentinel/api/) |
| Inventario y descubrimiento | Activos, observaciones, direcciones, exploraciones y exportación | [discovery.py](../src/netsentinel/discovery.py), [inventory_repository.py](../src/netsentinel/inventory_repository.py) |
| Monitorización | Monitores, sondas, lecturas, incidentes e historial | [monitoring.py](../src/netsentinel/monitoring.py), [monitoring_probe.py](../src/netsentinel/monitoring_probe.py) |
| Actividad | Privacidad, normalización, sesiones, importación y retención | [activity_import_service.py](../src/netsentinel/activity_import_service.py), [activity_zeek_import_service.py](../src/netsentinel/activity_zeek_import_service.py) |
| Hallazgos | Consulta y presentación de evidencia de varios dominios | [findings_service.py](../src/netsentinel/findings_service.py) |
| Persistencia | Esquema, conexiones, permisos y almacenamiento SQLite | [database_schema.py](../src/netsentinel/database_schema.py), [database_storage.py](../src/netsentinel/database_storage.py) |
| Geolocalización | Lectura de una base GeoIP local opcional | [geolocation_service.py](../src/netsentinel/geolocation_service.py) |
| Forense | Casos, manifiestos y operaciones de evidencia | [forensics_service.py](../src/netsentinel/forensics_service.py); módulo experimental |

La vista completa está en [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md). El [inventario técnico](ARCHITECTURE.md) detalla las responsabilidades y las fachadas de compatibilidad que todavía se conservan.

## Calidad y verificación

La estrategia de calidad combina pruebas de comportamiento con controles sobre la estructura y la distribución:

- La CI está configurada para Python 3.10–3.14 en Ubuntu, Windows y macOS.
- Un job separado instala las dependencias mínimas declaradas y ejecuta la suite sobre Python 3.10.
- La suite cubre API, persistencia, descubrimiento, monitorización, DNS/TLS, importación, privacidad, hallazgos, geolocalización, Forense, CLI y navegación.
- Un control AST verifica dependencias internas permitidas y evita ciclos arquitectónicos.
- CI valida metadatos del wheel, recursos estáticos, constraints mínimas, cabeceras de seguridad y pruebas responsive con Chromium.
- Los workflows separados ejecutan CodeQL, auditoría de dependencias y detección de secretos; el de cadena de suministro genera wheel, SBOM y manifiesto de integridad.

La configuración y los resultados deben evaluarse por commit. Una matriz configurada no significa que cada sistema operativo haya sido probado manualmente, y una ejecución verde de una PR no valida automáticamente otro SHA ni reemplaza la aceptación manual.

Puntos de entrada para revisar la implementación: [pruebas de límites arquitectónicos](../tests/test_architecture_boundaries.py), [pruebas de importación Zeek](../tests/test_activity_zeek_import_service.py), [pruebas de descubrimiento](../tests/test_local_discovery.py), [pruebas de monitorización](../tests/test_monitoring.py) y [pruebas de seguridad del navegador](../tests/test_security_headers.py).

## Evidencia automatizada asociada a la revisión del 3 de noviembre de 2026

La PR [#208](https://github.com/JavierGrecco/NetSentinel/pull/208), HEAD `96f4e2e49b325dfc1ef4469a725f2c458c9d0fc1`, completó sus controles aplicables sin fallos:

| Control | Resultado observado | Alcance |
|---|---:|---|
| CI, seguridad y cadena de suministro | 23 aprobados; 1 omisión esperada | La firma de procedencia se omite en PR que no publican una release |
| Suite Python | **855 pruebas aprobadas en 8,35 s** | Una ejecución de la matriz: Python 3.14 en Ubuntu |
| Interfaz responsive con Chromium | **135/135 comprobaciones correctas** | Seis páginas en la matriz de viewports definida por el script |
| CodeQL y auditoría de dependencias | Correctos | Análisis estático y dependencias del commit evaluado |
| Detección de secretos | Correcta | Gitleaks sin hallazgos no exceptuados |
| Paquete y cadena de suministro | Correctos | Wheel, SBOM y manifiesto de integridad generados |

Ejecuciones asociadas a esa revisión:

- [CI multiplataforma y responsive — run 41639881135](https://github.com/JavierGrecco/NetSentinel/actions/runs/41639881135).
- [Análisis de seguridad — run 41639881145](https://github.com/JavierGrecco/NetSentinel/actions/runs/41639881145).
- [Cadena de suministro — run 41639881114](https://github.com/JavierGrecco/NetSentinel/actions/runs/41639881114).

La ejecución de CI para una Pull Request utiliza la referencia de merge de GitHub, es decir, comprueba la combinación de la rama de trabajo con su base en ese momento. Por eso estos números se presentan como evidencia de la revisión de la PR #208, no como un resultado manual ni como garantía permanente para cualquier instalación. Los 855 tests corresponden a una sola combinación de la matriz; las demás combinaciones validan compatibilidad, pero no se extrapola aquí el mismo tiempo de ejecución.

## Límites conocidos

- **Desarrollo activo:** la versión publicada en el código es `0.10.0.dev0`. No se presenta como versión estable.
- **Aceptación manual pendiente:** faltan recorridos integrales registrados en instalaciones reales, revisión completa de accesibilidad y comprobaciones manuales de recuperación de datos.
- **Gobernanza pendiente:** el Ruleset de GitHub todavía no demuestra que proteja `main` ni que exija los checks de integración. El detalle está en [GITHUB_SETUP.md](GITHUB_SETUP.md).
- **Forense experimental:** hashes y manifiestos ayudan a detectar cambios, pero no autentican por sí solos al operador ni constituyen una cadena de custodia legalmente validada.
- **GeoIP aproximado:** el mapa requiere una base local válida y no permite inferir con precisión la ubicación de una persona o dispositivo.
- **Alcance deliberado:** no hay operación remota multi-sede, gestión multiusuario, captura automática de paquetes ni análisis integral de amenazas.

## Próximos pasos de ingeniería

1. Completar la aceptación manual sobre un SHA identificado y registrar resultados reales.
2. Confirmar backup, restauración y recuperación ante fallos en los sistemas soportados.
3. Configurar y probar efectivamente las reglas de integración de `main`.
4. Incorporar capturas auténticas, sanitizadas y vinculadas a una versión comprobada después de la aceptación; no presentar mockups como interfaz real.
5. Reducir gradualmente las fachadas de compatibilidad donde exista una mejora clara y cubierta por pruebas.

## Investigación y procedencia

Las herramientas y proyectos comparados se conservan en [RESEARCH_INDEX.md](RESEARCH_INDEX.md). La investigación sirvió para evaluar patrones y límites; no implica copia automática, asociación ni equivalencia funcional. Los componentes realmente distribuidos mantienen sus avisos en [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

