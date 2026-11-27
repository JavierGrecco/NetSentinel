# Roadmap maestro de NetSentinel

> **Plan temporal de evolución:** contiene únicamente tareas pendientes, prioridades y puertas de salida. El estado vigente y el traspaso se mantienen en [PROJECT_STATUS.md](PROJECT_STATUS.md); la evidencia de verificación se conserva en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md). El enfoque técnico permanente está en [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## Estado vigente — 27 de noviembre de 2026

**Rama canónica:** `main`. Último commit integrado verificado al iniciar este corte: `f06feb067dc36264ab9362b4a9a56b213a03fda5`. La última entrega funcional de dominio sigue siendo `a6088f5ed2239b530d07b484eb60bf8024e1a91f`.

**Última integración funcional:** PR #200, correlación temporal Zeek en Hallazgos, commit [`a6088f5ed2239b530d07b484eb60bf8024e1a91f`](https://github.com/JavierGrecco/NetSentinel/commit/a6088f5ed2239b530d07b484eb60bf8024e1a91f). Incluye el núcleo semántico CSV/Zeek (#212), la procedencia `blocked` (#222), la correlación trazable y la corrección de presentación de estados de Actividad. La versión 0.10.0 sigue en desarrollo; no es estable.

**Seguimiento temporal:** [issue #219 — ejecución del plan integral](https://github.com/JavierGrecco/NetSentinel/issues/219). Las etapas completadas se retiran del checklist; el estado durable y las evidencias se conservan aquí y en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

### Prioridad inmediata — M0

**Estado: abierto.** La versión 0.10.0 continúa en desarrollo; no se declara estable.

Quedan dos puertas de salida:
- **Gobernanza de `main`:** el ruleset #25281660 sigue sin alcance efectivo para la rama principal, sin checks requeridos y sin aprobaciones. Una persona administradora debe aplicar `~DEFAULT_BRANCH` o `refs/heads/main`, configurar los 26 contextos recomendados y verificar que GitHub bloquee una integración con checks ausentes o fallidos.
- **Aceptación manual integral 0.10.0:** completar los recorridos de instalación, primer inicio, uso, recuperación, privacidad, extensión Chrome/Edge y accesibilidad descritos en la Fase 0. La cobertura automática de wheel, Chromium y responsive ya está integrada; sus evidencias no se duplican en este plan y permanecen en `PROJECT_STATUS.md` y `VALIDATION_MATRIX.md`.

La lista de trabajo activa de M0 está desglosada en las tareas REL-01 a REL-11 de la Fase 0. No hay tareas completadas dentro de este checklist.

### Dirección posterior a la estabilización

7. **M1 — NetSentinel Red:** reforzar identidad estable de activos, procedencia y frescura; separar relaciones de topología observadas/importadas/inferidas; cerrar el ciclo monitorización → hallazgo → investigación → informe; integrar DNS/TLS persistidos solo con contratos, retención y migraciones adecuados.
8. **M2 — Conocimiento de infraestructura:** primer laboratorio SNMPv3 de solo lectura con PySNMP + SNMPSim; después interfaces, estados/contadores y, si hay soporte real, LLDP/CDP/BRIDGE-MIB/VLAN. No habilitar SNMP SET ni almacenar secretos en el inventario.
9. **M3 — Forense confiable:** antes de analizar evidencia real, completar autenticación/roles, recepción y custodios, separación original/adquisición/copia de análisis, anclaje externo de auditoría, backup/restauración, pruebas sintéticas y revisión independiente.
10. **M4 — Análisis estático:** ClamAV como escáner externo, YARA-X como motor preferido de reglas nuevas, Androguard en versión publicada reproducible y MobSF como servicio externo opcional. Ejecutar parsers en workers aislados; analizar copias verificadas, no originales. CAPE y análisis dinámico quedan en laboratorio posterior.
11. **M5 — Inteligencia de amenazas:** CIRCL hashlookup primero; evaluar MalwareBazaar, ThreatFox y URLhaus. VirusTotal solo como proveedor opcional, preferentemente consulta por SHA-256 sin subida de archivos; Public API para usos no comerciales/académicos permitidos, no para servicios comerciales sin autorización.
12. **M6 — Acceso remoto:** primero perfiles OpenSSH sin secretos; después elegir un proveedor por necesidad real (Guacamole para gateway web RDP/VNC/SSH, MeshCentral para gestión de endpoints o ShellHub para SSH centralizado Linux). Nexo/Teleport/RustDesk quedan como alternativas, no dependencias obligatorias.
13. **M7 — Empresarial:** multiusuario, sitios, colectores autenticados, PostgreSQL, API e integraciones solo cuando necesidades de adopción y operación lo justifiquen.

Los detalles técnicos, los límites de seguridad y la política de licencias se mantienen en [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). No duplicar aquí un backlog paralelo.

**Puerta común:** ningún cambio se considera disponible hasta estar integrado en `main`, pasar checks aplicables sobre el SHA integrado y tener la aceptación manual correspondiente documentada. Las hipótesis no se presentan como hechos; la evidencia, procedencia y limitaciones deben ser visibles.

**Vigencia:** fotografía consultada el 27/11/2026. Para el estado de una PR o workflow prevalecen siempre su HEAD y los checks actuales de ese SHA, no las referencias históricas de este documento.

## Cómo se mantiene el seguimiento

1. Cada tarea abierta conserva un ID estable (por ejemplo, REL-01 o FIND-02) para vincularla con PR, issue y evidencia.
2. Este roadmap y el issue temporal #219 contienen **solo trabajo pendiente**. No se dejan casillas `[x]`, listas de tareas terminadas ni etapas cerradas dentro del plan activo.
3. Cuando una tarea cumple todos sus criterios, el mismo PR que la integra elimina su entrada de este roadmap y del checklist temporal. La evidencia concisa (PR, commit, CI y, cuando corresponda, sesión humana) pasa a `PROJECT_STATUS.md` y `VALIDATION_MATRIX.md`.
4. Si una prueba falla o queda una parte manual, la tarea permanece abierta y se registra el siguiente paso concreto. Una prueba automatizada no cierra por sí sola una aceptación manual.
5. Una fase deja de figurar en el plan cuando ya no tiene tareas pendientes; no se conserva un apartado de “completadas”. Las fases futuras siguen en orden y con sus dependencias explícitas.
6. **Retirada final del roadmap:** cuando todas las fases y puertas estén terminadas, la persona que cierre el plan actualizará el estado final y la matriz de evidencia, eliminará `docs/ROADMAP.md`, quitará sus enlaces del README y de los documentos de mantenimiento, y cerrará el issue #219. Permanecen como documentación útil `PROJECT_STATUS.md`, `VALIDATION_MATRIX.md`, `IMPLEMENTATION_PLAN.md` y las guías técnicas/de usuario; no se crea un roadmap histórico sustituto.

## Fase 0 — Estabilización y release local 0.10.0

**Estado: en curso. Bloquea la publicación estable.**

El núcleo actual incluye inventario local, observaciones y cambios, descubrimiento LAN limitado, monitores Ping/TCP/HTTP(S), incidentes, consultas DNS, diagnóstico TLS puntual, hallazgos de inventario/monitorización, exportaciones, copia SQLite y extensión Chromium opt-in con importación manual. También existen pruebas automatizadas Python/Node, CI para Python 3.10–3.14 en Windows/macOS/Linux, análisis estático, auditoría de dependencias y artefactos de cadena de suministro.

Quedan por cerrar:

- [ ] **REL-01 — Instalación limpia multiplataforma.** Completar instalación y primer inicio desde descarga limpia, actualización/reinicio y diagnóstico de errores en Windows, macOS y Linux. Registrar sistema operativo, Python, versión/commit y evidencia.
- [ ] **REL-02 — Flujos de inventario y red.** Comprobar descubrimiento explícito, subredes duplicadas/interfaces virtuales, inventario vacío, cambios observados, diagnósticos y límites anunciados. Confirmar que un resultado sin respuesta no se presenta como prueba de ausencia.
- [ ] **REL-03 — Monitorización e incidentes.** Verificar los tipos Ping/TCP/HTTP(S), apertura/actualización/cierre de incidentes, timeouts, retención y webhook opcional con un destino de prueba controlado.
- [ ] **REL-04 — DNS y TLS.** Validar resolución correcta, NXDOMAIN/entrada inválida, timeout, endpoint TLS válido, certificado vencido/no confiable, hostname incompatible y puerto que no habla TLS. El resultado debe distinguir error de red, error de certificado y límite de diagnóstico.
- [ ] **REL-05 — Persistencia y recuperación.** Crear datos representativos, exportarlos, restaurar una copia SQLite en una ubicación segura y comprobar que los registros se recuperan sin pérdida. La regresión automatizada de [PR #159](https://github.com/JavierGrecco/NetSentinel/pull/159) verifica la recuperación del inventario y su historial a través de la aplicación; la [PR #162](https://github.com/JavierGrecco/NetSentinel/pull/162) amplía el control a checks e incidentes de monitorización relacionados. Esto no sustituye la restauración manual. Verificar además retención y borrado selectivo, incluidos el alcance y la confirmación.
- [ ] **REL-06 — Extensión e importación.** Probar manualmente Chrome y Edge: instalación, estado apagado por defecto, activación explícita, pausa, exclusiones, navegación SPA, retención, CSV, previsualización, deduplicación y ausencia de escrituras parciales cuando el lote es inválido. Registrar casos de falsos positivos/negativos del saneamiento.
- [ ] **REL-07 — Privacidad de actividad y correo.** Usar datos sintéticos o exportaciones de auditoría expresamente autorizadas. Confirmar límites de metadatos, rechazo de columnas de cuerpo/adjuntos, retención, exportación y borrado. No usar mensajes o datos personales reales en fixtures públicos.
- [ ] **REL-08 — Controles del repositorio.** Resolver el seguimiento de [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73): verificar en Settings que main exige PR y los checks necesarios, y que no permite force-push ni borrado. La documentación por sí sola no activa estas reglas.
- [ ] **REL-09 — Dependencias y workflows.** Comprobar que las actualizaciones integradas siguen asentadas, que las nuevas PR de Dependabot parten del `main` vigente y que se revisan los cambios de compatibilidad/acciones. Confirmar CI, Security y Supply Chain sobre el SHA candidato. Las antiguas PR #38–#43 se cerraron sin fusionar; sus reemplazos (#148, #150, #151, #152, #153 y #155) ya se integraron tras validación individual. No tratarlas como tareas abiertas.
- [ ] **REL-10 — Atestación de release etiquetado.** Cuando se cree el tag de la versión candidata, comprobar que el workflow de publicación emita la atestación de procedencia del wheel y del SBOM, verificarla desde el artefacto descargado y registrar la evidencia. La construcción, instalación multiplataforma, metadatos, recursos, CLI, SBOM y manifiesto SHA-256 ya están cubiertos en CI; no repetirlos como tareas abiertas.
- [ ] **REL-11 — Documentación de release.** Registrar resultados reales, limitaciones conocidas, pasos de actualización/restauración y procedimiento de reporte de vulnerabilidades. No llamar “probado manualmente” a un test automático.

### Puerta de salida de Fase 0

La 0.10.0 solo se declara estable cuando REL-01 a REL-11 estén cerradas o tengan una excepción documentada, aprobada y de riesgo bajo; la ejecución vigente de CI, Security y Supply Chain esté verde sobre el commit candidato; no haya vulnerabilidades críticas/altas sin tratar en el alcance publicado; los artefactos se instalen desde cero; y no haya fallos bloqueantes conocidos en los recorridos principales. Toda excepción debe indicar responsable, motivo, impacto y plan de resolución.

## Fase 1 — Hallazgos explicables y evidencia correlacionada

**Objetivo:** evolucionar desde una lista de observaciones hacia un flujo de triaje útil, sin exagerar lo que una señal demuestra.

**Prerequisito transversal:** antes de sumar correlaciones y fuentes, separar las responsabilidades internas por dominio sin retrasar las pruebas de estabilización de la Fase 0. La propuesta y sus límites están en [ADR-001: monolito modular](ADR-001-MODULAR-MONOLITH.md). No implica adoptar microservicios ni cambiar el modo de instalación local.

- [ ] **INV-01 — Identidad estable del activo y observaciones.** Separar la ficha lógica del activo de los identificadores observados (MAC, IP, hostname e interfaz). Registrar procedencia, alcance y vigencia temporal de cada identificador; tratar MAC administradas localmente como potencialmente aleatorias/virtuales. Definir reglas conservadoras para MAC rotadas o reutilizadas, IP reasignadas, varias interfaces y observaciones solapadas. No fusionar ni atribuir activos solo por coincidencia de MAC/IP/hostname. Diseñar migración SQLite aditiva y fixtures de compatibilidad antes de cambiar la clave actual del inventario.
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
