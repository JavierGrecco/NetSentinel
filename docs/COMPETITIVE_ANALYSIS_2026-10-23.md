# Análisis comparativo de NetSentinel y herramientas de observabilidad y seguridad

**Fecha de revisión:** 23 de octubre de 2026  
**Repositorio evaluado:** [JavierGrecco/NetSentinel](https://github.com/JavierGrecco/NetSentinel)  
**Base consultada:** `main`, merge de documentación `53d5a6a2d383af3b5991dc12d20f99e04c3d78dd`  
**Método:** revisión estática de código, arquitectura, README, matrices de adopción y documentación pública de los proyectos comparados. No se instalaron ni ejecutaron los productos competidores en una red real. Sus descripciones de funciones y cifras de pruebas se tratan como afirmaciones publicadas por sus autores, no como resultados verificados de forma independiente.

## 1. Conclusión ejecutiva

NetSentinel no lidera hoy el mercado por profundidad de inspección de tráfico, cobertura de hardware, automatización empresarial ni madurez forense. No sería serio compararlo en igualdad de condiciones con Zeek, Arkime, ntopng, Security Onion o plataformas de monitorización distribuida: esas herramientas operan con sensores, captura de paquetes, flujos, numerosos protocolos, servidores de análisis o despliegues pensados para redes mucho mayores.

Eso no significa que debamos copiar sus tamaños o arquitecturas. Pero la comparación ampliada también muestra que **operar localmente no alcanza por sí solo como diferencial**: NetAlertX combina inventario local, descubrimiento continuo, historial de cambios, alertas y sincronización multi-sitio; Uptime Kuma es fuerte en monitorización simple y notificaciones. Hay que competir por la calidad del flujo de investigación, no solo por el despliegue local.

> **Propuesta de valor:** una herramienta de primera respuesta para que un operador autorizado entienda qué dispositivos se observaron, qué cambió, qué comprobaciones fallaron y qué evidencia conviene revisar, con procedencia explícita, límites honestos y reportes portables.

La base técnica ya ofrece piezas valiosas para esa promesa: inventario local, observaciones históricas, mapa LAN basado en capturas, monitorización de disponibilidad, hallazgos de inventario/incidentes, importación manual y acotada de `conn.log` de Zeek, mapa geográfico opcional basado en GeoIP local y un espacio de casos forenses en desarrollo. El producto está construido alrededor de una aplicación web local y SQLite, con páginas y servicios modulares.

La brecha más valiosa no es agregar diez escáneres nuevos. Es unir mejor las funciones actuales para que el usuario pueda pasar de **observación → contexto → evidencia → próximo paso → informe verificable** sin que la interfaz invente tráfico, atribuya causalidad o transforme una señal débil en una alerta de ataque.

Hay dos condiciones previas que no deben diluirse en más desarrollo: cerrar la aceptación manual y accesible de la versión 0.10.0, y verificar administrativamente la protección real de `main`. Los checks verdes son necesarios, pero no sustituyen ninguna de las dos tareas. Seguimiento: [#75](https://github.com/JavierGrecco/NetSentinel/issues/75) y [#195](https://github.com/JavierGrecco/NetSentinel/issues/195).

## 2. Qué comparamos y cómo interpretar la tabla

Las herramientas siguientes no pertenecen todas a la misma categoría. Se incluyen para comparar fortalezas de mercado y decidir dónde conviene integrar, aprender o no competir directamente.

| Proyecto | Donde sobresale | Comparación con NetSentinel | Decisión |
|---|---|---|---|
| [ossianericson/netsentinel](https://github.com/ossianericson/netsentinel) | Aplicación de escritorio local con inventario, diagnóstico de conectividad, topología, seguimiento de estabilidad, funciones Wi-Fi y herramientas de aprendizaje. El repositorio publicado describe una cobertura funcional amplia. | Es la referencia más próxima por la intención local y por combinar inventario, diagnóstico y lectura visual. Publica muchas más funciones de sondeo y análisis activo; algunas dependen de privilegios, Npcap/libpcap u otras condiciones del sistema. | Aprender de su salud operativa, secuencia de diagnóstico, mapa y timeline. No perseguir su cantidad de funciones ni asumir que sus mediciones existen en nuestras fuentes. Ver también su [referencia de funciones](https://ossianericson.github.io/netsentinel/feature-reference/). |
| [blacsecurity/netsentinel](https://github.com/blacsecurity/netsentinel) | Panel de resumen, mapa animado de nodos, descubrimiento, alertas, análisis de puertos y consultas OSINT declaradas en el README. | La revisión del repositorio consultado encontró solo cuatro archivos en el árbol de raíz y un único archivo Python principal; el README recomienda clonar `spiderxploit/netsentinel`, y no se encontró un archivo `LICENSE` en la raíz de la revisión. Además, su modo alternativo de actividad no equivale necesariamente a bytes capturados. | Tomar ideas de jerarquía visual, filtros y selección contextual, no copiar código hasta aclarar la licencia/procedencia ni mostrar actividad estimada como tráfico medido. La matriz existente detalla la revisión técnica. |
| [NetAlertX](https://github.com/netalertx/NetAlertX) | Descubrimiento continuo de activos, seguimiento de cambios de presencia/IP, fuentes ARP/DHCP/SNMP/controladores, plugins, workflows, notificaciones y sincronización multi-sitio, según su documentación pública. | Es un competidor directo más cercano de lo que sugiere una comparación solo con herramientas SOC: cubre buena parte del uso de inventario, conocimiento de LAN y alertas, con enfoque de despliegue autocontenido/self-hosted. No medimos su precisión o rendimiento de forma independiente. | No afirmar que local-first es único ni perseguir paridad de plugins. Diferenciarse mediante cronología de evidencia enlazada entre dominios, alcance histórico comparable, explicación de incertidumbre y flujo guiado de diagnóstico; estudiar sus adaptadores sólo para fuentes que nuestros usuarios realmente necesitan. |
| [Nmap](https://nmap.org/book/man-host-discovery.html) | Herramienta especializada de descubrimiento activo, con varios tipos de sondas para identificar hosts y funciones de escaneo adicionales. La documentación oficial subraya que el alcance y las técnicas deben seleccionarse según el objetivo. | Nuestra detección actual, limitada a redes privadas y basada en la tabla local de vecinos, es más acotada y no equivale a la amplitud de sondeo de Nmap. Nmap también genera tráfico de prueba y requiere autorización explícita y control de alcance. | No envolver Nmap automáticamente ni ampliar escaneos solo para inflar cobertura. Valorar un adaptador opcional, acotado y de solo lectura si una necesidad comprobada lo justifica; antes definir autorización, rangos completos permitidos, límites, timeout, cancelación y registro de la técnica. |
| [ntopng](https://www.ntop.org/products/traffic-analysis/ntopng/) | Inspección de tráfico y flujos, protocolos de aplicación, retransmisiones, latencia, top talkers, SNMP, captura y exportación histórica. | Está mucho más cerca de una herramienta dedicada a analítica de tráfico. Necesita fuentes de captura/interfaz o flujos que NetSentinel no obtiene por defecto. | No replicar DPI, captura ni análisis de rendimiento en esta etapa. Diseñar adaptadores para importar metadatos de una fuente real cuando exista un caso de uso claro. |
| [Zeek](https://zeek.org/) | Análisis pasivo y extensible de protocolos; registros estructurados de conexiones y actividad de protocolos para investigación y otras herramientas. | Es un motor/monitor de red, no un panel local de onboarding ni una interfaz de aceptación para usuarios nuevos. NetSentinel ya admite importación explícita de registros de conexión, pero no ejecuta Zeek ni captura tráfico. | Aprovecharlo como fuente especializada y respetar sus campos, tiempo y procedencia. No declarar que tenemos monitorización en vivo por admitir un archivo Zeek. |
| [Arkime](https://arkime.com/) | Búsqueda de sesiones, indexación y consulta de metadatos de tráfico; guarda y permite revisar PCAP, con capacidades diseñadas para escalar. | Su profundidad y su capacidad de volver al paquete original superan la actual evidencia estructurada de NetSentinel. También conlleva necesidades de almacenamiento, indexación y operación distintas. | Integrar informes/enlaces o formatos interoperables cuando aporten valor; no reconstruir su motor de captura/índice dentro de la aplicación local. |
| [Malcolm](https://malcolm.fyi/docs/) | Plataforma integradora para PCAP, logs Zeek y sesiones Arkime, enriquecimiento, búsqueda y dashboards para investigación de tráfico. | Es una plataforma de análisis de red desplegable, no un reemplazo directo de una herramienta local de evaluación simple. | Usarla como referente para una futura interoperabilidad y enriquecimiento gobernado; no convertir nuestra instalación ligera en una pila distribuida por defecto. |
| [Security Onion](https://docs.securityonion.net/en/3/dev/introduction/) | Plataforma amplia de visibilidad de red y host, detección, registros, hunting y gestión de casos, combinando herramientas especializadas. | Su alcance supera claramente al de nuestro producto y exige otra escala de operación y conocimiento. | No presentarnos como SOC, SIEM, EDR o NDR completo. Definir exportación/integración con herramientas especializadas antes de duplicar sus funciones. |
| [LibreNMS](https://docs.librenms.org/Support/Features/) | Autodescubrimiento, SNMP y otros protocolos de gestión, alertas, tablas VLAN/ARP/FDB, flujos y polling distribuido. | Excelente referencia para monitorización y telemetría de infraestructura administrada; tiene una amplitud de fabricantes y operación central que no tenemos. | Evaluar SNMP, syslog o flujos solo a partir de una necesidad comprobada, credenciales mínimas y un dispositivo de referencia concreto. |
| [OpenNMS](https://www.opennms.com/platform/) | Gestión de fallos y rendimiento, monitorización de servicios, protocolos de datos, flujos, topología e implementación distribuida. | Más robusto para infraestructura grande, con mayor complejidad y requisitos operativos. | Aprender de los contratos de métricas y los informes, pero mantener nuestro producto simple y local en la etapa actual. |
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | Monitorización self-hosted de HTTP(S), TCP, ping, DNS, WebSocket y otros tipos de objetivos, con páginas de estado y muchos canales de notificación, según el README del proyecto. | Se solapa con nuestros monitores de disponibilidad HTTP/TCP/Ping y compite en la sencillez de operación y notificaciones; está más orientado a uptime y páginas de estado que al historial del inventario y la evidencia de red. | No perseguir cantidad de canales antes de cerrar el flujo principal. Evaluar compatibilidad o exportación de estados/alertas cuando haga falta interoperar, y mejorar primero la explicación del incidente y su relación con un activo observado. |
| [Prometheus](https://prometheus.io/docs/introduction/overview/) | Scraping y almacenamiento local de series numéricas, reglas de agregación/alertas y consulta de métricas etiquetadas. | Es una capa de métricas complementaria, no un reemplazo para la historia de dispositivos ni la evidencia del registro original. La exportación de métricas no debería volcar IDs/IP/URLs arbitrarias como etiquetas de alta cardinalidad. | Dejar la salida Prometheus como integración futura para métricas operativas acotadas; diseñar nombres estables y cardinalidad limitada. No añadir un servidor Prometheus como dependencia obligatoria. |
| [NetBox](https://netboxlabs.com/docs/netbox/) | Fuente de verdad de infraestructura: sitios, dispositivos, conexiones, prefijos IP, IPAM/DCIM, APIs y extensiones. Sus propias guías distinguen la documentación del estado deseado de la monitorización operativa. | Resuelve un problema complementario: modelar lo que debería existir no es lo mismo que observar qué apareció en una lectura. | En el futuro, permitir comparación de inventario observado con una fuente de verdad, sin sobrescribir automáticamente ninguno de los dos estados. |
| [Wireshark](https://www.wireshark.org/about) | Análisis de paquetes en vivo o desde archivos, con gran profundidad de protocolos y revisión granular. | El detalle de paquete que provee no existe en nuestras observaciones de inventario ni en todas las fuentes importadas. | Ofrecer exportación y documentación que permitan continuar un análisis en Wireshark cuando se trabaje con PCAP autorizado; no simular una vista de paquetes. |

### Resultado de la comparación

- **Referencias de intención más cercana:** el NetSentinel de ossianericson y NetAlertX. Este último ya ofrece descubrimiento continuo, historial de cambios, alertas, integraciones por plugin y sincronización de redes; por eso local-first es una base valiosa, pero no una exclusividad competitiva.
- **Referencia visual con precauciones fuertes:** blacsecurity/netsentinel. No copiar código cuya licencia/procedencia no está clara ni inferencias que no respalde la fuente.
- **Complementos especializados:** Nmap para descubrimiento activo autorizado; Uptime Kuma para la simplicidad de uptime; ntopng, Zeek, Arkime, Malcolm, Security Onion y Wireshark para análisis especializado. No necesitamos duplicar todas sus tareas dentro de la aplicación.
- **Referencias de infraestructura:** LibreNMS y OpenNMS para telemetría y operación distribuida; Prometheus para métricas agregadas de baja cardinalidad.
- **Referencia de inventario declarado:** NetBox, manteniendo separado el estado esperado del estado observado.

Las funciones y riesgos se resumen desde documentación y código públicos accesibles. No se compararon precisión ni rendimiento bajo una prueba común; la tabla no es un ranking cuantitativo.

## 3. Diagnóstico de nuestro nivel actual

La siguiente matriz describe el estado observable del código y la documentación propia, no una calificación comercial.

| Área | Estado actual | Evaluación honesta | Qué elevaría la madurez |
|---|---|---|---|
| Privacidad y ejecución local | Aplicación local con SQLite; exportaciones e integraciones son explícitas; la actividad del navegador requiere opt-in y transferencia manual. | **Fortaleza de diseño**, que debe seguir comprobándose en cada nueva fuente. No equivale a una auditoría externa de privacidad. | Inventario visible de datos recogidos por fuente, previsualización de exportación, controles de retención/borrado consistentes y pruebas negativas de salida de datos. |
| Inventario y cambios de red | Descubrimiento IPv4 privado acotado, consulta de la tabla local de vecinos, historiales y cambios observados. | **Útil para primera evaluación de LAN**, no descubrimiento exhaustivo. La ausencia en una lectura no confirma desconexión; no cubre redes exclusivamente IPv6 ni detecta todos los dispositivos. | Mostrar completitud de cada lectura, interfaces/rangos consultados, límite aplicado, frescura y motivos de datos ausentes. Seleccionar futuras fuentes adicionales por demanda real. |
| Topología LAN | Mapa dedicado, reconstrucción histórica a partir de una lectura y diferenciación entre relaciones observadas e inferidas. | **Diferencial visual potencial**; un grafo no prueba cableado, topología física ni comunicación entre equipos sin la fuente correspondiente. | Mantener clasificación observada/inferida/desconocida, verificación de teclado/lector de pantalla, conservar contexto y mostrar por qué se dibuja cada arista. |
| Mapa geográfico de IP | Vista mundial con GeoLite2-City local opcional. | **Contextualización aproximada de IP públicas**, no geolocalización precisa ni localización física de una persona. La base autorizada debe estar instalada y vigente. IP privadas no se deben ubicar geográficamente con este método. | Explicar precisión y fuente en leyenda, mostrar fecha/versión de la base y no renderizar el mapa como si hubiera localizaciones cuando faltan datos. |
| Disponibilidad | Controles Ping/TCP/HTTP(S), incidentes, muestras e historial con retención configurable y notificaciones webhook opcionales. | **Base útil de observabilidad de servicios configurados**, distinta del monitoreo universal de dispositivos o interfaces SNMP. | Informes sencillos de interrupciones, umbrales explicados y separación de falla del destino, error del monitor y falta de datos. |
| Actividad y tráfico | Importación manual de CSV/metadatos autorizados y `conn.log` de Zeek con validación, límites, deduplicación y vista previa. No ejecuta Zeek ni inicia captura de tráfico. | **Interoperabilidad inicial**, no un sensor de red. Los campos ausentes siguen siendo desconocidos; el período, la perspectiva y el dispositivo seleccionado condicionan la interpretación. | Mostrar siempre observado vs. importado, hora original vs. ingreso, alcance de IP, identidad de origen y dirección de la conexión; mejorar la navegación hasta la evidencia original. |
| Hallazgos | La vista unificada actualmente normaliza eventos de inventario e incidentes de monitorización con fuente, evidencia, confianza, limitaciones y acción sugerida. | **Triaje inicial, todavía sin correlación entre fuentes**. El propio módulo aclara que no atribuye causas ni crea detecciones nuevas. | Primer enlace de evidencia entre el inventario/monitorización y actividad Zeek autorizada, con criterios reproducibles y semántica temporal explicada. Seguimiento: [issue #197](https://github.com/JavierGrecco/NetSentinel/issues/197). |
| Forense | Casos, metadatos de recepción, eventos de auditoría enlazados por SHA-256, manifiestos e informes versionados; copia de trabajo local para comparar hashes. | **Prototipo funcional experimental**, no custodia validada. Un hash no autentica operadores ni evita que quien controle toda la base recalcule la cadena. | Autenticación, roles y autorización; anclaje externo firmado; revisión de procedimiento; prueba independiente y manual con datasets aprobados. Mantener pendiente [issue #114](https://github.com/JavierGrecco/NetSentinel/issues/114). |
| UX y pruebas | Páginas por dominio, documentación y asistente de aceptación de doce pasos con regresiones reales en Chromium. | **Buena disciplina de ingeniería automatizada en crecimiento**. El recorrido automatizado no certifica usabilidad real ni accesibilidad con lector de pantalla. | Completar la aceptación manual de 12 pasos, capturar hallazgos de UX y corregirlos en bloque antes de declarar estable 0.10.0. |
| Gobierno de cambios | CI multiplataforma, análisis de seguridad y cadena de suministro ejecutados en los SHA revisados. | **Proceso técnico útil**, pero los workflows verdes no bloquean necesariamente una integración si la protección del repositorio está mal configurada. | Resolver el ruleset/protección de `main` y comprobar con una PR de prueba que los checks son obligatorios. Seguimiento: [issue #195](https://github.com/JavierGrecco/NetSentinel/issues/195). |
| Operación empresarial | No hay colector central autenticado, RBAC, aislamiento multi-sitio ni operación remota segura. | **Fuera del alcance actual** y no debe anunciarse como capacidad. | Diseñar autenticación, autorización, enrolamiento, aislamiento, rotación y auditoría antes de abrir interfaces a la LAN o añadir multiusuario. |

## 4. El diferencial que sí podemos construir

La propuesta no debería ser “un panel con más gráficos”. También sería insuficiente decir solo “local-first”: NetAlertX ya ofrece una propuesta local/self-hosted madura para descubrimiento, cambios, alertas y sincronización multi-sitio. Nuestro rumbo diferencial necesita cerrar el espacio entre el inventario, los incidentes de disponibilidad y las fuentes importadas autorizadas, sin afirmar más de lo que prueba la evidencia.

1. **Contexto conservado:** cada equipo y hallazgo lleva a su lectura, la hora correspondiente y la fuente que realmente lo produjo.
2. **Explicabilidad:** el usuario ve qué se sabe, qué se infiere, qué queda desconocido y cuál es el próximo paso seguro.
3. **Flujo de investigación accesible:** desde un cambio de inventario o incidente se llega al activo, a la actividad coincidente, al detalle de su fuente y a un informe portable.
4. **Privacidad verificable:** no hay que desplegar una nube ni un colector antes de poder hacer la primera evaluación; las fuentes adicionales se autorizan y muestran explícitamente.
5. **Interoperabilidad sin duplicar el ecosistema:** NetSentinel ayuda a encontrar y organizar evidencia; Zeek, Wireshark, Arkime o plataformas mayores siguen haciendo el trabajo especializado que les corresponde.

El valor de este diferencial depende de completar el flujo y demostrarlo con pruebas, no de nombrar estas propiedades en la página principal.

## 5. Plan de mejora priorizado

### P0 — Cerrar las puertas de estabilización antes de sumar alcance

- Consultar CI, Security Analysis y Supply Chain en el SHA exacto de `main`; registrar los resultados finales de las ejecuciones posteriores al merge.
- Ejecutar manualmente el laboratorio completo de 12 pasos con datos sintéticos aislados, registrar resultados y SHA, y revisar teclado, lector de pantalla y ventanas estrechas.
- Verificar administrativamente el ruleset de `main`, los checks obligatorios y la restricción de push directo.
- No declarar 0.10.0 estable mientras esos puntos estén abiertos. Un reporte automatizado verde no cuenta como aceptación manual.

### P1 — Correlación temporal y navegación a evidencia de origen

Es la mejora de producto con mayor valor potencial después de estabilizar la versión actual.

- Extender el contrato de hallazgos para enlazar referencias a actividad importada de Zeek, sin convertir automáticamente una coincidencia en amenaza.
- Correlacionar únicamente si la identidad del activo, el intervalo temporal y el alcance son explícitos y compatibles. Si la IP fue reasignada o hay más de un propietario posible, el resultado debe declararse ambiguo.
- Conservar hora de observación, hora de importación, ID del registro de fuente, fuente, dirección de conexión y contador cuando exista.
- Permitir abrir la fila de actividad original y la lectura del inventario desde cada relación.
- Incluir evidencia que contradiga o debilite una hipótesis, no solo los elementos que parecen respaldarla.
- Probar todo con fixtures sintéticos: coincidencia y no coincidencia, datos fuera de ventana, IP reasignada, horas inválidas, cero real, campos ausentes, duplicados, retención y límites de consulta.

La definición funcional está en [issue #197](https://github.com/JavierGrecco/NetSentinel/issues/197). La implementación debe esperar a las puertas P0, no mezclarse con el cierre de la versión 0.10.0.

### P2 — Informe portátil de investigación

Cuando P1 esté validada, permitir exportar un expediente compacto y reproducible con resumen, rango temporal, activos, hallazgos, referencias a evidencia de origen, fuentes y sus limitaciones. Antes de exportar, mostrar qué campos personales/de red se incluirán. El paquete debe usar un esquema versionado, manifestar los archivos incluidos y su SHA-256 y no incluir rutas locales completas ni secretos.

El digest permitirá detectar modificaciones frente a una copia de referencia; no presentarlo como firma digital, autenticación ni garantía legal. La firma/anclaje externo pertenece al plan de madurez forense y necesita un diseño de confianza separado.

### P3 — Elegir una sola integración real de infraestructura

No crear todavía un sistema general de plugins ni integrar seis protocolos a la vez. Identificar un entorno objetivo y decidir entre un origen concreto de sólo lectura, por ejemplo SNMP o NetFlow/IPFIX si el dispositivo de referencia lo soporta y el caso de uso lo justifica. Definir previamente credenciales mínimas, disponibilidad, timeout, límites, versión del contrato, procedencia y pruebas con respuestas simuladas/sanitizadas.

La fuente debe poder apagarse y sus credenciales quitarse sin borrar historiales. Si la infraestructura ya produce Zeek logs, primero conviene extraer más valor de la importación actual antes de instalar otro sensor.

### P4 — Madurez forense verificable

Antes de usar el módulo en investigaciones oficiales, hacen falta como mínimo identidad autenticada, autorización, anclaje independiente verificable, revisión del procedimiento y pruebas manuales/externas con datasets aprobados. El flujo actual no debe confundirse con adquisición forense del soporte original.

### P5 — UX que convierte los módulos en un producto

- Dar prioridad a una ruta principal para responder “¿qué cambió?”, “¿qué está caído?” y “¿qué evidencia lo sostiene?”.
- Mantener un contexto de activo/rango temporal visible al cambiar entre mapa, actividad, hallazgos e informes.
- Explicar estados vacíos, datos antiguos, resultados parciales y falta de fuentes con instrucciones concretas.
- Medir éxito por tiempo hasta un diagnóstico reproducible, tasa de falsos positivos, pasos completados sin ayuda y calidad de los informes; no por cantidad de pantallas.

## 6. Qué no conviene copiar ni construir ahora

- **No presentar actividad de sockets, conteos estimados o animaciones como paquetes/bytes reales.** Cada métrica debe registrar su método de adquisición.
- No asociar gateway-dispositivo, IP-equipo o geolocalización como relación confirmada si sólo existe una inferencia débil.
- No llamar “vulnerabilidad” a todo puerto abierto ni atribuir una causa raíz a un solo evento.
- No desarrollar captura de paquetes, DPI o un repositorio PCAP propio para igualar ntopng, Zeek o Arkime antes de demostrar la necesidad y el coste operacional.
- No incorporar acciones privilegiadas de bloqueo de red sin un modelo de autorización, control de alcance, confirmación y reversión.
- No copiar código literal de fuentes cuya licencia y procedencia no estén confirmadas.
- No añadir una base multi-sede o servidor remoto sin autenticación, autorización y aislamiento diseñados y probados.
- No confundir el mapa mundial de IP públicas con la ubicación física de un dispositivo o una persona.
- No presentar NetSentinel Forense como herramienta pericial certificada.
- No convertir el laboratorio guiado de aceptación en una prueba que dependa de instalaciones externas, tráfico real o instrucciones dispersas.

## 7. Criterios para medir si mejoramos de verdad

Antes de ampliar alcance y luego de cada hito, medir con un mismo conjunto de escenarios:

- Tiempo para llegar al primer inventario útil y entender un incidente de disponibilidad.
- Porcentaje de cada afirmación del informe con fuente, hora y registro de origen navegable.
- Porcentaje de relaciones con etiqueta explícita de observada/inferida/desconocida.
- Falsos positivos, ambigüedades de identidad y errores de interpretación de campos ausentes.
- Tasa de tareas que se completan sin ayuda y claridad de las instrucciones al volver de otra pantalla.
- Exportación/importación repetible, deduplicación y consistencia del rango temporal.
- Restauración de respaldo comprobada y ausencia de pérdida de datos en migraciones.
- Dependencias, permisos y datos que salen de la máquina por defecto.
- CI, seguridad y cadena de suministro sobre el mismo SHA; aceptación manual registrada por separado.

Los objetivos cuantitativos se deben fijar después de una línea base medida, no inventar ahora porcentajes que no tenemos.

## 8. Fuentes primarias consultadas

### Proyectos de referencia directa

- [ossianericson/netsentinel — repositorio y README](https://github.com/ossianericson/netsentinel)
- [ossianericson/netsentinel — referencia de funciones](https://ossianericson.github.io/netsentinel/feature-reference/)
- [blacsecurity/netsentinel — repositorio](https://github.com/blacsecurity/netsentinel)
- [NetAlertX — repositorio](https://github.com/netalertx/NetAlertX)
- [NetAlertX — descripción de funciones](https://docs.netalertx.com/FEATURES/)
- [Nmap — documentación oficial de descubrimiento de hosts](https://nmap.org/book/man-host-discovery.html)

### Observabilidad, tráfico y análisis de red

- [ntopng — Network Traffic Analysis](https://www.ntop.org/products/traffic-analysis/ntopng/)
- [Zeek — Network Security Monitor](https://zeek.org/)
- [Zeek — Logging Framework](https://docs.zeek.org/en/lts/frameworks/logging.html)
- [Arkime — Network Analysis and Packet Capture](https://arkime.com/)
- [Malcolm — Documentation overview](https://malcolm.fyi/docs/)
- [Security Onion — Introduction](https://docs.securityonion.net/en/3/dev/introduction/)
- [Wireshark — About and features](https://www.wireshark.org/about)

### Monitorización de infraestructura e inventario

- [LibreNMS — Feature list](https://docs.librenms.org/Support/Features/)
- [OpenNMS — Platform overview](https://www.opennms.com/platform/)
- [Uptime Kuma — repositorio y tipos de monitor](https://github.com/louislam/uptime-kuma)
- [Prometheus — documentación de arquitectura de métricas](https://prometheus.io/docs/introduction/overview/)
- [NetBox — Documentation](https://netboxlabs.com/docs/netbox/)

### Fuentes del propio proyecto para continuar el trabajo

- [Dirección de producto y barra de calidad](PRODUCT_DIRECTION.md)
- [Matriz de adopción de las referencias](REFERENCE_FEATURE_ADOPTION_MATRIX.md)
- [Explorador de red y observabilidad](NETWORK_OBSERVABILITY_CONSOLE.md)
- [Importación de conn.log de Zeek](ZEEK_CONNLOG_IMPORT.md)
- [Estado actual](PROJECT_STATUS.md)
- [Roadmap maestro](ROADMAP.md)
- [Matriz de preparación pericial](FORENSIC_READINESS_MATRIX.md)
- [Issue de correlación de evidencia](https://github.com/JavierGrecco/NetSentinel/issues/197)

---

**Decisión recomendada:** estabilizar y aceptar la versión local actual; después unir los datos existentes mediante una correlación temporal transparente y un informe portable. Sólo entonces elegir una integración de infraestructura basada en un caso real. Esto maximiza el diferencial del producto sin sacrificar privacidad, legibilidad, mantenibilidad ni precisión.
