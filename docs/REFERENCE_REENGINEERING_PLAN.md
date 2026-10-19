# Plan de reingeniería selectiva de los proyectos de referencia

**Estado:** laboratorio aislado; no integrado en `main`.
**Rama:** `lab/reference-reengineering-2026-10`
**Base:** `main` en `81552f93d65bca33d4123df07748f605673cbb54`.
**Objetivo:** estudiar los proyectos de referencia, rescatar las ideas útiles y transformarlas en módulos pequeños, comprobables y adecuados a la arquitectura de NetSentinel. No se propone importar ninguno de los repositorios completos.

## Decisión principal

Sí conviene tener un espacio separado para experimentar, pero no conviene copiar un proyecto entero y después intentar desarmarlo. La ruta más segura y eficiente es:

1. inspeccionar el código y sus licencias;
2. registrar qué problema resuelve cada módulo y qué supuestos hace;
3. definir primero un contrato de datos para NetSentinel;
4. reproducir las ideas útiles en una prueba aislada con datos sintéticos;
5. integrar una capa por vez mediante cambios pequeños y reversibles.

Esta rama es el lugar de trabajo para el plan y los prototipos. `main` no cambia por este documento ni se incorpora código ajeno en esta etapa.

## Auditoría de las referencias

### 1. `ossianericson/netsentinel`

Repositorio: https://github.com/ossianericson/netsentinel

El repositorio contiene una licencia MIT. Esto permite estudiar y, si resulta conveniente, reutilizar partes de su código respetando el aviso de copyright y la licencia. No significa que convenga copiar directamente componentes que dependen de la arquitectura propia del proyecto.

**Qué merece estudiarse y adaptarse**

- Separación entre construcción del grafo, estilos, disposición y comparación de capturas.
- Selección y enfoque de un nodo, navegación por vecinos, filtros y posiciones guardadas como preferencia visual.
- Comparación de dos estados y presentación de cambios de forma entendible.
- Prácticas para evitar reconstrucciones y actualizaciones innecesarias del grafo.

**Advertencias detectadas en el código inspeccionado**

- El constructor de instantáneas puede crear una arista entre la puerta de enlace y cada dispositivo solo porque se conoce la puerta de enlace. Esto es una inferencia de topología, no una relación física ni un flujo de tráfico demostrado. No debe trasladarse como una relación confirmada.
- La firma usada por `compute_scan_id` deriva subredes `/24` desde las direcciones de los equipos, en vez de usar necesariamente los rangos reales registrados. Puede agrupar mal redes que usen otras máscaras. NetSentinel debe conservar el ID real de la lectura y los CIDR observados.
- La función de identidad de nodo puede terminar usando `id(objeto)` si faltan MAC e IP. Esa identidad cambia entre ejecuciones y no es adecuada para guardar posiciones o comparar historiales.
- Partes de la vista están acopladas a PyQt/QWebEngine y a modelos, servicios y puentes propios de esa aplicación. Nuestro producto usa FastAPI, SQLite y una interfaz web estática. Copiar la vista literalmente agregaría acoplamiento; es preferible adaptar los algoritmos y mantener nuestra tecnología de presentación.
- Los supuestos sobre malla Wi-Fi, gateway y fuentes auxiliares deben activarse solo con datos de una fuente que realmente los proporcione.

**Decisión:** reutilizar patrones y algoritmos tras revisar sus contratos y pruebas. Cualquier código que se copie debe mantener su aviso MIT y quedar registrado en los avisos de terceros.

### 2. `blacsecurity/netsentinel`

Repositorio: https://github.com/blacsecurity/netsentinel

Este proyecto presenta una vista atractiva de actividad, resúmenes y alertas. Sin embargo, la inspección encontró una discrepancia de procedencia/licencia: el README menciona MIT con atribución a `spiderxploit` y recomienda clonar ese otro repositorio, mientras que no aparece un archivo `LICENSE` en la raíz del repositorio inspeccionado. Hasta aclarar los derechos sobre el código exacto, no se debe copiar código literal de esta fuente.

**Qué podemos estudiar sin copiar su código**

- Jerarquía visual de resúmenes y eventos recientes.
- Selección de equipos y acceso rápido al detalle.
- Filtros, leyenda y señales discretas para actividad que tenga una fuente real.
- Forma de organizar una lectura rápida del estado general antes de entrar al detalle.

**Qué no se debe heredar**

- La aplicación monolítica como base arquitectónica.
- Contadores estimados que se presentan como si fueran medidas reales por flujo.
- Conclusiones de vulnerabilidad basadas solo en un puerto abierto.
- Acciones de bloqueo o modificación de red sin un modelo completo de permisos, límites, auditoría y reversión.
- Dependencias externas o comportamiento en vivo que no tenga un origen de datos explícito.

