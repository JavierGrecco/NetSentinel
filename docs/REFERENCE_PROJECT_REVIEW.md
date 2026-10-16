# Revisión del NetSentinel de referencia y oportunidades para nuestro proyecto

**Fecha de revisión:** 16 de octubre de 2026  
**Proyecto de referencia:** [ossianericson/netsentinel](https://github.com/ossianericson/netsentinel)  
**Proyecto propio:** [JavierGrecco/NetSentinel](https://github.com/JavierGrecco/NetSentinel)  
**Estado:** análisis del código publicado y propuesta de evolución. No se instaló ni ejecutó el producto de referencia.

## Resumen ejecutivo

El proyecto de referencia tiene ideas visuales y de ingeniería que vale la pena estudiar, sobre todo en tres áreas: **mapa interactivo de relaciones de red, geolocalización de IP públicas y métricas históricas**. Su implementación usa un grafo Cytoscape.js, un mapa mundial con datos GeoLite2 y una base SQLite de series temporales. También resuelve detalles importantes como conservar la posición de los nodos, mostrar diferencias entre lecturas, evitar actualizaciones redundantes y detener tareas de fondo al ocultar una pantalla.

Nuestro NetSentinel tiene una base más pequeña y una arquitectura distinta: aplicación web local, FastAPI, SQLite, páginas HTML/CSS/JavaScript, inventario obtenido de fuentes locales, monitorización de objetivos configurados y eventos con procedencia. Ya existe una primera visualización de tendencias de latencia en Monitorización y un verificador responsive con Chromium. No necesitamos volver a construir esas capacidades desde cero.

**Recomendación principal:** adoptar los patrones que mejoren la comprensión de los datos, no reproducir la lista completa de funciones del otro producto. Terminar primero las pruebas de estabilización de la versión actual; después mejorar las métricas existentes, incorporar un grafo LAN con relaciones explicables y valorar un mapa mundial separado solo cuando tengamos direcciones IP públicas procedentes de fuentes reales.

## Qué se revisó y qué no

Se inspeccionaron el README, la documentación de arquitectura, dependencias, árbol de archivos y el código del constructor de grafos, la pantalla de topología, el guardado de posiciones, las diferencias entre capturas, el localizador geográfico, la pantalla de mapa mundial y las consultas de métricas. La documentación del proyecto de referencia anuncia miles de pruebas y muchas herramientas; esas cifras son declaraciones del propio repositorio, no una validación independiente de esta revisión.

Los enlaces al código se incluyen al final para que otra persona del equipo pueda comprobar las conclusiones. El análisis es estático: no se midieron tiempos de arranque, consumo de memoria, resultados reales de detección ni la apariencia del programa en una máquina instalada.

## 1. El grafo de relaciones: la idea más valiosa para nuestra interfaz

La referencia separa la preparación de los datos, el dibujo y la interacción:

- `modules/topology_cytoscape.py` convierte los dispositivos y sus atributos en nodos y enlaces.
- `modules/topology_cytoscape_style.py` define los colores y estilos.
- `modules/topology_cytoscape_html.py` arma la experiencia interactiva con Cytoscape.js.
- `modules/topology_layout.py` guarda posiciones como estado de presentación, en lugar de mezclarlas con las mediciones.
- `modules/topology_snapshot.py` compara dos lecturas y detecta equipos y relaciones que aparecen o desaparecen.
- `modules/network_map_cache.py` guarda los datos usados en la última representación para evitar que el mapa pierda contexto al reiniciar.

El mapa permite elegir diseños, acercar/alejar, ajustar el contenido al área, mover nodos, enfocar un nodo y sus vecinos, mostrar cambios, bloquear posiciones y habilitar un recubrimiento de tráfico cuando la persona lo solicita. La vista interactiva conserva una alternativa clásica cuando WebEngine no está disponible.

### Qué deberíamos incorporar

**Primera versión del grafo LAN**

- Una vista “Mapa de red” que pueda abrirse desde el inventario, sin sustituir ni desplazar la tabla existente.
- Un nodo por activo conocido, con etiquetas breves. Al seleccionarlo, mostrar IP, MAC cuando exista, nombre, fabricante si está disponible, último avistamiento, fuente y estado medido.
- Controles sencillos: ajustar al área, zoom, centrar selección, buscar activo y filtrar dispositivos conocidos/desconocidos.
- Guardar posiciones para que el usuario no tenga que ordenar el mapa después de cada actualización.
- Más adelante, superponer cambios entre lecturas guardadas, siempre que los dos conjuntos de datos sean comparables.
- Mantener el mapa utilizable con teclado, una leyenda comprensible, alternativa en forma de lista y diseño adaptable a pantallas pequeñas.

Cytoscape.js parece una opción razonable si necesitamos mover nodos, organizar el grafo y resaltar vecinos. Antes de incorporarlo, fijar una versión concreta, conservar sus avisos de licencia y guardar el recurso localmente para no depender de una CDN ni de Internet al abrir la aplicación. Para una vista pequeña y estática también sería posible comenzar con SVG; la elección debe basarse en pruebas de interacción y rendimiento, no en sumar una dependencia porque sí.

### Una distinción fundamental: relación observada frente a relación inferida

Nuestro descubrimiento actual obtiene vecinos de tablas locales del sistema operativo. Eso puede demostrar que se observó una combinación IP/MAC, pero **no siempre permite afirmar qué puerto de switch, punto de acceso o cable conecta físicamente cada equipo**.

En un primer grafo, no debemos dibujar una línea como si fuera un enlace físico confirmado cuando solo conocemos que el equipo apareció en la misma red. Cada relación debería tener un tipo explícito, por ejemplo:

- **Observada:** la fuente realmente reportó esa relación.
- **Inferida:** la aplicación la dibuja como contexto a partir de una regla declarada.
- **Desconocida:** la información disponible no permite determinar el vínculo.

La relación también debería indicar fuente y hora de observación. Si el grafo usa una puerta de enlace como centro por comodidad visual, la interfaz tiene que dejar claro que la línea no demuestra por sí sola una conexión física directa. Un enlace punteado o una etiqueta de “relación inferida” es preferible a una certeza falsa.

## 2. El mapa del mundo: otra función, no otra vista del inventario LAN

La referencia incluye una vista mundial para **direcciones IP públicas** vinculadas a inteligencia de amenazas, exposición a Internet o entradas manuales. No es una ubicación exacta de todos los equipos de la red local.

El código consulta una base GeoLite2 local y omite direcciones privadas o especiales. Los puntos pueden agruparse cuando están cerca en pantalla; al elegir uno, la interfaz muestra país/ciudad aproximados, categoría y datos vinculados. Puede dibujar líneas entre una dirección de referencia y las IP marcadas como amenaza.

### Qué deberíamos tomar de esa idea

- Mantener separado el mapa geográfico del grafo de la red local.
- Mostrarlo solo si existe una fuente real de IP públicas —por ejemplo, un hallazgo o una señal de exposición— que tenga utilidad para investigar.
- Al seleccionar una marca, abrir la evidencia original: fuente, hora, categoría, motivo de la relación y acción sugerida.
- Diferenciar “ubicación aproximada de una IP” de la ubicación real de una persona, dispositivo o atacante.
- Dejar claro cuándo faltan coordenadas o la base geográfica no está disponible, en lugar de colocar puntos ficticios.

Las direcciones como `192.168.x.x`, `10.x.x.x` y `172.16.x.x`–`172.31.x.x` son privadas: no deberían aparecer en un mapa mundial como si tuvieran una ubicación pública. Una ubicación GeoIP también puede representar un punto aproximado del proveedor o de su infraestructura; no demuestra que una actividad maliciosa se haya originado exactamente allí.

La referencia conserva la base geográfica por separado y documenta sus condiciones de licencia. Para nuestro producto no conviene descargar una base grande de un tercero en segundo plano ni remitir cada IP a un geolocalizador externo. Si más adelante se implementa esta vista, primero debemos definir fuente autorizada, licencia, procedencia del archivo, actualización, tamaño, controles de descarga y comportamiento sin base local.

**Prioridad propuesta: posterior al grafo y a las métricas.** La pantalla mundial no debería ser un adorno con ubicaciones de ejemplo ni una promesa si todavía no existe un origen real de IP públicas.

## 3. Métricas: primero aprovechar lo que nuestro proyecto ya sabe medir

La referencia persiste muestras de latencia y otras series temporales y usa consultas agregadas para recuperar promedios y tendencias sin enviar todo el historial a la interfaz. Su puntuación general de salud combina disponibilidad, alertas y latencia; es una idea visual atractiva, pero un número compuesto puede inducir a error si faltan datos o el usuario desconoce los pesos.

Nuestro NetSentinel ya tiene consulta histórica de comprobaciones, datos por monitor, promedios, mínimos y máximos de latencia, recuentos de resultados, incidentes y exportación CSV. La pantalla de Monitorización ya dibuja tendencias de latencia con barras, incluidas ventanas históricas agrupadas. La oportunidad inmediata consiste en hacer esa información más fácil de interpretar, no en implementar otra base de métricas.

### Mejoras recomendadas para el panel y Monitorización

1. **Tendencia temporal más legible.** Una línea para la latencia y una representación separada de fallos/disponibilidad; rangos 1 h, 24 h y 7 d solo donde tengamos datos suficientes.
2. **Contexto visible.** Indicar intervalo, cantidad de mediciones válidas, última comprobación, período sin datos y objetivo consultado.
3. **Estados honestos.** Separar “correcto”, “degradado”, “sin respuesta”, “no comprobado” y “sin datos suficientes”. Un hueco de medición no equivale a cero latencia ni a una caída.
4. **Comparación útil.** Resaltar cambios frente a una ventana anterior comparable si existe evidencia suficiente; no inventar un porcentaje cuando el denominador es cero.
5. **Navegación desde el resumen.** Poder pasar desde una anomalía visible a las comprobaciones e incidentes que la respaldan.
6. **Accesibilidad.** No depender solo del color; usar ejes/unidades, leyenda, nombres accesibles y un resumen tabular que se pueda leer sin interpretar un gráfico.
7. **Coste acotado.** Agrupar en SQLite por intervalos y consultar solo el rango solicitado. No cargar miles de registros crudos en el navegador si una consulta agregada resuelve la misma pregunta.

Conviene aplazar una nota global de salud hasta definir y documentar sus factores, pesos, disponibilidad mínima y tratamiento de datos incompletos. Si se incorpora, hay que mostrar qué contribuyó al resultado y qué fuentes faltan; nunca presentarla como una certificación de seguridad.

## 4. Arquitectura y rendimiento: patrones que merece la pena reutilizar

El otro proyecto está escrito para una aplicación de escritorio Qt y usa trabajadores de fondo, un almacén SQLite de series temporales y un grafo web embebido. Nuestro producto es una aplicación web local. **No recomiendo migrar a PyQt, copiar sus módulos completos ni convertir nuestro panel en una aplicación de escritorio.** Sí conviene adoptar sus límites de responsabilidad.

| Patrón de la referencia | Aplicación posible en nuestro proyecto |
|---|---|
| Construcción del grafo separada de la vista | Un servicio transforma activos y relaciones en un contrato de datos; el navegador se ocupa de dibujarlo. |
| Estilos del grafo separados | Leyenda, colores de estado y estilos mantenidos en un único módulo visual. |
| Posiciones del grafo guardadas aparte de las mediciones | Persistir posiciones como preferencia de presentación, no como evidencia de red. |
| Instantáneas y diferencias entre lecturas | Comparar inventarios solo si hay capturas persistidas con fecha y procedencia. |
| Consultas SQL agregadas | Resumir ventanas temporales con consultas limitadas y evitar cargar todo el historial. |
| Actualización incremental y descarte de redibujos idénticos | No reconstruir el grafo cuando los datos relevantes no cambiaron. |
| Trabajadores que se detienen al abandonar una página | Si más adelante hay sondeos o gráficos en vivo en el navegador, cancelar temporizadores y peticiones al ocultar/desmontar la vista. |
| Recursos visuales locales y fallback | Evitar dependencias de CDN en tiempo de ejecución y ofrecer estados de error vacíos comprensibles. |

La propia referencia documenta una incidencia real en la que un trabajador de ancho de banda y el renderizador del mapa seguían activos al abandonar la página. Es una advertencia útil: las visualizaciones en vivo requieren un ciclo de vida explícito, cancelación y mediciones de memoria, además de una apariencia atractiva.

## 5. Lo que no deberíamos copiar sin una necesidad demostrada

El repositorio de referencia también incluye captura de paquetes, funciones que requieren permisos de administrador, pruebas de credenciales, múltiples adaptadores de router, automatizaciones y numerosas herramientas especializadas. Que estén disponibles allí no significa que debamos sumarlas todas.

Para nuestro proyecto, toda nueva fuente debe tener un caso de uso claro y documentado. Antes de implementar tráfico, DNS de router o flujos, hay que identificar el dispositivo o servicio compatible, el permiso requerido, qué campos devuelve, cómo se habilita y deshabilita, cómo se limita su alcance y qué datos quedan almacenados.

No debemos declarar causa raíz, compromiso o atribución geográfica a partir de una única señal débil. Una MAC desconocida, un ping fallido, una IP marcada por una fuente o una ubicación GeoIP son indicios que requieren contexto, no una conclusión automática.

## 6. Comparación con nuestro NetSentinel

Nuestro proyecto tiene varias piezas que nos permiten avanzar de forma progresiva:

- El inventario y los eventos aportan los primeros nodos y observaciones del grafo.
- La procedencia de los vecinos detectados permite identificar de qué fuente viene cada observación.
- Monitorización ya conserva comprobaciones e incidentes y ofrece métricas agregadas.
- La arquitectura separada por routers, repositorios y servicios permite añadir capacidades sin concentrar toda la lógica en una página.
- La prueba responsive con Chromium, integrada en CI, es una base adecuada para comprobar las cinco páginas con distintos tamaños de ventana.

La diferencia más relevante no es que nos falten “miles de funciones”; es que aún no ofrecemos esas relaciones y tendencias mediante unas visualizaciones de investigación claras, y no tenemos en todas las áreas la misma profundidad de historial o fuentes de infraestructura que muestra la referencia.

## 7. Propuesta de prioridades

El orden recomendado es deliberado. La estabilización actual sigue siendo el primer compromiso del proyecto.

### Primero — cerrar la estabilización actual

Completar los recorridos manuales pendientes en Windows, macOS y Linux y registrar la evidencia en la matriz existente. Mantener las pruebas de navegador, exportaciones, persistencia, privacidad y recuperación en la puerta de salida de la versión. La documentación de este análisis no cuenta como validación manual de la aplicación.

### Después — mejorar las métricas existentes

- Refinar la presentación del historial de latencia y la disponibilidad.
- Añadir resúmenes legibles de período, muestra y datos faltantes.
- Unificar los estados vacíos, errores y unidades.
- Validar accesibilidad, tamaños, cambios de tema y carga con datos sintéticos de prueba.

**Criterio de aceptación:** un usuario puede detectar un cambio importante y abrir las mediciones que lo explican; el gráfico no muestra datos inventados ni oculta períodos sin observaciones.

### Siguiente — crear el grafo LAN de solo lectura

- Usar únicamente inventario y relaciones con fuente comprobable.
- Distinguir visualmente enlaces observados e inferidos.
- Añadir selección, búsqueda, ajuste al área y guardado de posiciones.
- Preparar el contrato de datos y las pruebas antes de integrar el renderizador.
- Mantener tabla y lista como alternativas legibles si el grafo no es adecuado para el tamaño de pantalla.

**Criterio de aceptación:** cada nodo y enlace visible puede explicarse por datos reales; al faltar información, el usuario ve esa limitación en vez de una topología falsa.

### Más adelante — mapa geográfico de IP públicas

Empezar solo cuando haya un flujo real y autorizado de IP públicas que justifique la pantalla. Resolver antes la fuente geográfica, licencia, actualización y privacidad. Mantener esta función separada del mapa LAN.

**Criterio de aceptación:** cada punto lleva categoría, procedencia, hora y precisión apropiada; las IP privadas no se presentan como ubicaciones mundiales.

### Finalmente — fuentes avanzadas de infraestructura

Valorar una primera integración de solo lectura con un router, controlador o fuente de logs concreta, si resuelve una necesidad demostrada. No implementar una capa genérica de plugins, captura continua o acceso remoto hasta contar con alcance, permisos, retención y diseño de seguridad definidos.

## 8. Barras de calidad para cualquier nueva visualización

- [ ] Se apoya en datos reales y muestra la fuente y el momento de observación.
- [ ] Distingue los hechos de las inferencias y declara lo que no puede saberse.
- [ ] Tiene estados vacíos, error, carga y datos desactualizados.
- [ ] No requiere Internet para mostrar los datos locales ya disponibles.
- [ ] No envía direcciones ni inventarios a servicios externos sin una decisión explícita y documentada.
- [ ] No carga el historial completo para representar una ventana pequeña.
- [ ] Funciona con teclado, contraste adecuado, leyendas textuales y alternativas no gráficas.
- [ ] Se adapta a móvil, ventana intermedia y escritorio sin provocar desplazamiento global horizontal.
- [ ] Tiene pruebas deterministas con fixtures sintéticos, más una revisión visual documentada.
- [ ] Actualiza la guía de uso, las limitaciones, la matriz de validación y el historial de cambios.

## Fuentes revisadas

### Proyecto de referencia

- [README y catálogo de funciones](https://github.com/ossianericson/netsentinel/blob/main/README.md)
- [Arquitectura](https://github.com/ossianericson/netsentinel/blob/main/docs/architecture.md)
- [Constructor del grafo](https://github.com/ossianericson/netsentinel/blob/main/modules/topology_cytoscape.py)
- [Interfaz web del grafo](https://github.com/ossianericson/netsentinel/blob/main/modules/topology_cytoscape_html.py)
- [Posiciones persistidas](https://github.com/ossianericson/netsentinel/blob/main/modules/topology_layout.py)
- [Instantáneas y diferencias de topología](https://github.com/ossianericson/netsentinel/blob/main/modules/topology_snapshot.py)
- [Caché de representación del mapa](https://github.com/ossianericson/netsentinel/blob/main/modules/network_map_cache.py)
- [Página interactiva de topología](https://github.com/ossianericson/netsentinel/blob/main/ui/pages/network_map_page.py)
- [Mapa geográfico](https://github.com/ossianericson/netsentinel/blob/main/ui/pages/geo_map_page.py)
- [Localizador GeoLite2](https://github.com/ossianericson/netsentinel/blob/main/modules/geo_locator.py)
- [Consultas de métricas](https://github.com/ossianericson/netsentinel/blob/main/modules/metric_store_queries_metrics.py)
- [Cálculo de salud](https://github.com/ossianericson/netsentinel/blob/main/modules/health_score.py)
- [Pruebas de caos y uso prolongado](https://github.com/ossianericson/netsentinel/blob/main/docs/chaos-testing.md)

### Nuestro proyecto

- [Arquitectura de NetSentinel](ARCHITECTURE.md)
- [Visibilidad de red y sus límites](NETWORK_VISIBILITY.md)
- [Roadmap maestro](ROADMAP.md)
- [Matriz de validación](VALIDATION_MATRIX.md)
- [Descubrimiento local](../src/netsentinel/discovery.py)
- [Analítica de monitorización](../src/netsentinel/monitoring_analytics_repository.py)
- [Interfaz de tendencias](../src/netsentinel/static/monitors.js)

La revisión deja una dirección clara: **mejor evidencia, mejor lectura visual y mejores decisiones**, sin ampliar la superficie de riesgo ni prometer información que las fuentes no pueden demostrar.
