# Matriz de adopción de los proyectos de referencia

**Actualizado:** 23 de octubre de 2026  
**Objetivo:** mejorar NetSentinel sin importar afirmaciones de datos que las fuentes no permiten demostrar ni duplicar responsabilidades existentes.

Esta matriz distingue entre patrones que ya están implementados, trabajo pendiente y funciones que descartamos conscientemente. Los proyectos se inspeccionaron de forma estática; las notas sobre ellos no equivalen a una prueba de ejecución en nuestro entorno. Los módulos seleccionados se integraron en `main` mediante #189. Para el estado actual de CI y la aceptación manual, prevalece [PROJECT_STATUS.md](PROJECT_STATUS.md); la checklist local vive en [EXPERT_ACCEPTANCE_LAB.md](EXPERT_ACCEPTANCE_LAB.md).

Para comparar NetSentinel con herramientas especializadas de observabilidad, análisis de tráfico, monitorización empresarial y forense, y ver la estrategia priorizada que resulta de esa comparación, consultá el [análisis comparativo profundo del 23/10/2026](COMPETITIVE_ANALYSIS_2026-10-23.md).

## Del proyecto ossianericson/netsentinel

| Patrón útil | Decisión en NetSentinel | Estado y evidencia |
|---|---|---|
| Separar modelo de topología, proyección del grafo y presentación | Adoptado; el modelo y la API son módulos del servidor, Cytoscape solo presenta | Implementado en `topology_model.py`, `topology_graph.py` y `api/inventory_topology.py`; la UI usa el contrato compartido |
| Construir un grafo interactivo con zoom, foco, selección y filtros | Adoptado con controles y alternativa textual | Integrado en `/network` mediante #189, con pruebas automatizadas responsive. La revisión manual de teclado, lector de pantalla y usabilidad sigue pendiente; consultar `PROJECT_STATUS.md` para los checks del HEAD actual. |
| Mantener contexto al elegir una captura histórica | Adoptado usando observaciones vinculadas al `scan_id` exacto | API `GET /api/scans/{scan_id}/topology`; el servicio no sustituye IP históricas por los últimos valores del inventario |
| Posiciones y estado de presentación persistentes | Adoptar solo como preferencia de UI validada, separada de las mediciones | La UI guarda posiciones localmente; el verificador responsive prueba recuperación tras JSON corrupto, coordenadas válidas y límite de 1200 entradas. La prueba manual de arrastrar, recargar y confirmar persistencia sigue pendiente. Todo cambio nuevo se verifica sobre el SHA actual; ver `PROJECT_STATUS.md`. |
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
| Aplicación concentrada y procedencia/licencia no aclaradas | No reutilizar código literal hasta aclarar licencia y procedencia | La revisión actual confirma que el repositorio tiene cuatro archivos en la raíz, no incluye un archivo `LICENSE` y su README indica clonar `spiderxploit/netsentinel` en vez de `blacsecurity/netsentinel`. Tomamos ideas, no código. |

## Hallazgos de la revisión de referencias (actualización de estado: 23 de octubre de 2026)

### Salud de las fuentes y errores visibles