**Decisión:** usarlo como referencia de interacción, no como base de código, hasta resolver la procedencia y demostrar que una función concreta vale la pena.

## Qué queremos construir en nuestro proyecto

El objetivo no es reproducir un “mapa animado”. Es un espacio de investigación que permita responder qué se observó, cuándo, mediante qué fuente, qué cambió y qué se puede comprobar a continuación.

### Contrato mínimo para el modelo de topología

El modelo de dominio deberá distinguir al menos:

- **Lectura:** ID persistente, hora de inicio/fin, redes consultadas, alcance, errores y estado de finalización.
- **Dispositivo:** identidad estable de inventario; nombre, IP, MAC y fabricante serán atributos que pueden faltar o cambiar.
- **Observación:** lectura de origen, dispositivo, dirección observada, momento y fuente. La ausencia de una observación no prueba que el equipo esté apagado.
- **Relación:** extremos, tipo explícito, fuente, lectura, tiempo y estado de evidencia. No se deben crear relaciones físicas a partir de una mera pertenencia a subred.
- **Evento de actividad:** hora del origen y de recepción cuando existan, tipo de evento, fuente, datos disponibles, alcance y referencia a su evidencia.
- **Estado visual:** posiciones, zoom, filtros y selección. Se mantiene separado de las observaciones históricas y nunca modifica la evidencia.

Los campos desconocidos deben seguir siendo desconocidos. No convertir valores ausentes en cero, ni estimaciones en mediciones, ni relaciones inferidas en hechos.

## Capas propuestas

Los nombres son orientativos; antes de crear archivos nuevos se compararán con los módulos actuales para no duplicar responsabilidades.

| Capa | Responsabilidad | Límite |
|---|---|---|
| Modelo de dominio | Identidad, observaciones, relaciones y estados de evidencia | No conoce HTML, Cytoscape ni SQLite |
| Adaptadores de fuentes | Normalizar inventario, tabla local de vecinos y, más adelante, logs/flujos autorizados | Cada adaptador declara alcance, límites y campos que realmente conoce |
| Lecturas y comparación | Recuperar una lectura exacta, comprobar compatibilidad y obtener diferencias | No infiere desconexiones a partir de ausencias |
| Servicios de consulta | Preparar los datos que necesita la interfaz | No mezcla lógica de negocio con estilos o eventos del navegador |
| Persistencia | Guardar los datos históricos mediante los repositorios existentes | La vista no escribe directamente en la base |
| Presentación del grafo | Dibujar nodos, relaciones, filtros, selección y movimientos | Solo representa el modelo recibido; no crea hechos de red |
| Panel contextual y línea de tiempo | Mostrar detalle, observaciones, cambios y procedencia | Toda conclusión enlaza con registros verificables |

## Secuencia de trabajo

### Etapa 1 — Fijar el contrato y las pruebas

El primer prototipo ya contiene un modelo puro y un servicio de consulta que usa la persistencia existente. La consulta exacta de una lectura se agregó a la fachada existente para no depender del límite de las capturas recientes. Hay pruebas de regresión para la lectura histórica, informes corruptos, direcciones múltiples, subredes repetidas por interfaz y alcance limitado.

Falta validar la nueva cabeza completa. Las pruebas escritas no se consideran aprobadas hasta que CI concluya sobre ese SHA.

**Salida exigida:** contrato documentado y pruebas que fallen cuando el modelo fabrique relaciones o interprete una ausencia como desconexión.

### Etapa 2 — Aislar el modelo de topología

Extraer o reescribir la construcción de nodos y relaciones como funciones pequeñas sin interfaz ni acceso a la base de datos. Evaluar algoritmos de disposición, pero mantener la presentación intercambiable.

**Salida exigida:** las mismas entradas producen el mismo modelo; los identificadores permanecen estables entre ejecuciones; ninguna relación se crea sin una regla documentada. La prueba actual separa el constructor puro de la consulta de persistencia y comprueba que una lectura anterior conserve la IP registrada originalmente aunque el inventario actual haya cambiado.

### Etapa 3 — Añadir comparación histórica

Utilizar las observaciones guardadas por NetSentinel. Comparar solo lecturas con alcance compatible y explicar diferencias, datos faltantes, errores y antigüedad.

**Salida exigida:** cada diferencia se puede rastrear hasta la lectura y la observación original; una prueba sintética demuestra que “no observado” nunca se convierte automáticamente en “desconectado”.

### Etapa 4 — Pulir el explorador visual

