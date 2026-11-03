# ADR-001: aplicación modular con despliegue único y límites estrictos

- **Estado:** Adoptada como dirección arquitectónica; implementación en evolución (3 de noviembre de 2026).
- **Fecha:** 2026-10-13.
- **Alcance:** organización interna del backend Python y sus contratos con la API, la interfaz y las fuentes de datos.
- **No cambia:** el modo local de ejecución, el servidor en loopback, SQLite ni el comportamiento funcional de la versión actual.

## Contexto

NetSentinel ya reúne varias responsabilidades distintas: inventario y descubrimiento local, monitorización periódica, incidentes y avisos, consultas DNS/TLS, diagnósticos, actividad procedente de fuentes autorizadas, importación/exportación y hallazgos. También hay una extensión Chromium opcional que se comunica con el backend mediante la API.

El código ya tiene módulos dedicados, pero las responsabilidades siguen concentradas en puntos compartidos. La aplicación FastAPI mezcla creación de la app, configuración de seguridad, páginas y rutas de varios dominios; la capa SQLite reúne consultas y almacenamiento de inventario, actividad y monitorización; y el módulo de actividad contiene desde normalización sensible a privacidad hasta ciclos de vida de sesión e importación. Estas concentraciones hacen que sea más costoso localizar un cambio, aislar una prueba y revisar qué comportamiento podría verse afectado.

La modularización debe preparar el crecimiento, no añadir complejidad operacional al usuario.

## Decisión adoptada

Adoptar una **aplicación modular de despliegue único**. En esta decisión, *monolito* describe solo el artefacto de instalación y el proceso principal; no significa que cada módulo sea un bloque grande ni que pueda depender libremente de los demás. La distribución puede ser una, mientras los módulos internos siguen siendo pequeños, cohesionados, testeables y protegidos por contratos explícitos. Se conserva SQLite local y se diseña el interior para que componentes que lo justifiquen puedan separarse más adelante.

La decisión se adopta como dirección de diseño para el producto actual. **No implica que toda la migración esté terminada.** La implementación ya separa routers, servicios y repositorios en varios dominios, y CI verifica un conjunto explícito de dependencias. Persisten fachadas de compatibilidad y puntos de composición que deben reducirse con cambios acotados, manteniendo los contratos existentes.

**Estado de implementación — 3 de noviembre de 2026:**
- Implementado: routers agrupados por capacidad en Inventario, Actividad, Monitorización, Herramientas y otros dominios.
- Implementado: servicios y repositorios especializados para operaciones de Actividad, Monitorización, topología, geolocalización y Forense.
- Implementado: verificación estática de ciclos y dependencias permitidas mediante `scripts/check_architecture_boundaries.py`, ejecutada en CI.
- En evolución: reducir las fachadas de compatibilidad y las concentraciones de responsabilidades sin romper API, persistencia ni experiencia local.
- Pendiente de estabilización: completar aceptación manual, backup/restauración y revisión de los flujos críticos sobre el commit que se publique.

### Responsabilidad de cada capa

1. **Composición de la aplicación:** crea FastAPI, registra routers, configura el ciclo de vida y conecta dependencias. Es el lugar donde se reúnen los componentes, no donde se acumula la lógica de cada función.
2. **API y clientes:** los routers validan peticiones, llaman a servicios y convierten resultados y errores en respuestas HTTP estables. No ejecutan SQL ni contienen reglas de negocio.
3. **Servicios de dominio:** cada módulo ofrece casos de uso claros y tipos de entrada/salida conocidos. Las reglas de inventario, monitorización, actividad y hallazgos pertenecen a su dominio.
4. **Adaptadores e infraestructura:** los repositorios gestionan lecturas y escrituras SQLite; los adaptadores encapsulan comandos del sistema o fuentes externas. Los módulos no deben saltarse estas fronteras para consultar tablas ajenas.
5. **Contratos compartidos:** los tipos realmente transversales —por ejemplo, referencia de activo, procedencia, marca de tiempo y resultado de una observación— se definen una vez, con significado documentado. No se crea una estructura universal enorme para cada dato.

### Reglas de diseño que no deben negociarse

- **Límites por capacidad funcional.** Un módulo agrupa reglas y cambios que suelen evolucionar juntos; no se crean módulos solo por tipo de archivo ni uno por cada función.
- **Alta cohesión y bajo acoplamiento.** Cada módulo expone una interfaz pública pequeña. Su implementación queda privada y puede cambiar sin obligar a sus clientes a conocerla.
- **Dependencias dirigidas y sin ciclos.** La composición conecta módulos. La API llama a servicios; los servicios no importan la API. Los adaptadores de infraestructura implementan contratos definidos hacia el interior.
- **Reglas de dominio independientes del transporte.** La lógica de inventario, actividad, monitorización y hallazgos no debe depender de clases FastAPI, peticiones HTTP ni detalles de SQLite.
- **Persistencia con propiedad lógica.** Cada dominio gestiona sus operaciones y consultas. Una única SQLite es aceptable, pero no es aceptable que otro módulo escriba directamente en sus tablas para evitar la interfaz publicada.
- **Contratos tipados y errores explícitos.** Definir entradas, salidas, límites, efectos secundarios y errores esperados. No filtrar estructuras internas ni exponer un modelo universal gigante.
- **Sin comunicación de red dentro del proceso.** Las llamadas internas son interfaces Python tipadas. HTTP, colas o RPC solo se introducen cuando los componentes son procesos independientes por una necesidad demostrada.
- **Sin estado global oculto.** La composición debe hacer visibles las dependencias. Evitar singletons mutables que vuelvan las pruebas dependientes del orden.
- **Pruebas por frontera.** Cada módulo necesita pruebas unitarias; los límites públicos necesitan pruebas de contrato e integración; las reglas de arquitectura deben comprobar automáticamente que no aparezcan ciclos o dependencias prohibidas.
- **Abstracción justificada por variación real.** Los adaptadores se introducen para fuentes distintas o sustitución necesaria, no para anticipar todos los proveedores imaginables.
- **Separación desplegable cuando haya una razón operativa.** Solo se extrae un módulo a otro proceso si necesita escalar, recuperarse, aislar privilegios o desplegarse independientemente. La separación en carpetas no exige separación de procesos.

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

## Investigación considerada

La decisión se contrastó con herramientas de inventario, monitorización, análisis de tráfico y arquitecturas modulares. La investigación completa, las referencias originales y la separación entre patrones estudiados y decisiones propias están centralizadas en [RESEARCH_INDEX.md](RESEARCH_INDEX.md). Este ADR registra la decisión de NetSentinel; no pretende atribuirle implementación, autoría ni equivalencia con esos productos.

La referencia externa sirvió para evaluar alternativas, no para copiar arquitecturas distribuidas ni incorporar código sin procedencia y licencia verificadas.

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
5. **Establecer límites automatizados.** Ejecutar `scripts/check_architecture_boundaries.py` en CI para comprobar ciclos, listas explícitas de dependencias de los routers, independencia de la persistencia respecto de la API/dominios de coordinación y ausencia de dependencias HTTP en módulos de dominio/infraestructura. Ampliar las reglas cuando se extraigan nuevas fronteras.
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

## Fuentes y trazabilidad

- [Índice de investigación, fuentes y decisiones propias](RESEARCH_INDEX.md).
- [Vista general de arquitectura](ARCHITECTURE_OVERVIEW.md).
- [Arquitectura implementada y reglas de dependencia](ARCHITECTURE.md).
- [Verificador de límites arquitectónicos](../scripts/check_architecture_boundaries.py).

