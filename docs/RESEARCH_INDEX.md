# Investigación y proyectos de referencia

Este índice reúne la investigación que ayudó a tomar decisiones de producto y arquitectura. Las referencias son fuentes de estudio, no componentes de los que NetSentinel dependa automáticamente ni evidencia de autoría compartida.

## Cómo interpretar esta investigación

- **Referencia** identifica un proyecto o una herramienta externa estudiada.
- **Patrón observado** describe una idea general, no una afirmación de que copiamos su implementación.
- **Decisión propia** explica qué se construyó, adaptó, pospuso o descartó en NetSentinel.
- **Evidencia** apunta al código, las pruebas o la documentación de este repositorio.
- **Procedencia** identifica código, datos, bibliotecas o recursos externos que sí se distribuyen.

Las revisiones de repositorios externos fueron principalmente estáticas. No equivalen a auditorías de seguridad, pruebas de ejecución completas ni validaciones de sus autores.

## Referencias principales

| Fuente | Qué estudiamos | Decisión y tratamiento |
|---|---|---|
| [ossianericson/netsentinel](https://github.com/ossianericson/netsentinel) | Modelo de topología, navegación del grafo, contexto de observaciones y comunicación de fallos | Adoptamos patrones conceptuales donde encajan con nuestra arquitectura web; no trasladamos su interfaz de escritorio ni sus mecanismos internos. |
| [blacsecurity/netsentinel](https://github.com/blacsecurity/netsentinel) | Lectura rápida del inventario, selección de nodos y presentación de hallazgos | Tomamos ideas generales de interacción. No reutilizamos código cuya licencia y procedencia no estaban aclaradas en la revisión. |
| NetAlertX, Nmap, ntopng, Zeek, Arkime, Malcolm, Security Onion, Uptime Kuma, Prometheus, LibreNMS, OpenNMS, NetBox y Wireshark | Alcances de inventario, observabilidad, análisis de tráfico, monitorización e interoperabilidad | Se usan como referencias de categoría y para identificar límites; NetSentinel no afirma reemplazarlos ni igualar sus capacidades. |

## Referencias por área

Las fuentes se agrupan por el problema que ayudaron a estudiar. No son dependencias de ejecución, socios, certificaciones ni una lista de productos que NetSentinel prometa reemplazar.

### Inventario, descubrimiento y topología

| Fuente | Aspecto estudiado |
|---|---|
| [ossianericson/netsentinel](https://github.com/ossianericson/netsentinel) | Topología, observaciones, navegación del grafo y geolocalización |
| [blacsecurity/netsentinel](https://github.com/blacsecurity/netsentinel) | Lectura del inventario, interacción con nodos y presentación de hallazgos |
| [NetAlertX](https://github.com/netalertx/NetAlertX) | Descubrimiento y seguimiento de dispositivos de red |
| [Nmap](https://nmap.org/book/man-host-discovery.html) | Descubrimiento de hosts y límites de las sondas |
| [Fing](https://www.fing.com/scan/) | Incorporación sencilla y reconocimiento de dispositivos |
| [Angry IP Scanner](https://angryip.org/documentation/) | Separación entre interfaz, motor de escaneo y recolectores |
| [NetBox](https://netboxlabs.com/docs/netbox/) | Modelado explícito de inventario e infraestructura |

### Monitorización, observabilidad y diagnóstico

| Fuente | Aspecto estudiado |
|---|---|
| [ntopng](https://www.ntop.org/products/traffic-analysis/ntopng/) | Visibilidad de tráfico y análisis de red |
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | Comprobación de disponibilidad y presentación de estados |
| [Prometheus](https://prometheus.io/docs/introduction/overview/) | Métricas, etiquetas y exportación |
| [LibreNMS](https://docs.librenms.org/Support/Features/) | Inventario y monitorización de infraestructura |
| [OpenNMS](https://www.opennms.com/platform/) | Gestión y monitorización de redes |
| [Zabbix](https://www.zabbix.com/documentation/7.2/en/manual/introduction/overview) | Separación de servidor, proxy, agentes y presentación |
| [Auvik](https://www.auvik.com/system-security/) | Límites de colectores y despliegues distribuidos |

### Telemetría, análisis de tráfico y respuesta

| Fuente | Aspecto estudiado |
|---|---|
| [Zeek](https://zeek.org/) | Eventos estructurados, metadatos y procedencia |
| [Arkime](https://arkime.com/) | Exploración e investigación de sesiones de red |
| [Malcolm](https://malcolm.fyi/docs/) | Integración de herramientas de análisis de tráfico |
| [Security Onion](https://docs.securityonion.net/en/3/dev/introduction/) | Plataforma integrada de monitoreo y análisis |
| [Wireshark](https://www.wireshark.org/about) | Análisis de protocolos y evidencia de paquetes |
| [Suricata](https://docs.suricata.io/en/suricata-8.0.2/output/eve/eve-json-output.html) | Eventos estructurados y contratos de salida |
| [Wazuh](https://documentation.wazuh.com/current/getting-started/architecture.html) | Separación de agentes, análisis, almacenamiento y panel |

### Arquitectura y modularidad

| Fuente | Aspecto estudiado |
|---|---|
| [Spring Modulith](https://docs.spring.io/spring-modulith/reference/verification.html) | Verificación de ciclos y APIs públicas entre módulos |
| [Apache Fineract](https://github.com/apache/fineract/blob/develop/build.gradle) | Visibilidad de dependencias y métricas de arquitectura |
| [Microsoft — Architecture styles](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/) | Costos y trade-offs de los estilos arquitectónicos |
| [Martin Fowler — Microservice trade-offs](https://martinfowler.com/articles/microservice-trade-offs.html) | Costo operativo de separar procesos y servicios |

### Qué se tomó de la investigación

- Se priorizó una instalación local simple con límites internos explícitos, en lugar de introducir microservicios, agentes permanentes o infraestructura central sin necesidad demostrada.
- Se adoptó la distinción entre observación, evidencia e interpretación; los datos importados no se presentan como captura ejecutada por NetSentinel.
- Se tomaron patrones generales de interacción e inventario sin afirmar que se trasladó código de los repositorios comparados.
- Se descartaron atajos que ampliarían privilegios o superficie de ataque sin una necesidad de producto clara.

## Documentos de investigación existentes

- [Revisión de ossianericson/netsentinel](REFERENCE_PROJECT_REVIEW.md).
- [Revisión de blacsecurity/netsentinel](REFERENCE_PROJECT_REVIEW_BLACSECURITY.md).
- [Matriz de adopción y decisiones](REFERENCE_FEATURE_ADOPTION_MATRIX.md).
- [Análisis competitivo](COMPETITIVE_ANALYSIS_2026-10-23.md).
- [Plan histórico de reingeniería de referencias](REFERENCE_REENGINEERING_PLAN.md).

Estos documentos conservan el detalle técnico y las fuentes originales. No hace falta repetir sus comparaciones en el README principal.

## Qué no debe confundirse

1. Una idea de interfaz inspirada por una referencia no significa que se haya copiado su código.
2. Una función de una herramienta externa no forma parte de NetSentinel hasta que exista implementación propia y evidencia.
3. Una inspección estática no prueba que el proyecto externo funcione ni que sea seguro.
4. Un recurso de terceros distribuido con NetSentinel debe conservar sus avisos y licencia.
5. Las referencias no deben usarse como reclamo comercial ni para insinuar asociación, aval o compatibilidad no comprobada.

## Procedencia y avisos

Los componentes y recursos que sí se distribuyen se documentan en [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y en sus archivos de licencia correspondientes. Esa documentación es independiente de la investigación comparativa y debe conservarse.

## Regla editorial

La documentación pública principal debe explicar primero qué construye NetSentinel. La investigación se mantiene disponible para quien quiera conocer el proceso de evaluación y las decisiones que surgieron de él, pero no debe dominar la identidad del producto.