Mantener Cytoscape.js local si supera las pruebas de utilidad, accesibilidad y rendimiento. Separar el modelo, la construcción de elementos, los estilos y la interacción. Conservar las posiciones como preferencia de presentación, con almacenamiento acotado y validado.

**Salida exigida:** selección con ratón y teclado, búsqueda, filtros, foco del nodo elegido, lista textual equivalente, tres temas visuales, diseño responsive y pruebas reproducibles del flujo principal.

### Etapa 5 — Incorporar actividad real por capas

Antes de animar flujos o asignar contadores por dispositivo, seleccionar una fuente autorizada concreta y construir un adaptador de solo lectura. DNS, registros de firewall y NetFlow/IPFIX tienen capacidades distintas; no se supondrá que todos los routers ofrecen esas funciones.

**Salida exigida:** fuente identificada, esquema normalizado, marcas de tiempo, pruebas de expiración/retención, límites, fallos explicables y valores solo para métricas realmente medidas.

### Etapa 6 — Integración gradual

Cada capa se entrega como una PR pequeña contra una base actualizada, con sus pruebas y documentación. Nada se integra automáticamente por existir en el laboratorio.

**Puerta de integración:** CI, seguridad, empaquetado y revisión de dependencias en verde; casos de error probados; evidencia y licencia registradas; revisión manual cuando cambia la interfaz. No se fusiona una rama de investigación completa como un único bloque.

## Criterios de calidad

- No copiar repositorios completos ni reemplazar la arquitectura actual para imitar otra aplicación.
- No reutilizar código de `blacsecurity/netsentinel` hasta aclarar la licencia del código exacto y su procedencia.
- Al reutilizar código MIT de `ossianericson/netsentinel`, conservar el aviso exigido y anotarlo en `THIRD_PARTY_NOTICES.md`.
- No agregar una dependencia hasta justificarla y comprobar su licencia, mantenimiento, empaquetado y uso sin Internet.
- No añadir funciones de captura, bloqueo o cambios de configuración de red como efecto secundario del mapa.
- No duplicar lo que ya existe en los módulos actuales; extender la interfaz pública estable de cada módulo.
- Registrar cada tarea como pendiente, en curso o terminada solo con evidencia. El diseño de un plan no cuenta como implementación.

## Estado al 19 de octubre de 2026

- [x] Rama de laboratorio creada desde el `main` consultado.
- [x] Revisiones previas de ambos proyectos localizadas y contrastadas.
- [x] Riesgos de reutilización y primeros límites de arquitectura documentados.
- [x] Modelo puro en `src/netsentinel/topology_model.py`, separado de la persistencia y la presentación.
- [x] Consulta exacta de lecturas históricas expuesta por los repositorios/fachada existentes; evita depender del límite de las capturas recientes.
- [x] Servicio de consulta en `src/netsentinel/topology_service.py`, con pruebas que usan SQLite temporal.
- [x] Proyección neutral en `src/netsentinel/topology_graph.py`; produce nodos, relaciones, contadores y procedencia sin depender de Cytoscape.
- [x] Pruebas para relaciones observadas, dispositivos sin enlace confirmado, direcciones múltiples, IDs estables, evidencia no disponible y lectura vacía.
- [x] Incorporada la allow-list explícita del servicio de topología en `scripts/check_architecture_boundaries.py` tras un fallo real de CI en el prototipo.
- [ ] Confirmar que la comprobación de límites y el conjunto completo de tests pasan en la cabeza final de la PR #172.
- [ ] Aprobar CI, análisis de seguridad y cadena de suministro en la cabeza final de la PR #172. Los resultados de commits anteriores no validan automáticamente los cambios posteriores.
- [ ] Revisar con detalle el ajuste del repositorio de lecturas y la semántica de los metadatos actuales frente al historial.
- [ ] Resolver los pendientes de la PR #171 antes de conectar la proyección neutral con la interfaz visual.
- [ ] Mantener la PR como laboratorio hasta verificar que los módulos no duplican responsabilidades y que las pruebas cubren los casos de error.

## Referencias internas

- [Revisión de ossianericson/netsentinel](REFERENCE_PROJECT_REVIEW.md)
- [Auditoría de blacsecurity/netsentinel](REFERENCE_PROJECT_REVIEW_BLACSECURITY.md)
- [Arquitectura actual de NetSentinel](ARCHITECTURE.md)
- [Visibilidad de red y límites de las fuentes](NETWORK_VISIBILITY.md)
- [Estado del proyecto](PROJECT_STATUS.md)
- [Explorador de red en desarrollo](https://github.com/JavierGrecco/NetSentinel/pull/171)
