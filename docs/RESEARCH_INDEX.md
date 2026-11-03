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
