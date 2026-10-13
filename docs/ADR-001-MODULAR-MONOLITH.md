# ADR-001: evolucionar hacia un monolito modular

- **Estado:** Propuesta para revisión.
- **Fecha:** 2026-10-13.
- **Alcance:** organización interna del backend Python y sus contratos con la API, la interfaz y las fuentes de datos.
- **No cambia:** el modo local de ejecución, el servidor en loopback, SQLite ni el comportamiento funcional de la versión actual.

## Contexto

NetSentinel ya reúne varias responsabilidades distintas: inventario y descubrimiento local, monitorización periódica, incidentes y avisos, consultas DNS/TLS, diagnósticos, actividad procedente de fuentes autorizadas, importación/exportación y hallazgos. También hay una extensión Chromium opcional que se comunica con el backend mediante la API.

El código ya tiene módulos dedicados, pero las responsabilidades siguen concentradas en puntos compartidos. La aplicación FastAPI mezcla creación de la app, configuración de seguridad, páginas y rutas de varios dominios; la capa SQLite reúne consultas y almacenamiento de inventario, actividad y monitorización; y el módulo de actividad contiene desde normalización sensible a privacidad hasta ciclos de vida de sesión e importación. Estas concentraciones hacen que sea más costoso localizar un cambio, aislar una prueba y revisar qué comportamiento podría verse afectado.

La modularización debe preparar el crecimiento, no añadir complejidad operacional al usuario.

## Decisión propuesta

Adoptar un **monolito modular local**: una distribución, un proceso principal y una base SQLite, con módulos internos cohesionados, interfaces explícitas y dependencias dirigidas.

### Responsabilidad de cada capa

1. **Composición de la aplicación:** crea FastAPI, registra routers, configura el ciclo de vida y conecta dependencias. Es el lugar donde se reúnen los componentes, no donde se acumula la lógica de cada función.
2. **API y clientes:** los routers validan peticiones, llaman a servicios y convierten resultados y errores en respuestas HTTP estables. No ejecutan SQL ni contienen reglas de negocio.
3. **Servicios de dominio:** cada módulo ofrece casos de uso claros y tipos de entrada/salida conocidos. Las reglas de inventario, monitorización, actividad y hallazgos pertenecen a su dominio.
4. **Adaptadores e infraestructura:** los repositorios gestionan lecturas y escrituras SQLite; los adaptadores encapsulan comandos del sistema o fuentes externas. Los módulos no deben saltarse estas fronteras para consultar tablas ajenas.
5. **Contratos compartidos:** los tipos realmente transversales —por ejemplo, referencia de activo, procedencia, marca de tiempo y resultado de una observación— se definen una vez, con significado documentado. No se crea una estructura universal enorme para cada dato.

### Módulos de destino

La estructura definitiva se ajustará al extraer código; no se crearán paquetes vacíos solo para cumplir un dibujo. Las fronteras funcionales esperadas son:

- **Inventario y descubrimiento:** activos, direcciones, observaciones y procedencia.
- **Monitorización:** configuración de controles, sondas, programación, transiciones e incidentes.
- **Actividad:** sesiones autorizadas, tokens, normalización de eventos, privacidad, retención e importación/exportación.
- **Hallazgos:** agrupación y explicación de evidencia, sin apropiarse de los registros originales.
- **Herramientas de red y diagnóstico:** DNS, TLS, conectividad y diagnóstico local acotado.
- **API/presentación:** routers por capacidad y recursos estáticos.
- **Infraestructura:** conexiones y transacciones SQLite, migraciones versionadas y repositorios de cada dominio.

Un módulo presta servicio a otros mediante funciones o interfaces tipadas dentro del proceso. Los clientes externos usan la API; **no se hacen llamadas HTTP entre módulos internos**. La abstracción adicional solo se justifica donde exista variación real —por ejemplo, varias fuentes de descubrimiento— y se implementa como adaptador pequeño, no como cargador genérico de plugins.

## Qué aprendemos de herramientas maduras

Estas referencias no son equivalentes uno a uno a NetSentinel, pero enseñan patrones útiles:

- **Fing** prioriza el descubrimiento sencillo, el reconocimiento de dispositivos y una experiencia de inicio rápida, con aplicaciones de escritorio y agentes opcionales para seguimiento continuo. Para NetSentinel, la lección es que separar internamente no debe añadir pasos al usuario; los agentes deben responder a una necesidad real de continuidad y cobertura. [Referencia](https://www.fing.com/scan/)
- **Angry IP Scanner** documenta un núcleo de escaneo desacoplado, un mediador entre la interfaz y los recolectores, y *fetchers* seleccionables o ampliables mediante plugins. Es un ejemplo especialmente cercano de extensibilidad por adaptadores. La lección es definir interfaces intercambiables para recolectar datos, pero no crear un cargador de plugins hasta que tengamos múltiples implementaciones reales. [Referencia](https://angryip.org/documentation/)
- **Auvik** separa un colector instalado en la red del servicio de gestión central y contempla más de un colector para segmentos aislados o continuidad operativa. Esa separación responde a despliegues multi-sede; no es motivo para convertir ahora NetSentinel en un producto remoto. [Arquitectura y seguridad](https://www.auvik.com/system-security/) · [Cuándo desplegar colectores](https://support.auvik.com/hc/en-us/articles/217099526-When-and-how-to-deploy-additional-Auvik-collectors)
- **Wazuh** separa agente, servidor de análisis, indexador y panel. La lección es dividir recolección, procesamiento, almacenamiento y visualización cuando tienen responsabilidades diferentes; no exige replicar esa arquitectura distribuida en una app local. [Referencia](https://documentation.wazuh.com/current/getting-started/architecture.html)
- **Zeek** separa el motor de eventos que describe lo observado de la política que interpreta esos eventos. NetSentinel puede aplicar el mismo principio: preservar la evidencia y su procedencia separadas de la conclusión o recomendación. [Referencia](https://docs.zeek.org/en/current/about/architecture.html)
- **Suricata** ofrece salidas estructuradas como EVE JSON para alertas, anomalías y metadatos. Un contrato de salida estable hace posible añadir consumidores sin acoplarlos al código interno que detecta. [Referencia](https://docs.suricata.io/en/suricata-8.0.2/output/eve/eve-json-output.html)
- **Zabbix** define papeles distintos para servidor, base de datos, interfaz, proxy y agente. El proxy es opcional y sirve a entornos que necesitan distribuir la recolección. [Referencia](https://www.zabbix.com/documentation/7.2/en/manual/introduction/overview)
- **Prometheus** usa exportadores para adaptar sistemas que no están instrumentados directamente. [Referencia](https://prometheus.io/docs/instrumenting/exporters/)
- **LibreNMS** recomienda escalar gradualmente: optimizar una instalación estable y separar servicios o añadir pollers cuando la carga lo pide. [Referencia](https://docs.librenms.org/Extensions/Distributed-Poller/)

La conclusión no es copiar esos sistemas: es mantener módulos cohesionados, contratos estables y una experiencia de uso sencilla, separando procesos solo cuando la escala, el aislamiento o el despliegue lo justifiquen.

## Opciones consideradas

| Opción | Decisión | Motivo |
| --- | --- | --- |
| Mantener el módulo único por capacidad y seguir sumando rutas/consultas compartidas | No como dirección a largo plazo | Aumenta el acoplamiento y dificulta pruebas aisladas y revisión del impacto |
| **Monolito modular** | **Recomendada** | Conserva la experiencia de una app local y permite aislar reglas, almacenamiento y pruebas por dominio |
| Microservicios o procesos independientes ahora | No | Añade despliegue, autenticación interna, supervisión, versionado de contratos y fallos de red sin una necesidad actual demostrada |
| Sistema de plugins cargables desde archivos externos | No por ahora | Amplía la superficie de ataque y mantenimiento antes de tener varios adaptadores reales que lo justifiquen |

## Plan de migración

La versión 0.10.0 debe seguir priorizando las puertas de estabilización y la validación manual. La extracción de código no debe mezclarse con los fixes de release ni cambiar comportamiento a escondidas.

1. **Establecer la línea base.** Documentar las rutas y dependencias actuales; asegurar pruebas de contrato para respuestas JSON, códigos HTTP, seguridad del navegador, exportaciones, CLI y ciclo de vida.
2. **Separar la entrada de la aplicación.** Extraer routers por dominio de `main.py`; dejar en la composición de la app el registro de rutas, middleware y ciclo de vida. Mantener alias temporales si alguna prueba o importación pública lo necesita.
3. **Versionar el esquema SQLite.** Añadir un mecanismo explícito de versión/migración y pruebas de actualización, backup y restore antes de mover tablas o cambiar sus consultas.
4. **Crear servicios y repositorios por dominio.** Extraer primero la responsabilidad más acotada, conservar funciones de compatibilidad y retirar la fachada anterior solo cuando no tenga consumidores.
5. **Establecer límites automatizados.** Añadir pruebas arquitectónicas que comprueben, como mínimo, que los routers no ejecutan SQL, los módulos no importan detalles internos de otro dominio y las reglas de dominio no dependen de FastAPI.
6. **Introducir adaptadores de fuente cuando sean reales.** Definir contrato, fixture y prueba de errores antes de integrar cada nueva fuente; mantener las fuentes opcionales y de solo lectura cuando aplique.
7. **Evaluar separación de procesos con evidencia.** Considerar procesos/servicios separados solo si aparecen necesidades medibles de escala, permisos, aislamiento de fallos o despliegue independiente.

## Criterios para aceptar cada extracción

- El comportamiento anterior permanece cubierto por pruebas, incluidas las respuestas API y el uso de la interfaz.
- El módulo tiene un responsable claro y una interfaz pública pequeña y documentada.
- No hay dependencia circular ni acceso directo a tablas de otros dominios.
- Las operaciones que escriben datos mantienen atomicidad y las copias SQLite siguen siendo restaurables.
- Los errores tienen un mensaje útil y no filtran URLs privadas, tokens, credenciales ni datos de actividad.
- La documentación y los ejemplos indican qué se observa, qué se infiere y qué límites tiene cada fuente.

## Fuera de alcance

Esta decisión no incorpora colas, Redis, un bus de eventos, Kubernetes, un servidor remoto ni microservicios. Tampoco autoriza captura de contenido de correo o navegación, apertura de la API a la red ni cambios automáticos de la configuración del router.

## Referencias técnicas

- [Wazuh — Architecture](https://documentation.wazuh.com/current/getting-started/architecture.html)
- [Zeek — Architecture](https://docs.zeek.org/en/current/about/architecture.html)
- [Suricata — EVE JSON output](https://docs.suricata.io/en/suricata-8.0.2/output/eve/eve-json-output.html)
- [Zabbix — Overview and architecture](https://www.zabbix.com/documentation/7.2/en/manual/introduction/overview)
- [Prometheus — Exporters and integrations](https://prometheus.io/docs/instrumenting/exporters/)
- [LibreNMS — Distributed polling and gradual scaling](https://docs.librenms.org/Extensions/Distributed-Poller/)
