# Roadmap maestro de NetSentinel

> **Fuente única de verdad para prioridades, estado y criterios de finalización.** El plan técnico de [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) complementa este documento; no mantiene un backlog paralelo. Para retomar el trabajo sin leer todo el plan, consultá primero [PROJECT_STATUS.md](PROJECT_STATUS.md). La evidencia de pruebas manuales se registra en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## Estado del proyecto

**Estado:** estabilización de la versión local 0.10.0. La funcionalidad principal existe y las comprobaciones automatizadas han estado verdes en la revisión anterior, pero **la versión todavía no está lista para declararse estable** porque faltan pruebas manuales documentadas en sistemas/navegadores reales y confirmar controles de repositorio.

- **Versión durante el desarrollo:** 0.10.0.dev0.
- **Próxima versión objetivo:** 0.10.0. Es una meta de trabajo, no una fecha prometida.
- **Última integración de código:** [PR #140](https://github.com/JavierGrecco/NetSentinel/pull/140), mejora del historial de latencia para distinguir períodos vacíos de fallos sin medición; commit [8d08ee4](https://github.com/JavierGrecco/NetSentinel/commit/8d08ee40e51157fa38f1009ced502fa5c9fef6c4). La comparación de capturas entró en las PR #137 y #139; el grafo LAN en la PR #135.
- **Último commit funcional revisado al actualizar esta nota:** [8d08ee4](https://github.com/JavierGrecco/NetSentinel/commit/8d08ee40e51157fa38f1009ced502fa5c9fef6c4), continuidad de las series de monitorización y estados de latencia más claros.
- **CI de la comparación inicial (PR #137):** [ejecución #38858149460](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149460) — 18/18 trabajos correctos antes de fusionar.
- **Corrección de alcance (PR #139):** CI [#38858557234](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557234) — 18/18 trabajos correctos; seguridad [#38858557227](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557227) — 2/2 correctos; cadena de suministro [#38858557244](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557244) — build y SBOM/manifiesto correctos, firma de procedencia omitida por no ser una publicación de release.
- **Seguridad y cadena de suministro de la PR #137:** [ejecución #38858149503](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149503) y [#38858149464](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149464) finalizaron correctamente antes de fusionar.
- **CI de historial de monitorización (PR #140):** [ejecución #38859569998](https://github.com/JavierGrecco/NetSentinel/actions/runs/38859569998) — 18/18 trabajos correctos antes de fusionar; **seguridad:** [#38859570132](https://github.com/JavierGrecco/NetSentinel/actions/runs/38859570132) — 2/2 correctos; **cadena de suministro:** [#38859570019](https://github.com/JavierGrecco/NetSentinel/actions/runs/38859570019) — build, SBOM y manifiesto correctos, firma omitida por no ser una release. Los checks citados son del SHA revisado de la PR; los posteriores a la fusión sobre [8d08ee4](https://github.com/JavierGrecco/NetSentinel/commit/8d08ee40e51157fa38f1009ced502fa5c9fef6c4) no están confirmados.
- **Revisión visual y pruebas manuales:** pendientes de registrar en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md), incluidos `UI-09` (comparación de capturas) y `UI-10` (huecos/latencia en Monitorización).
- **Protección efectiva de main:** pendiente de verificación en GitHub; seguimiento en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
- **Pruebas manuales de instalación y uso:** seguimiento operativo en [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75); registrar resultados y evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
- **Pull requests de Dependabot:** #37–#43 requieren revisión individual; no fusionarlos en lote solo porque una comprobación antigua aparezca verde.

Los enlaces de ejecución son una fotografía de la revisión, no un indicador dinámico. Antes de una release debe revisarse la ejecución más reciente de cada workflow y su commit.

## Análisis comparado: visualizaciones, datos y seguridad

Las revisiones estáticas están documentadas en [REFERENCE_PROJECT_REVIEW.md](REFERENCE_PROJECT_REVIEW.md) (ossianericson) y [REFERENCE_PROJECT_REVIEW_BLACSECURITY.md](REFERENCE_PROJECT_REVIEW_BLACSECURITY.md) (blacsecurity). La segunda aporta ideas de actividad en vivo y selección de nodos, además de riesgos que no debemos copiar: API sin protección visible, servicio en todas las interfaces, CORS abierto, secreto fijo, acciones que cambian el firewall y métricas de tráfico estimadas presentadas como actividad.

La dirección del producto queda así:

1. **Grafo LAN de solo lectura:** primera versión integrada mediante la [PR #135](https://github.com/JavierGrecco/NetSentinel/pull/135). La vista parte de las observaciones exactas asociadas a un `scan_id`, muestra la fuente de cada relación y no afirma una conexión física directa por compartir subred. Si no se puede recuperar la evidencia de la lectura, no dibuja vínculos. CI multiplataforma, Security, Supply Chain y el test responsive de Chromium pasaron para el commit revisado de la PR. Queda pendiente la revisión visual manual en instalaciones reales.
2. **Historial de Monitorización:** la [PR #140](https://github.com/JavierGrecco/NetSentinel/pull/140) integró una línea temporal continua y separa períodos sin registros de comprobaciones fallidas sin latencia. La API y la exportación CSV comparten los mismos intervalos, sin inventar mediciones; se mantiene como siguiente trabajo revisar resúmenes y tendencias con datos reales y comprobar el flujo manualmente.
3. **Cambios entre lecturas:** versión inicial integrada mediante la [PR #137](https://github.com/JavierGrecco/NetSentinel/pull/137) y corrección de alcance mediante la [PR #139](https://github.com/JavierGrecco/NetSentinel/pull/139). Compara observaciones históricas exactas solo dentro de las subredes IPv4 privadas compartidas, para evitar diferencias falsas cuando el alcance cambia entre capturas. Advierte cuando hubo errores o alcance limitado y no interpreta ausencia como desconexión. CI, seguridad, empaquetado y Chromium pasaron para los SHA revisados antes de fusionar; queda pendiente revisar visualmente el flujo en una instalación real.
4. **Mapa mundial de IP públicas:** estudiar después y solo si existe una fuente real/autorizada de IP públicas con utilidad para investigar. La geolocalización es aproximada y no demuestra la ubicación de una persona ni de un dispositivo.
5. **Fuentes adicionales:** elegir una integración concreta y de solo lectura antes de crear conectores genéricos. No incorporar captura privilegiada, bloqueo de equipos ni acceso remoto como atajo visual.

El grafo y la comparación ya están integrados en `main`, pero no sustituyen la Fase 0 ni permiten declarar estable la release. Las pruebas automáticas no reemplazan la validación visual y manual documentada en instalaciones reales. Las nuevas capacidades no se consideran terminadas por existir código solamente.

## Cómo se mantiene el seguimiento

1. Cada tarea lleva un ID estable (por ejemplo, REL-01 o FIND-02) para poder referenciarla desde PR, issue y evidencia de pruebas.
2. Una casilla marcada como completa significa que **todos** los criterios de aceptación de esa tarea están cumplidos. Que el código exista, compile o pase CI no basta si la tarea requiere prueba manual, política de privacidad, documentación o verificación operativa.
3. Las tareas que dependen de sistemas reales se cierran solo después de añadir fecha, entorno, versión/commit y resultado en VALIDATION_MATRIX.md. Adjuntá el enlace de CI, PR o issue cuando corresponda.
4. Si una prueba falla, no marques la tarea como completa: abrí o vinculá un issue con pasos para reproducir, resultado observado y esperado.
5. Actualizá este documento en el mismo PR que completa una tarea. No mantengas porcentajes estimados en paralelo: el estado por fase y las evidencias son más fiables que contar casillas de diferente tamaño.
6. Las fases son puertas secuenciales: se pueden preparar tareas futuras, pero no habilitar capacidades remotas ni anunciar una release antes de superar sus puertas de seguridad.

## Fase 0 — Estabilización y release local 0.10.0

**Estado: en curso. Bloquea la publicación estable.**

El núcleo actual incluye inventario local, observaciones y cambios, descubrimiento LAN limitado, monitores Ping/TCP/HTTP(S), incidentes, consultas DNS, diagnóstico TLS puntual, hallazgos de inventario/monitorización, exportaciones, copia SQLite y extensión Chromium opt-in con importación manual. También existen pruebas automatizadas Python/Node, CI para Python 3.10–3.14 en Windows/macOS/Linux, análisis estático, auditoría de dependencias y artefactos de cadena de suministro.

Quedan por cerrar:

- [ ] **REL-01 — Instalación limpia multiplataforma.** Completar instalación y primer inicio desde descarga limpia, actualización/reinicio y diagnóstico de errores en Windows, macOS y Linux. Registrar sistema operativo, Python, versión/commit y evidencia.
- [ ] **REL-02 — Flujos de inventario y red.** Comprobar descubrimiento explícito, subredes duplicadas/interfaces virtuales, inventario vacío, cambios observados, diagnósticos y límites anunciados. Confirmar que un resultado sin respuesta no se presenta como prueba de ausencia.
- [ ] **REL-03 — Monitorización e incidentes.** Verificar los tipos Ping/TCP/HTTP(S), apertura/actualización/cierre de incidentes, timeouts, retención y webhook opcional con un destino de prueba controlado.
- [ ] **REL-04 — DNS y TLS.** Validar resolución correcta, NXDOMAIN/entrada inválida, timeout, endpoint TLS válido, certificado vencido/no confiable, hostname incompatible y puerto que no habla TLS. El resultado debe distinguir error de red, error de certificado y límite de diagnóstico.
- [ ] **REL-05 — Persistencia y recuperación.** Crear datos representativos, exportarlos, restaurar una copia SQLite en una ubicación segura y comprobar que los registros se recuperan sin pérdida. Verificar retención y borrado selectivo, incluidos el alcance y la confirmación.
- [ ] **REL-06 — Extensión e importación.** Probar manualmente Chrome y Edge: instalación, estado apagado por defecto, activación explícita, pausa, exclusiones, navegación SPA, retención, CSV, previsualización, deduplicación y ausencia de escrituras parciales cuando el lote es inválido. Registrar casos de falsos positivos/negativos del saneamiento.
- [ ] **REL-07 — Privacidad de actividad y correo.** Usar datos sintéticos o exportaciones de auditoría expresamente autorizadas. Confirmar límites de metadatos, rechazo de columnas de cuerpo/adjuntos, retención, exportación y borrado. No usar mensajes o datos personales reales en fixtures públicos.
- [ ] **REL-08 — Controles del repositorio.** Resolver el seguimiento de [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73): verificar en Settings que main exige PR y los checks necesarios, y que no permite force-push ni borrado. La documentación por sí sola no activa estas reglas.
- [ ] **REL-09 — Dependencias y workflows.** Revisar separadamente los PR #37–#43 de Dependabot, verificar que sus checks correspondan a los SHAs actuales y evaluar cambios de compatibilidad/acciones antes de fusionar o cerrar.
- [ ] **REL-10 — Preparación del paquete.** Instalar el wheel generado en un entorno limpio y verificar metadatos, recursos estáticos, CLI, checksum y SBOM. Confirmar la procedencia de los artefactos firmados/atestados cuando exista una etiqueta.
- [ ] **REL-11 — Documentación de release.** Registrar resultados reales, limitaciones conocidas, pasos de actualización/restauración y procedimiento de reporte de vulnerabilidades. No llamar “probado manualmente” a un test automático.

### Puerta de salida de Fase 0

La 0.10.0 solo se declara estable cuando REL-01 a REL-11 estén cerradas o tengan una excepción documentada, aprobada y de riesgo bajo; la ejecución vigente de CI, Security y Supply Chain esté verde sobre el commit candidato; no haya vulnerabilidades críticas/altas sin tratar en el alcance publicado; los artefactos se instalen desde cero; y no haya fallos bloqueantes conocidos en los recorridos principales. Toda excepción debe indicar responsable, motivo, impacto y plan de resolución.

## Fase 1 — Hallazgos explicables y evidencia correlacionada

**Objetivo:** evolucionar desde una lista de observaciones hacia un flujo de triaje útil, sin exagerar lo que una señal demuestra.

**Prerequisito transversal:** antes de sumar correlaciones y fuentes, separar las responsabilidades internas por dominio sin retrasar las pruebas de estabilización de la Fase 0. La propuesta y sus límites están en [ADR-001: monolito modular](ADR-001-MODULAR-MONOLITH.md). No implica adoptar microservicios ni cambiar el modo de instalación local.

- [ ] **ARCH-01 — Línea base de contratos.** Mapear dependencias/rutas existentes y asegurar pruebas de contrato para API, seguridad del navegador, exportaciones, CLI y ciclo de vida antes de mover código.
- [ ] **ARCH-02 — Separar API de casos de uso.** Extraer routers por dominio de `main.py`; mantener respuestas, códigos, encabezados de seguridad, protección de origen y rutas compatibles.
- [ ] **ARCH-03 — Persistencia con migraciones explícitas.** Versionar el esquema SQLite y probar actualización, backup, restauración y operaciones atómicas antes de redistribuir consultas por dominio.
- [ ] **ARCH-04 — Servicios y repositorios por dominio.** Hacer que cada módulo publique una interfaz tipada pequeña y que ningún dominio escriba directamente en las tablas internas de otro.
- [ ] **ARCH-05 — Límites comprobados por pruebas.** Añadir verificaciones de dependencias para evitar SQL en routers, ciclos de importación y dependencias de las reglas de dominio respecto de FastAPI.
- [ ] **ARCH-06 — Adaptadores solo cuando aporten valor.** Incorporar interfaces para fuentes variables una a una, con fixtures, timeouts, procedencia, desconexión y errores documentados. No crear un sistema genérico de plugins sin necesidad demostrada.

**Refuerzo integrado:** la [PR #129](https://github.com/JavierGrecco/NetSentinel/pull/129) declara y prueba las dependencias permitidas de `activity_tracking.py`. La revisión confirmó que esa pieza ya funciona como fachada de servicios, por lo que no se la vuelve a dividir sin una necesidad demostrada. En esta etapa, la prioridad deja de ser mover archivos y vuelve a la puerta de salida de la Fase 0: pruebas manuales reproducibles de instalación, inventario, monitorización, DNS/TLS, persistencia, extensión y privacidad, registradas en la matriz de validación. Las tareas ARCH-01 a ARCH-06 permanecen abiertas hasta cumplir sus criterios completos.

**Entrega parcial integrada en `main` (15 de octubre de 2026):** las PR #111, #115, #116, #118, #120, #121, #123, #125 y #127 separaron persistencia, las rutas HTTP de Monitorización/Inventario/DNS/TLS y las políticas transversales de seguridad y errores. La Fase 1 de arquitectura sigue abierta hasta cumplir los criterios completos de separación de casos de uso, persistencia, contratos y adaptadores; ninguna extracción aislada da por completa esa fase.

- [ ] **FIND-01 — Contrato de evidencia y retención.** Definir, antes de persistir nuevas fuentes, esquema, campos mínimos, migración SQLite, plazo de retención, borrado/exportación y configuración de desactivación.
- [ ] **FIND-02 — Resultados DNS/TLS opcionales.** Incorporar resultados puntuales solo con política explícita de persistencia y retención; registrar fuente, hora, activo consultado, resultado bruto mínimo necesario y limitaciones. No almacenar secretos ni contenido HTTP.
- [ ] **FIND-03 — Ciclo de vida de hallazgos.** Especificar y probar estados nuevo/revisado/aceptado como riesgo/resuelto, agrupación determinista, deduplicación, reevaluación y cierre sin eliminar el historial de evidencia.
- [ ] **FIND-04 — Correlación conservadora.** Crear reglas deterministas con explicación de cada relación. Mantener severidad y confianza separadas; identificar qué dato respalda una inferencia y qué información falta. No inferir causa raíz o compromiso basándose solo en una MAC desconocida, ping fallido, nombre DNS o certificado.
- [ ] **FIND-05 — UX de investigación.** Facilitar filtros por activo, periodo, fuente y estado; permitir saltar desde el hallazgo al evento original; representar errores, falta de datos y falsos positivos de forma accesible.
- [ ] **FIND-06 — Pruebas de regresión.** Cubrir duplicados, eventos fuera de orden, transición a resuelto, evidencia incompleta, migraciones, exportación y borrado; añadir pruebas de aceptación para no filtrar texto externo como HTML.

### Puerta de salida de Fase 1

Cada hallazgo debe ser reproducible, tener procedencia/fecha/evidencia y explicar su grado de certeza; la retención y el borrado deben funcionar; las migraciones deben conservar datos; y la documentación debe describir exactamente las fuentes que sí entran y las que no.

## Fase 2 — Fuentes reales de infraestructura, de solo lectura

**Objetivo:** sumar contexto fiable sin inventar adaptadores genéricos ni abrir accesos innecesarios. La alternativa de observación sin agentes por dispositivo y sus límites están descritos en [NETWORK_VISIBILITY.md](NETWORK_VISIBILITY.md). Las opciones DNS/flujo que aparecen en la interfaz de Actividad todavía no equivalen a un adaptador implementado.

- [ ] **SRC-01 — Selección de la primera integración.** Elegir un modelo/proveedor concreto de router, AP, DHCP o resolvedor a partir de documentación/API disponible y necesidad real. Documentar campos que realmente expone, requisitos de acceso y limitaciones.
- [ ] **SRC-02 — Contrato del adaptador.** Definir interfaz común para origen, marca de tiempo, alcance, estado de frescura, errores parciales, paginación/límites y saneamiento de datos.
- [ ] **SRC-03 — Primer adaptador de solo lectura.** Implementar una integración real a la vez. Mantener credenciales fuera del repositorio y de logs; configurar timeouts, llamadas limitadas y opción clara de desconexión.
- [ ] **SRC-04 — Fixtures sin hardware real.** Guardar fixtures sanitizados y pruebas deterministas para respuestas normales, vacías, incompletas, malformadas, autenticación fallida, timeout y cambio de versión de API.
- [ ] **SRC-05 — Confianza y atribución.** Mostrar la fuente y la hora de cada dato; distinguir información observada de inferida y no asociar una IP/MAC a una persona sin evidencia.
- [ ] **SRC-06 — Expansión condicionada.** Evaluar SNMP u otras familias después de demostrar que la primera integración es estable y útil; documentar compatibilidad, versiones y credenciales requeridas.

### Puerta de salida de Fase 2

Una fuente se considera soportada solo si tiene documentación, fixtures, pruebas de error, timeouts, límites, procedencia visible, gestión de secretos y validación en un equipo compatible sin requerir privilegios innecesarios.

## Fase 3 — Informes, métricas y experiencia operativa

- [ ] **OPS-01 — Informe reproducible.** Exportar un informe por periodo/activo con eventos, hallazgos, evidencia, fuentes, tiempos y limitaciones; permitir minimizar datos sensibles y verificar neutralización de fórmulas en formatos tabulares.
- [ ] **OPS-02 — Métricas Prometheus.** Añadir métricas de cardinalidad controlada, sin etiquetas de alta cardinalidad con IP arbitrarias, URL, nombres de usuario o datos sensibles. Mantener exposición local segura y documentar cómo desactivarlas.
- [ ] **OPS-03 — Perfiles de red.** Diseñar aislamiento de inventario e historial por sitio/perfil antes de implementar múltiples ubicaciones. Evitar mezclar direcciones repetidas de redes diferentes.
- [ ] **OPS-04 — Usabilidad y accesibilidad.** Mantener un marco visual común entre Inventario, Hallazgos, Monitorización, Herramientas y Actividad (ancho, tipografía, controles, paneles y espacios); validar teclado, contraste, nombres accesibles, adaptación móvil, errores accionables y funcionamiento sin depender de notificaciones temporales. Registrar el recorrido visual real en la matriz de validación. La nueva distribución del Inventario ya aprovecha una segunda fila y se apila en ventanas estrechas; la tarea sigue abierta hasta comprobarla visualmente en un navegador real. El verificador `scripts/check_responsive_ui.py` cubre cinco páginas y una matriz de quince tamaños con Chromium; sus resultados automáticos no reemplazan la revisión visual humana ni los registros de Windows/macOS/Linux.
- [ ] **OPS-05 — Métricas del producto.** Medir tiempo hasta inventario útil, recorridos completos sin ayuda, falsos positivos reportados, éxito de restauración y tiempo de reproducción de errores. No recolectar telemetría de uso externa por defecto.

## Fase 4 — Recolección remota y multi-sede (bloqueada por diseño de seguridad)

**No exponer la API actual a la LAN como atajo.** Esta fase no empieza hasta aprobar el diseño de amenazas, el modelo de autorización y las pruebas del límite de confianza.

- [ ] **REM-01 — Modelo de amenazas y arquitectura.** Definir actores, activos, límites de red, enrolamiento, pérdida de credenciales, suplantación, repetición, aislamiento y escenarios de actualización comprometida.
- [ ] **REM-02 — Identidad y transporte.** Implementar TLS, autenticación fuerte, autorización por dispositivo, enrolamiento explícito, expiración, rotación y revocación de credenciales.
- [ ] **REM-03 — Protección de la ingestión.** Añadir protección anti-replay, idempotencia, cuotas y rate limiting, límites de tamaño, validación estricta, registro de auditoría y comportamiento fail-closed.
- [ ] **REM-04 — Aislamiento multi-sede.** Definir roles/permisos y probar que usuarios, agentes y administradores de un sitio no puedan consultar/modificar datos de otro.
- [ ] **REM-05 — Operación segura.** Versionar migraciones, respaldos/restauración, actualización, recuperación, rotación de secretos y respuesta a incidentes.
- [ ] **REM-06 — Revisión antes de habilitar.** Realizar pruebas de seguridad específicas de API remota y solo entonces documentar una configuración remota habilitada expresamente.

### Puerta de salida de Fase 4

No se habilita despliegue remoto/centralizado hasta que las pruebas negativas de autenticación, autorización, replay, rate-limit y aislamiento estén verdes, exista auditoría y revocación probadas, y la configuración segura por defecto se haya verificado.

## Fase 5 — Ecosistema e integración SOC

- [ ] **INT-01 — Webhooks y formatos de intercambio.** Definir contrato versionado, reintentos, idempotencia, autenticación y minimización de datos para integraciones externas.
- [ ] **INT-02 — Integración SIEM.** Elegir un formato/proveedor a partir de casos de uso reales y validar manejo de errores, orden, duplicados y secretos.
- [ ] **INT-03 — Adaptador de auditoría de correo.** Solo después de seleccionar proveedor, verificar capacidades de la cuenta, consentimiento y permisos mínimos; empezar por metadatos de auditoría y no por lectura de bandejas.
- [ ] **INT-04 — Otros navegadores/agentes opt-in.** Considerar Firefox o agentes por sistema operativo únicamente después de definir el contrato de eventos, los controles de autorización y la desinstalación/borrado.
- [ ] **INT-05 — Mapeo de controles.** Publicar una matriz de evidencia y brechas frente a marcos pertinentes (por ejemplo, NIST CSF 2.0/CISA CPG) sin declarar certificación o cumplimiento automático.

## No objetivos y límites de producto

Mientras no exista evidencia y diseño explícitos, NetSentinel no debe presentarse como EDR, IDS/NDR, SIEM completo, escáner de vulnerabilidades integral ni gestor de identidad de dispositivos. El núcleo local actual no captura paquetes de red ni puede ver por sí solo toda la actividad de otros equipos. No implementar keylogging, recuperación/interceptación de contraseñas, lectura de cuerpos de mensajes, captura de formularios ni descifrado/proxy TLS general.

## Definición de terminado para cualquier tarea

Una tarea se marca completa cuando aplican y se cumplen todos estos puntos:

1. Código integrado por PR y revisión del cambio.
2. Tests deterministas de casos normales, inválidos, límites, errores y timeouts; sin depender de Internet, hardware o privilegios en tests unitarios.
3. CI vigente verde y wheel/recursos de distribución verificados si el cambio los afecta.
4. Prueba manual documentada para características dependientes de SO, navegador, router o experiencia de usuario.
5. Tratamiento de privacidad, retención, eliminación y autorización documentado junto a la función.
6. Migración compatible y restauración validada si cambia el almacenamiento.
7. Guía, changelog y limitaciones actualizados.
8. Evidencia enlazada desde esta tarea: PR/commit, ejecución CI, fila de VALIDATION_MATRIX.md y/o issue de seguimiento.

No se considera terminado por existir código, por una captura de pantalla aislada ni por la cantidad de líneas implementadas.
