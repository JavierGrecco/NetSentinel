
# Auditoría del NetSentinel de blacsecurity y qué conviene trasladar

**Fecha:** 16 de octubre de 2026  
**Repositorio analizado:** [blacsecurity/netsentinel](https://github.com/blacsecurity/netsentinel)  
**Revisión del código:** rama `main`, árbol `c4924dbe23a2b990a970395a645481c79e687634`  
**Método:** inspección estática del README, dependencias y código publicado. No se instaló ni ejecutó el programa en una red real.

## Conclusión ejecutiva

Este proyecto tiene una experiencia visual ambiciosa: mapa animado de nodos, actividad de paquetes, estadísticas, alertas, inventario, escaneo de servicios, indicios de vulnerabilidades, prueba de velocidad y consultas OSINT. El grafo puede ser una buena fuente de ideas para mostrar relaciones de tráfico y destacar actividad reciente.

Sin embargo, el repositorio no ofrece garantías suficientes para copiar su diseño de seguridad o dar por verificadas todas sus métricas. Su aplicación está concentrada en un único archivo de aproximadamente 5.900 líneas; varias acciones de impacto están expuestas sin autenticación aparente; la aplicación escucha en todas las interfaces; el origen de los datos cambia según se ejecute con privilegios o sin ellos; y algunas etiquetas de vulnerabilidad se asignan a partir de un puerto abierto, sin confirmar CVE, versión afectada o controles de autenticación.

**Resultado para nuestro producto:** tomar patrones de visualización y lectura rápida, pero no portar el servicio, sus rutas de administración ni sus inferencias. El mejor grafo es el que deja claro qué se observó, en qué momento y mediante qué fuente; no el que dibuja más líneas.

**Estado tras la última revisión:** en la rama `feat/ip-world-map-geoip-2026-10` se añadió una primera vista mundial de IP públicas observadas, con enriquecimiento desde bases GeoLite2 locales opcionales. Esto no cubre todavía el mapa de paquetes TCP/UDP/ICMP en vivo, las fuentes WAN/UPnP ni la inteligencia de amenazas que describe esta referencia. No se importan métricas estimadas ni se presenta una IP geolocalizada como la ubicación exacta de una persona o máquina.

## 1. Qué aporta la interfaz

### Grafo animado de relaciones y tráfico

La aplicación construye un mapa de nodos y conexiones con Canvas, hace circular puntos para representar actividad y permite seleccionar equipos para consultar información relacionada. La idea valiosa es acercar inventario, tráfico reciente y contexto del dispositivo en una misma vista.

La limitación es que el significado de las líneas depende de cómo se obtuvo la información. En modo de captura con Scapy y privilegios elevados, el código puede procesar paquetes IP. En el modo alternativo, `psutil` enumera conexiones de sockets y el código genera un valor estimado para el tamaño de cada registro (`64 + dport % 1400`) en lugar de medir los bytes reales de ese flujo. El gráfico puede parecer igualmente activo en ambos casos aunque la calidad de la medición sea distinta. Véase [PacketCapture](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1037-L1188).

**Qué tomar:** animación discreta, selección de nodos, filtros, leyenda y resumen contextual.  
**Qué corregir en nuestro diseño:** representar el tipo de fuente en el modelo y no presentar datos estimados como si fueran paquetes, bytes o conexiones efectivamente capturados.

### Resumen, alertas y contexto de dispositivo

Las tarjetas del panel ayudan a encontrar rápidamente recuentos, equipos, alertas y datos recientes. Esto respalda una regla útil de UX: primero debe entenderse el estado general; los detalles se consultan al seleccionar un equipo o abrir una vista concreta.

La misma interfaz puede volverse difícil de interpretar si muestra un indicador compuesto sin metodología, confunde advertencias heurísticas con vulnerabilidades confirmadas o deja que la animación domine a los datos. En NetSentinel debemos conservar los resúmenes, pero exponer período, cantidad de observaciones, fuente, frescura y límites.

## 2. Hallazgos de seguridad y operación

### S0/S1 — El servicio no está restringido a la computadora local

El código configura Socket.IO con `cors_allowed_origins="*"`, utiliza una clave de Flask fija (`netsentry_v3_secret`) y arranca el servidor con `host="0.0.0.0"`. En las rutas inspeccionadas no aparece una capa general de autenticación o autorización que proteja la API.

Fuentes: [configuración Flask/Socket.IO](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1825-L1833) y [arranque del servicio](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L5870-L5883).

Escuchar en todas las interfaces significa que, según el firewall y la red de la máquina, otros equipos pueden intentar acceder al panel; CORS abierto no reemplaza autenticación. Esto es especialmente delicado porque el servidor entrega datos de inventario, direcciones, actividad y alertas. No recomiendo usarlo con datos reales en una red compartida sin rediseñar ese límite.

### S0/S1 — Acciones de cambio de red expuestas por HTTP

Las rutas `POST /api/block/<ip>` y `POST /api/unblock/<ip>` cambian el estado y, cuando el programa se ejecuta con privilegios, intentan crear o eliminar reglas mediante `iptables`, `ebtables`, `arptables` y `tc`; el código también puede enviar respuestas ARP construidas por Scapy. Estas acciones se encuentran en [las funciones de bloqueo](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1879-L2084).

No vi una autorización que exija una confirmación privilegiada en el servidor antes de esas acciones. También hay una ruta de reescaneo que crea un hilo por petición y un endpoint GET de prueba de velocidad que puede ejecutar descargas y cargas externas, sin un límite por usuario visible en el código inspeccionado. Eso puede permitir acciones no deseadas o consumo de recursos a clientes que alcancen la aplicación.

**Qué aprender:** una acción con consecuencias debe requerir permiso explícito, alcance validado, confirmación en el servidor, límites, resultado verificable y una forma documentada de deshacerla.  
**Qué no copiar:** bloqueo automático de equipos, manipulación de firewall o envenenamiento ARP desde una interfaz sin un modelo de autorización completo.

### S1 — La etiqueta “vulnerable” es más amplia que la evidencia

`assess_vulns()` asigna severidad a determinados puertos abiertos a partir de una tabla fija. Algunos mensajes sugieren exposición o riesgo, y una regla agrupa los puertos 6379, 27017 y 9200 como “Unauthenticated DB” con severidad crítica sin comprobar la autenticación efectiva ni la configuración del servicio. Véase [evaluación de servicios](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1015-L1034).

Un puerto abierto puede ser una superficie que conviene revisar, pero no demuestra por sí solo una CVE, ausencia de autenticación ni explotación. Esto es especialmente importante en una herramienta de ciberseguridad, porque una severidad exagerada reduce la confianza y provoca fatiga de alertas.

**Qué adoptar:** separar exposición observada, indicio heurístico y vulnerabilidad confirmada; añadir versión/fuente/evidencia cuando estén disponibles y mantener la confianza separada de la severidad. Este enfoque encaja con la Fase 1 de nuestro roadmap.

### S1 — La fuente cambia y la precisión no siempre queda suficientemente diferenciada

En la captura alternativa, el código recorre conexiones de `psutil` y estima el tamaño de cada entrada según el puerto remoto. Los contadores por interfaz de `psutil` sí pueden dar estadísticas agregadas de bytes/paquetes, pero no convierten esos contadores en una medición exacta por dispositivo o flujo. La interfaz debe reflejar esta diferencia en lugar de ofrecer ambas modalidades con el mismo grado de certeza.

El descubrimiento también retorna la primera estrategia que produce resultados, en vez de combinar y deduplicar sistemáticamente todas las estrategias, y su último fallback deriva la dirección de gateway suponiendo que termina en `.1`. Esa suposición no es válida para todas las redes. Véase [NetworkScanner](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L804-L903).

**Qué adoptar:** procedencia visible, confianza explícita, fallback con estados degradados y ninguna dirección de gateway inventada. Nuestro descubrimiento ya documenta su alcance acotado y preserva de qué fuente procede una observación.

## 3. Fiabilidad, mantenimiento y distribución

### Monolito difícil de probar

El árbol público contiene cuatro archivos y concentra escáner, captura, estado global, API, reglas de riesgo y casi toda la interfaz HTML/CSS/JavaScript en `netsentinel.py`. La separación entre la obtención de datos, el modelo y la vista resulta insuficiente para que una corrección acotada tenga una frontera de prueba clara.

No encontré un conjunto de pruebas automatizadas ni workflows de CI en el árbol revisado. Esto no demuestra que nunca se haya probado manualmente; significa que la evidencia reproducible no está publicada junto al código inspeccionado.

**Qué adoptar:** modularización por responsabilidad, contratos de datos, pruebas deterministas, fixtures sin hardware y límites claros entre API, servicios, persistencia y presentación. Nuestro monolito modular y sus verificaciones de dependencias son una base más segura para evolucionar sin reproducir ese acoplamiento.

### Persistencia principalmente en memoria

Inventario, alertas, muestras de tráfico y registros de paquetes se guardan en estructuras globales y colas con tamaño limitado. Eso es válido para una vista efímera de actividad, pero un reinicio elimina el historial que no se haya exportado o persistido por otra vía. No equivale a un historial auditable.

**Qué adoptar:** separar estado efímero en vivo de observaciones históricas persistentes. En nuestro proyecto, SQLite y los repositorios ya ofrecen esa base; no conviene duplicar almacenamiento por cada gráfico.

### Dependencias y recursos externos

El README anuncia captura y análisis avanzado, mientras que `requirements.txt` no incluye Scapy ni Requests, aunque el programa intenta importarlos opcionalmente. El escaneo con Nmap también depende del ejecutable del sistema, y parte de la prueba de velocidad depende de herramientas adicionales. Por eso, una instalación limpia a partir de los pasos documentados no garantiza todas las funciones anunciadas.

La interfaz carga Socket.IO, Chart.js y fuentes desde CDNs externos. Esto introduce dependencia de Internet, reduce la reproducibilidad visual y hace más difícil garantizar el funcionamiento completo sin conexión.

**Qué adoptar:** matriz de capacidades, dependencias opcionales declaradas, degradación explicada y recursos de interfaz locales con versiones conocidas.

### Procedencia del código y licencia

El README de este repositorio menciona una licencia MIT atribuida a `spiderxploit` y recomienda clonar `spiderxploit/netsentinel`, mientras que el repositorio revisado es `blacsecurity/netsentinel`. En el árbol consultado no aparece un archivo `LICENSE` independiente. Esta discrepancia no prueba una infracción, pero impide asumir que todo el código puede copiarse sin comprobar la procedencia y las condiciones aplicables.

No copiamos código del proyecto. Para inspirarnos en patrones basta con analizar el comportamiento y diseñar una implementación propia; antes de reutilizar código literal debe resolverse su licencia y atribución.

## 4. Qué podemos llevar a nuestro proyecto

| Idea de la referencia | Decisión para nuestro NetSentinel |
|---|---|
| Grafo interactivo y selección de nodos | Sí, pero basado primero en las observaciones de inventario realmente disponibles. |
| Nodos animados por actividad | Más adelante, solo con una fuente que mida tráfico real; nada de generar movimiento para simular actividad. |
| Indicadores y alertas a primera vista | Sí, con período, procedencia, muestras y límites visibles. |
| Mapeo de equipos y destinos externos | Solo cuando existan eventos de flujo/DNS reales que sostengan esas relaciones. |
| Detección por puertos | Sí como contexto de exposición en una futura función autorizada y acotada; no como confirmación automática de CVE. |
| Funciones de bloqueo remoto o ARP | No para el producto actual. Requieren otro modelo de amenazas, permisos y validaciones. |
| Captura permanente privilegiada | No como requisito para el inventario; evaluar fuentes concretas y opt-in si hay un caso de uso real. |
| Escaneo automático muy frecuente | No. Mantener el descubrimiento explícito y limitado salvo que se apruebe una política de observación distinta. |

## 5. Decisiones de producto y orden recomendado

1. **Estabilización primero.** Las pruebas manuales de instalación, actualización, persistencia, privacidad y operación siguen siendo una puerta de salida; una nueva visualización no la reemplaza.
2. **Grafo LAN de solo lectura.** La primera versión puede agrupar dispositivos observados por las subredes que reportó una lectura concreta. Una línea significará que la dirección observada cae dentro del rango CIDR registrado; no afirmará que exista un cable, un puerto de switch o una conexión física directa.
3. **Métricas más explicables.** Reutilizar Monitorización y SQLite. Distinguir mediciones reales, huecos, datos antiguos y estados sin comprobar.
4. **Mapa mundial separado.** Evaluarlo únicamente con IP públicas procedentes de una fuente real y autorizada, una base geográfica con licencia apropiada y ubicación declaradamente aproximada.
5. **Fuentes adicionales solo con un contrato probado.** Seleccionar un proveedor de infraestructura concreto, de solo lectura, y exigir fixtures, timeouts, procedencia, límites y gestión de secretos antes de declararlo soportado.

### Criterios para dar por terminada una visualización

- Las relaciones trazables se apoyan en datos de una lectura identificable.
- La falta de datos o una lectura antigua se ve en la interfaz y no se convierte en una conclusión de caída.
- Un resultado heurístico se distingue de una vulnerabilidad confirmada.
- No se envían inventario ni direcciones a servicios externos por defecto.
- La interfaz funciona sin CDNs en tiempo de ejecución y mantiene una alternativa textual accesible.
- Los límites de cantidad de nodos, datos y refrescos son explícitos y probados.
- Hay pruebas con datos sintéticos y se documenta una revisión visual real.

## Fuentes revisadas

- [README del repositorio](https://github.com/blacsecurity/netsentinel/blob/main/README.md)
- [Dependencias declaradas](https://github.com/blacsecurity/netsentinel/blob/main/requirements.txt)
- [Escáner y detección de servicios](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L804-L1034)
- [Captura y representación de actividad](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1037-L1188)
- [API, configuración y acciones de bloqueo](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L1825-L2084)
- [Prueba de velocidad y reescaneo](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L2087-L2340)
- [Mapa y resumen de topología](https://github.com/blacsecurity/netsentinel/blob/main/netsentinel.py#L2337-L2440)
- [Revisión del otro proyecto de referencia](REFERENCE_PROJECT_REVIEW.md)
- [Roadmap del producto](ROADMAP.md)