La versión actual de [ossianericson/netsentinel](https://github.com/ossianericson/netsentinel/commit/e2ab5eebaed9816860a8a807e6154e9eb28c189f) pone el foco en algo que merece adoptarse más allá del grafo: una operación que falla no debe aparecer como correcta, vacía, nunca ejecutada ni saludable. El error debe comunicarse con una explicación y un paso siguiente acordes con su impacto. El estado de salud de una tarea debe mantenerse visible mientras el problema persista y recuperarse cuando una ejecución vuelva a funcionar.

En nuestro proyecto ya existen respuestas HTTP con códigos de error, referencias de seguimiento, clasificación segura y un registro local. No hay que crear otro sistema paralelo. La oportunidad es reutilizarlo cuando llegue el primer adaptador de datos y mostrar, por fuente, al menos:

- Estado legible: disponible, degradado, sin datos recientes o no disponible.
- Hora de la última lectura correcta y, si ocurrió, de la última falla.
- Explicación y acción siguiente sin exponer secretos ni detalles internos.
- Una diferencia inequívoca entre «la fuente informó cero eventos» y «no pudimos consultar o interpretar la fuente».
- Pruebas de regresión para fallo, recuperación, datos vacíos y datos incompletos.

La parte de interfaz de esta referencia se construyó para una aplicación de escritorio; no trasladaremos su implementación de hilos o widgets. NetSentinel debe conservar su separación actual entre servicios, API y presentación web.

### Procedencia del segundo proyecto

La revisión actual de [blacsecurity/netsentinel](https://github.com/blacsecurity/netsentinel/tree/c4924dbe23a2b990a970395a645481c79e687634) vuelve más importante la cautela sobre la reutilización: la raíz publicada contiene `README.md`, `dashboard.png`, `netsentinel.py` y `requirements.txt`; no se encontró un archivo `LICENSE` en la raíz y el README dirige la instalación a `spiderxploit/netsentinel`. Hasta aclarar licencia y procedencia, no copiamos su código. Sí podemos implementar patrones generales de lectura rápida y selección usando nuestros contratos y pruebas.

### Alcance histórico y selección de interfaz

La reconstrucción de una lectura solo puede clasificar un equipo como «no visto» cuando una dirección conocida tiene un intervalo de observación que se solapa con la captura seleccionada y pertenece a una subred cuyo descubrimiento fue completo. Si la dirección apareció después, dejó de observarse antes o carece de fechas fiables, se mantiene fuera de esa conclusión. Si el mismo CIDR figura en varias interfaces, una interfaz completa no compensa el alcance limitado de otra: se exige coincidencia de interfaz cuando el historial de la dirección la identifica; si el origen es ambiguo, se falla de forma conservadora.

## Reglas que no debemos negociar

1. **La evidencia es la fuente de verdad.** El servidor define las observaciones y las relaciones del modelo. La UI puede agrupar visualmente varias IP del mismo dispositivo dentro de una subred, pero no puede inventar relaciones.
2. **La ausencia no es una desconexión.** Solo clasificamos un equipo como “no visto en esta lectura” si alguna IP del inventario pertenece a una subred registrada y el descubrimiento de esa subred no figura como limitado. Los equipos fuera de alcance no se mezclan con esa lectura.
3. **Cada relación tiene significado explícito.** `observed-subnet-membership` indica que una IP observada cae dentro de una subred registrada; no significa tráfico, conexión física ni un enlace directo.
4. **Se distingue el dato de la ficha actual de la evidencia histórica.** Nombre, fabricante y confianza del registro de inventario pueden cambiar y no se presentan como si fueran un histórico inmutable.
5. **Una prueba escrita no equivale a una prueba aprobada.** Los checks solo valen para el SHA que ejecutaron. La integración #189 ya está fusionada en `main`; el estado de CI, Security y Supply Chain debe consultarse para el SHA exacto que vaya a probarse. La revisión manual responsive, de teclado y de lector de pantalla sigue pendiente.
6. **Los validadores de alcance deben coincidir.** La interfaz y el servidor solo aceptan una subred si el rango completo está dentro de RFC 1918; una dirección privada al comienzo de un CIDR no vuelve privado todo el rango.

## Próximos pasos desde la integración en main

1. Consultar en [Actions](https://github.com/JavierGrecco/NetSentinel/actions) los checks del SHA exacto de `main`; no usar una ejecución de una cabeza anterior como señal de aprobación.
2. Ejecutar el asistente `/guided-test` con la base y los archivos sintéticos descritos en [EXPERT_ACCEPTANCE_LAB.md](EXPERT_ACCEPTANCE_LAB.md). Registrar los 12 resultados, el SHA y las incidencias.
3. Revisar el explorador LAN en la lectura sintética; confirmar que los nodos, las relaciones y la procedencia se derivan de la API histórica y no implican tráfico en vivo.
4. Probar teclado, lector de pantalla, persistencia de posiciones, estados vacíos, escritorio y ventana estrecha; registrar las observaciones en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
5. Validar CSV y Zeek primero con registros sintéticos; solo después, si corresponde, usar exportaciones reales autorizadas y sanitizadas. NetSentinel no inicia captura ni instala sensores.
6. Resolver el alcance y los checks obligatorios del ruleset de `main` con la persona administradora en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73). No eliminar ramas mientras ese control siga pendiente.
7. No reabrir PRs duplicadas para los módulos ya integrados. Las mejoras nuevas deben partir del `main` actualizado y entrar por una PR con sus checks y criterios de aceptación definidos.
