# Roadmap maestro de NetSentinel

> **Fuente única de verdad para prioridades, estado y criterios de finalización.** El plan técnico de [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) complementa este documento; no mantiene un backlog paralelo. Para retomar el trabajo sin leer todo el plan, consultá primero [PROJECT_STATUS.md](PROJECT_STATUS.md). La evidencia de pruebas manuales se registra en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## Estado del proyecto

**Estado al 20/10/2026:** estabilización de la versión local 0.10.0. Sigue sin estar lista para declararse estable: faltan validaciones manuales registradas, completar pruebas de recuperación de datos y confirmar la protección efectiva de `main`.

- **Último cambio de código de aplicación:** [`b4ef762`](https://github.com/JavierGrecco/NetSentinel/commit/b4ef762c60871c2f00dd45bc02608292fc6fec7f). Después se integraron y validaron por separado Playwright 1.64 (#174), psutil 7.2.2 (#173), FastAPI 0.143.3 (#175) y CodeQL v4.39.0 (#176). La cabeza actual es [`78bd392`](https://github.com/JavierGrecco/NetSentinel/commit/78bd392aa48e4ffdcb8422cd4ffa5f9a55f40718); CI [18/18](https://github.com/JavierGrecco/NetSentinel/actions/runs/39506529594), Security [correcto](https://github.com/JavierGrecco/NetSentinel/actions/runs/39506529701) y Supply Chain [correcto](https://github.com/JavierGrecco/NetSentinel/actions/runs/39506529692).
- **PR #171 — explorador de red:** cabeza `eb38815`, alineada con `main`; CI 18/18, Security y Supply Chain correctos. Mantener en borrador hasta revisar visualmente el grafo, responsive, teclado y lector de pantalla. [Ver PR](https://github.com/JavierGrecco/NetSentinel/pull/171).
- **PR #177 — importador Zeek:** cabeza `f596475`, apilada sobre #171; CI 18/18 correcto. Security y Supply Chain se deben exigir cuando se dirija a `main`. Falta una prueba manual con archivo autorizado y sanitizado. [Ver PR](https://github.com/JavierGrecco/NetSentinel/pull/177).
- **Mapa mundial de IP:** primera implementación en la rama `feat/ip-world-map-geoip-2026-10` (todavía no está en `main`). Añade una vista separada para IP públicas que ya figuran como destino en eventos locales y usa bases GeoLite2 instaladas por la persona usuaria; no captura tráfico en vivo ni aporta inteligencia de amenazas. La revisión de CI y el recorrido manual quedan pendientes.
- **PR #157 — NetSentinel Forense:** cabeza `122366d`, alineada con `main`; CI 18/18, Security y Supply Chain correctos. Falta ejecutar la guía manual con archivos sintéticos y revisar teclado/accesibilidad antes de salir del borrador. [Ver PR](https://github.com/JavierGrecco/NetSentinel/pull/157).
- **Validación manual de release:** la [matriz](VALIDATION_MATRIX.md) conserva 54 tareas sin marcar y ninguna completada. La [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75) coordina estos recorridos. La prueba de CI no se toma como evidencia de instalación o uso manual.
- **Protección de `main`:** pendiente de configuración y prueba por una persona con permisos de administración. El detalle se mantiene en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).

### Registro de validaciones anteriores (conservado por trazabilidad)

**Estado:** estabilización de la versión local 0.10.0. La versión todavía no está lista para declararse estable: faltan pruebas manuales documentadas en sistemas y navegadores reales, completar las comprobaciones de recuperación de datos y confirmar la protección efectiva de `main`. La validación automática más reciente de `main` y el último SHA de código identificado como validado se indican abajo; no deben confundirse entre sí.

