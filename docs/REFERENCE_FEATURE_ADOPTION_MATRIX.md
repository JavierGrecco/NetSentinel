# Matriz de adopción de los proyectos de referencia

**Actualizado:** 19 de octubre de 2026  
**Objetivo:** mejorar NetSentinel sin importar afirmaciones de datos que las fuentes no permiten demostrar ni duplicar responsabilidades existentes.

Esta matriz distingue entre patrones que ya están implementados, trabajo pendiente y funciones que descartamos conscientemente. Los proyectos se inspeccionaron de forma estática; las notas sobre ellos no equivalen a una prueba de ejecución en nuestro entorno.

## Del proyecto ossianericson/netsentinel

| Patrón útil | Decisión en NetSentinel | Estado y evidencia |
|---|---|---|
| Separar modelo de topología, proyección del grafo y presentación | Adoptado; el modelo y la API son módulos del servidor, Cytoscape solo presenta | Implementado en `topology_model.py`, `topology_graph.py` y `api/inventory_topology.py`; la UI usa el contrato compartido |
| Construir un grafo interactivo con zoom, foco, selección y filtros | Adoptado con controles y alternativa textual | Integrado en `/network`; pendiente aprobar CI de la revisión final y la revisión manual de accesibilidad |
| Mantener contexto al elegir una captura histórica | Adoptado usando observaciones vinculadas al `scan_id` exacto | API `GET /api/scans/{scan_id}/topology`; el servicio no sustituye IP históricas por los últimos valores del inventario |
| Posiciones y estado de presentación persistentes | Adoptar solo como preferencia de UI validada, separada de las mediciones | La UI ya contempla posiciones; falta confirmar en pruebas de navegador la persistencia, la recuperación de valores dañados y el límite de almacenamiento |
| Comparar capturas y explicar cambios | Adoptar si ambas lecturas y sus alcances son comparables | NetSentinel ya tiene comparación de capturas; no se debe afirmar que un equipo desapareció si la lectura fue incompleta o sus redes no coinciden |
| Métricas de red y mapa geográfico | No mezclarlas con el grafo LAN actual | La telemetría disponible es principalmente inventario/observaciones locales y monitorización configurada. No se asignará geolocalización pública a direcciones privadas ni se simulará tráfico |

## Del proyecto blacsecurity/netsentinel

| Patrón útil | Decisión en NetSentinel | Estado y evidencia |
|---|---|---|
| Resumen visual, lectura rápida y filtros | Adoptado con etiquetas que aclaran su significado | La vista muestra recuentos, filtros y selección; el estado desconocido no se representa como cero confirmado |
| Seleccionar nodos y consultar detalle | Adoptado | El detalle expone la lectura, IP, fuente y alcance de la relación |
| Animar paquetes o destacar actividad reciente | Pospuesto hasta que exista telemetría real adecuada | No se usarán tamaños de paquete inventados ni animaciones que hagan parecer capturado un tráfico que no se midió |
| Indicadores y hallazgos derivados de puertos | No copiar inferencias como vulnerabilidades confirmadas | Un puerto abierto puede justificar revisión, pero no demuestra CVE, explotación ni falta de autenticación. Cada hallazgo debe señalar la evidencia y el nivel de certeza |
| Bloqueo de IP y acciones privilegiadas desde la interfaz | Fuera del alcance de esta integración | Una acción de cambio de red necesita autorización, límites, confirmación del servidor, auditoría y reversión antes de diseñarse |
| Aplicación concentrada y licencia/origen dudoso | No reutilizar código literal sin aclarar licencia y procedencia | Se adaptan ideas de arquitectura y UX; las capacidades nuevas se implementan contra los módulos existentes del proyecto |

## Reglas que no debemos negociar

1. **La evidencia es la fuente de verdad.** El servidor define las observaciones y las relaciones del modelo. La UI puede agrupar visualmente varias IP del mismo dispositivo dentro de una subred, pero no puede inventar relaciones.
2. **La ausencia no es una desconexión.** Solo clasificamos un equipo como “no visto en esta lectura” cuando el alcance de red de esa lectura puede interpretarse.
3. **Cada relación tiene significado explícito.** `observed-subnet-membership` indica que una IP observada cae dentro de una subred registrada; no significa tráfico, conexión física ni un enlace directo.
4. **Se distingue el dato de la ficha actual de la evidencia histórica.** Nombre, fabricante y confianza del registro de inventario pueden cambiar y no se presentan como si fueran un histórico inmutable.
5. **Una prueba escrita no equivale a una prueba aprobada.** Los checks se consideran válidos solo para el SHA que ejecutaron. La PR del explorador permanece como borrador hasta pasar CI, seguridad y cadena de suministro en su cabeza final, además de revisión manual responsive y accesible.

## Próxima secuencia

1. Aprobar CI y analizar los fallos de la revisión más reciente antes de agregar más superficie funcional.
2. Probar el explorador en Chromium con lecturas con varias IP, subredes vacías, alcance desconocido, errores de API, filtros, teclado y móvil.
3. Verificar persistencia de posiciones, preferencias de tema y recuperación tras datos locales inválidos.
4. Revisar el resultado junto con las responsabilidades actuales para no mantener dos fuentes de verdad.
5. Mantener la PR en borrador hasta completar los puntos anteriores.
