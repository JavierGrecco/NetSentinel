# Explorador de red y observabilidad

## Qué problema resuelve

El mapa no debe ser una ilustración decorativa. Debe ayudar a responder, con la evidencia disponible, qué equipos se observaron, qué cambió entre lecturas y qué información falta para investigar un dispositivo.

La experiencia de topología vive en una sección propia, accesible desde **Mapa de red** y la ruta `/network`. El Inventario mantiene su tarea principal y enlaza al explorador en lugar de cargar el grafo pesado dentro de la tabla.

## Qué representa la primera entrega

- Un nodo de subred agrupa las direcciones IP observadas en un rango registrado.
- Un nodo de dispositivo identifica un equipo del inventario e indica si apareció en la lectura elegida, si quedó sin asociación a una subred y si la persona lo marcó como conocido.
- Al seleccionar un dispositivo se muestran IP, MAC, fabricante cuando está disponible, estado, fuente y momento de observación.
- El historial lateral muestra observaciones históricas del equipo, con su hora, IP y fuente.
- La sección «Cambios registrados» muestra eventos del inventario asociados al equipo (por ejemplo, primera detección o cambio de IP). Estos eventos describen lo que NetSentinel observó, no toda la actividad de red del dispositivo.
- **Selector de lectura histórica:** se puede reconstruir el mapa de una captura anterior con las observaciones ligadas a esa lectura, sin reemplazarlas por direcciones actuales del inventario.
- **Contrato único de topología:** la página solicita `GET /api/scans/{scan_id}/topology`. El servidor construye los nodos y las relaciones desde la evidencia guardada; el navegador se limita a aplicar búsqueda, filtros, selección y disposición visual. El endpoint también devuelve procedencia y contadores desconocidos cuando no se puede confirmar el alcance de las subredes.
- Las lecturas sin rangos válidos también se pueden seleccionar. Si hay observaciones pero no hay alcance de red interpretable, se muestran equipos aislados y no se dibujan asociaciones inventadas. La lectura inicial sigue prefiriendo la captura más reciente con subredes válidas.
- Buscar, filtrar, acercar, alejar, ajustar al área y reorganizar el grafo son acciones independientes y tienen etiquetas claras.
- Las posiciones del mapa se guardan localmente como una preferencia de presentación; no se guardan como una nueva observación de red.
- La lista textual permite elegir dispositivos sin depender del mapa visual.

## Qué no representa

La API de topología es de solo lectura. No ejecuta descubrimientos por sí misma ni muta el inventario al reconstruir una lectura.

La primera entrega no es una captura de paquetes ni una vista de tráfico en vivo. Una línea no significa que dos dispositivos intercambiaron tráfico, que estén conectados directamente por un cable o que se conozca el puerto de switch. La ausencia de un dispositivo en una lectura tampoco demuestra que esté desconectado.

Los datos actuales permiten consultar observaciones del inventario y pruebas de disponibilidad contra objetivos configurados. No permiten afirmar qué aplicación usó un equipo, qué página visitó ni cuántos bytes generó por dispositivo.

## Hacia dónde debe crecer

### Etapa A — Investigación LAN

Completar mapa, detalle de activo, historial, comparación de lecturas, procedencia y filtros. La página `/network` incluye un panel que compara dos capturas usando la API histórica existente y exige al menos una subred privada compartida. Mantener una alternativa textual y validar escritorio, móvil, teclado y lectores de pantalla.

### Etapa B — Actividad por dispositivo

Antes de dibujar conexiones entre dispositivos, definir un contrato de evento común. Cada evento debe conservar origen de datos, hora original y normalizada, IP de origen/destino, protocolo y contadores solo cuando la fuente realmente los proporcione. Debe mostrar alcance, retraso, errores, retención y campos desconocidos.

Las integraciones se diseñarán como adaptadores separados, inicialmente de solo lectura: registros DNS autorizados y, si la infraestructura los ofrece, flujos de conexión (NetFlow/IPFIX u otro formato documentado). No asumir que un router genérico expone estas fuentes ni instalar agentes de manera implícita.

### Etapa C — Investigación de cambios

Comparar dos lecturas compatibles, destacar equipos que aparecen o dejan de aparecer y cambios de dirección, y enlazar cada conclusión con la observación original. La interfaz debe evitar tratar ausencia o datos antiguos como fallos confirmados.

### Etapa D — Vistas especializadas

Mantener la topología LAN separada de un eventual mapa geográfico de IP públicas. Una vista geográfica solo se incorporará cuando haya fuentes públicas reales, una base geográfica con licencia adecuada y un mensaje claro sobre precisión aproximada.

## Biblioteca de grafo

La UI usa una copia local versionada de Cytoscape.js `3.34.4`, publicada bajo MIT. La aplicación no depende de una CDN para dibujar el mapa. Se conserva el aviso de copyright y la licencia distribuida con el paquete. La biblioteca organiza y dibuja los elementos que entrega NetSentinel; no aporta por sí misma evidencia de red.

## Puerta de calidad antes de mostrar el proyecto a expertos

No declarar maduro el producto hasta cumplir, como mínimo:

- Pruebas automáticas de modelo, filtros, estados, accesibilidad y recursos locales.
- Recorridos reales documentados en Windows, macOS y Linux.
- Validación manual en escritorio, móvil, teclado y contraste en los tres temas.
- Un caso de investigación de inicio a fin con datos sintéticos reproducibles.
- Para la vista de actividad por dispositivo, una fuente real autorizada y evidencia que permita reproducir cada evento mostrado.
- Mensajes comprensibles cuando no existen datos, una fuente queda fuera de línea o un campo no puede verificarse.

Seguimiento de este frente: [issue #170](https://github.com/JavierGrecco/NetSentinel/issues/170).