- **Revisión de repositorio al 16/10/2026 (histórica):** [diagnóstico técnico y prioridades](REVIEW_2026-10-16.md). El HEAD consultado es [`8a7756b`](https://github.com/JavierGrecco/NetSentinel/commit/8a7756b1ab2a471401fc7e557ca236f8edc8920e); CI [#38970565141](https://github.com/JavierGrecco/NetSentinel/actions/runs/38970565141), seguridad [#38970565046](https://github.com/JavierGrecco/NetSentinel/actions/runs/38970565046) y cadena de suministro [#38970565067](https://github.com/JavierGrecco/NetSentinel/actions/runs/38970565067) terminaron correctamente para ese SHA. El último SHA de código identificado como validado es [`f23c30c`](https://github.com/JavierGrecco/NetSentinel/commit/f23c30cc85d1e5610ee0ed3254176cbf624728c6); la validación manual y la protección de `main` siguen pendientes.
- **Versión durante el desarrollo:** 0.10.0.dev0.
- **Próxima versión objetivo:** 0.10.0. Es una meta de trabajo, no una fecha prometida.
- **Última mejora funcional:** [PR #142](https://github.com/JavierGrecco/NetSentinel/pull/142), alternativa textual accesible por intervalo para el historial de latencia; commit [1e36530](https://github.com/JavierGrecco/NetSentinel/commit/1e36530629ef9e4310bcd5fce9bfb87aeed234c4). La línea temporal continua entró en la [PR #140](https://github.com/JavierGrecco/NetSentinel/pull/140).
- **Último commit funcional revisado al actualizar esta nota:** [1e36530](https://github.com/JavierGrecco/NetSentinel/commit/1e36530629ef9e4310bcd5fce9bfb87aeed234c4), detalle textual por intervalo para que el historial no dependa del hover ni de interpretar barras gráficas.
- **CI de la comparación inicial (PR #137):** [ejecución #38858149460](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149460) — 18/18 trabajos correctos antes de fusionar.
- **Corrección de alcance (PR #139):** CI [#38858557234](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557234) — 18/18 trabajos correctos; seguridad [#38858557227](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557227) — 2/2 correctos; cadena de suministro [#38858557244](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858557244) — build y SBOM/manifiesto correctos, firma de procedencia omitida por no ser una publicación de release.
- **Seguridad y cadena de suministro de la PR #137:** [ejecución #38858149503](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149503) y [#38858149464](https://github.com/JavierGrecco/NetSentinel/actions/runs/38858149464) finalizaron correctamente antes de fusionar.
- **CI de historial y accesibilidad (PR #142):** [ejecución #38889622598](https://github.com/JavierGrecco/NetSentinel/actions/runs/38889622598) — 18/18 trabajos correctos antes de fusionar; **seguridad:** [#38889622556](https://github.com/JavierGrecco/NetSentinel/actions/runs/38889622556) — 2/2 correctos; **cadena de suministro:** [#38889622586](https://github.com/JavierGrecco/NetSentinel/actions/runs/38889622586) — build, SBOM y manifiesto correctos; firma omitida porque no era una release. Estos checks corresponden al SHA revisado de la PR. No se presentan como ejecuciones posteriores al merge [1e36530](https://github.com/JavierGrecco/NetSentinel/commit/1e36530629ef9e4310bcd5fce9bfb87aeed234c4).
- **Regresión interactiva de Monitorización (PR #144):** [CI #38890406903](https://github.com/JavierGrecco/NetSentinel/actions/runs/38890406903) — 18/18 trabajos correctos; **seguridad:** [#38890406908](https://github.com/JavierGrecco/NetSentinel/actions/runs/38890406908) — 2/2; **cadena de suministro:** [#38890406900](https://github.com/JavierGrecco/NetSentinel/actions/runs/38890406900) — build/SBOM/manifiesto correctos, firma omitida por no ser una release. Prueba con Chromium la apertura de la pestaña Monitores y el detalle por intervalo usando teclado y datos sintéticos. Los checks corresponden a la PR antes de fusionar; no se dispone de una verificación posterior para el merge [d4af736](https://github.com/JavierGrecco/NetSentinel/commit/d4af736bb228bff1dca16148f8e0549c6ac70423).
- **Paridad de tendencia y CSV (PR #146):** se añadió una regresión que comprueba que la exportación semanal conserva los mismos 29 intervalos y el mismo orden que la API, sin inventar latencias para huecos ni para controles fallidos. CI [#38891060852](https://github.com/JavierGrecco/NetSentinel/actions/runs/38891060852) — 18/18 trabajos correctos; seguridad [#38891060572](https://github.com/JavierGrecco/NetSentinel/actions/runs/38891060572) — 2/2; cadena de suministro [#38891060702](https://github.com/JavierGrecco/NetSentinel/actions/runs/38891060702) finalizó correctamente. Son resultados de la PR antes del merge, no una verificación posterior del commit en `main`.
- **Revisión visual y pruebas manuales:** pendientes de registrar en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md), incluidos `UI-09` (comparación de capturas) y `UI-10` (huecos, latencia, detalle por teclado y lector de pantalla en Monitorización). La comprobación automática de Chromium no sustituye la prueba con un lector de pantalla real.
- **Protección efectiva de main:** pendiente de verificación en GitHub; seguimiento en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).
- **Pruebas manuales de instalación y uso:** seguimiento operativo en [issue #75](https://github.com/JavierGrecco/NetSentinel/issues/75); registrar resultados y evidencia en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
- **Dependencias revisadas sobre el `main` actual (16/10/2026):** las PR históricas de Dependabot [#38–#43](https://github.com/JavierGrecco/NetSentinel/pulls) se cerraron sin fusionar porque partían de bases antiguas. En su lugar, se validaron cambios aislados y se integraron: [#148](https://github.com/JavierGrecco/NetSentinel/pull/148) elevó HTTPX a 0.28.1 (CI [#38892973286](https://github.com/JavierGrecco/NetSentinel/actions/runs/38892973286), seguridad [#38892973399](https://github.com/JavierGrecco/NetSentinel/actions/runs/38892973399), cadena de suministro [#38892973137](https://github.com/JavierGrecco/NetSentinel/actions/runs/38892973137)); [#150](https://github.com/JavierGrecco/NetSentinel/pull/150) elevó pytest a 9.1.1 (CI [#38893615554](https://github.com/JavierGrecco/NetSentinel/actions/runs/38893615554), seguridad [#38893615681](https://github.com/JavierGrecco/NetSentinel/actions/runs/38893615681), cadena de suministro [#38893615673](https://github.com/JavierGrecco/NetSentinel/actions/runs/38893615673)); [#151](https://github.com/JavierGrecco/NetSentinel/pull/151) quitó `httpx2` porque no se encontró ningún uso en el código; [#152](https://github.com/JavierGrecco/NetSentinel/pull/152) elevó FastAPI a 0.143.0; [#153](https://github.com/JavierGrecco/NetSentinel/pull/153) elevó Uvicorn a 0.54.0; y [#155](https://github.com/JavierGrecco/NetSentinel/pull/155) elevó setuptools a 84.0.0. Las seis PR de reemplazo pasaron CI, seguridad y cadena de suministro sobre sus heads antes de fusionarse. La firma de procedencia se omite en estos cambios porque no son publicaciones de release. Además, tras integrar las dependencias en el commit [`953da4d`](https://github.com/JavierGrecco/NetSentinel/commit/953da4d37d3f479bffcbf58211c06afd8d4e9baf), los workflows de `push` sobre `main` finalizaron correctamente: CI [#38931543461](https://github.com/JavierGrecco/NetSentinel/actions/runs/38931543461), seguridad [#38931543412](https://github.com/JavierGrecco/NetSentinel/actions/runs/38931543412) y cadena de suministro [#38931543456](https://github.com/JavierGrecco/NetSentinel/actions/runs/38931543456). Estos resultados validan el conjunto integrado en ese commit; los cambios de documentación posteriores vuelven a disparar sus propios workflows.
- **Protección de `main` y validación manual:** la protección efectiva de la rama no pudo verificarse con los permisos actuales de la integración; queda pendiente la comprobación de la persona administradora siguiendo el [issue #73](https://github.com/JavierGrecco/NetSentinel). También siguen pendientes las revisiones en instalación real `UI-09` y con lector de pantalla `UI-10`; las pruebas sintéticas de Chromium no las reemplazan.

Los enlaces de ejecución son una fotografía de la revisión, no un indicador dinámico. Antes de una release debe revisarse la ejecución más reciente de cada workflow y su commit.

## Análisis comparado: visualizaciones, datos y seguridad

Las revisiones estáticas están documentadas en [REFERENCE_PROJECT_REVIEW.md](REFERENCE_PROJECT_REVIEW.md) (ossianericson) y [REFERENCE_PROJECT_REVIEW_BLACSECURITY.md](REFERENCE_PROJECT_REVIEW_BLACSECURITY.md) (blacsecurity). La segunda aporta ideas de actividad en vivo y selección de nodos, además de riesgos que no debemos copiar: API sin protección visible, servicio en todas las interfaces, CORS abierto, secreto fijo, acciones que cambian el firewall y métricas de tráfico estimadas presentadas como actividad.

La dirección del producto queda así:

1. **Grafo LAN de solo lectura:** primera versión integrada mediante la [PR #135](https://github.com/JavierGrecco/NetSentinel/pull/135). La vista parte de las observaciones exactas asociadas a un `scan_id`, muestra la fuente de cada relación y no afirma una conexión física directa por compartir subred. Si no se puede recuperar la evidencia de la lectura, no dibuja vínculos. CI multiplataforma, Security, Supply Chain y el test responsive de Chromium pasaron para el commit revisado de la PR. Queda pendiente la revisión visual manual en instalaciones reales.
2. **Historial de Monitorización:** las PR [#140](https://github.com/JavierGrecco/NetSentinel/pull/140) y [#142](https://github.com/JavierGrecco/NetSentinel/pull/142) integraron una línea temporal continua, estados diferenciados para huecos y fallos sin latencia, y una vista textual desplegable con la hora, métricas y recuentos de cada intervalo. La [PR #144](https://github.com/JavierGrecco/NetSentinel/pull/144) añade una regresión Chromium que abre la pestaña Monitores y el detalle con teclado en un entorno sintético. API, gráfico y CSV conservan las mediciones reales; queda revisar manualmente con teclado/lector de pantalla y seguir puliendo los resúmenes con datos reales.
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
- [ ] **REL-05 — Persistencia y recuperación.** Crear datos representativos, exportarlos, restaurar una copia SQLite en una ubicación segura y comprobar que los registros se recuperan sin pérdida. La regresión automatizada de [PR #159](https://github.com/JavierGrecco/NetSentinel/pull/159) verifica la recuperación del inventario y su historial a través de la aplicación; la [PR #162](https://github.com/JavierGrecco/NetSentinel/pull/162) amplía el control a checks e incidentes de monitorización relacionados. Esto no sustituye la restauración manual. Verificar además retención y borrado selectivo, incluidos el alcance y la confirmación.
- [ ] **REL-06 — Extensión e importación.** Probar manualmente Chrome y Edge: instalación, estado apagado por defecto, activación explícita, pausa, exclusiones, navegación SPA, retención, CSV, previsualización, deduplicación y ausencia de escrituras parciales cuando el lote es inválido. Registrar casos de falsos positivos/negativos del saneamiento.
- [ ] **REL-07 — Privacidad de actividad y correo.** Usar datos sintéticos o exportaciones de auditoría expresamente autorizadas. Confirmar límites de metadatos, rechazo de columnas de cuerpo/adjuntos, retención, exportación y borrado. No usar mensajes o datos personales reales en fixtures públicos.
- [ ] **REL-08 — Controles del repositorio.** Resolver el seguimiento de [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73): verificar en Settings que main exige PR y los checks necesarios, y que no permite force-push ni borrado. La documentación por sí sola no activa estas reglas.
- [ ] **REL-09 — Dependencias y workflows.** Comprobar que las actualizaciones integradas siguen asentadas, que las nuevas PR de Dependabot parten del `main` vigente y que se revisan los cambios de compatibilidad/acciones. Confirmar CI, Security y Supply Chain sobre el SHA candidato. Las antiguas PR #38–#43 se cerraron sin fusionar; sus reemplazos (#148, #150, #151, #152, #153 y #155) ya se integraron tras validación individual. No tratarlas como tareas abiertas.
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
