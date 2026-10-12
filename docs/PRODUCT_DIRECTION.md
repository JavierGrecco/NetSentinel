# Dirección de producto y barra de calidad empresarial

Este documento guía las decisiones de producto de NetSentinel. El objetivo no es maximizar el número de módulos, sino ofrecer observabilidad de red y asistencia de seguridad que una empresa pueda evaluar, operar y confiar.

## 1. Evaluación honesta del producto actual

NetSentinel ya tiene una base funcional útil: inventario local y cambios observados, etiquetas de confianza, descubrimiento acotado, monitores con incidentes e historial, diagnósticos, herramientas DNS, inspección puntual TLS, exportaciones y una arquitectura local-first con SQLite.

Su propuesta diferenciadora es la **visibilidad operativa local, explicable y con bajo impacto sobre la privacidad**. Ejecutarse en la computadora del operador, mantener los datos localmente por defecto y hacer explícito cuándo se genera tráfico son atributos valiosos para consultores, equipos de TI y proveedores de servicios gestionados que necesitan evaluar redes autorizadas sin desplegar primero una plataforma central.

No debe presentarse todavía como una plataforma SOC completa, un EDR, un SIEM, un escáner de vulnerabilidades integral ni un sistema de detección de intrusiones. El producto actual no tiene por sí solo telemetría completa de endpoints, correlación de eventos de seguridad, inventario de software con versiones, un colector central autenticado ni gestión empresarial multiusuario. Las etiquetas comerciales deben seguir a las capacidades comprobadas, no adelantarse a ellas.

## 2. Posicionamiento recomendado

**Categoría:** herramienta local-first de inventario, observabilidad y triaje de redes autorizadas.

**Usuarios iniciales:**
- Consultores de ciberseguridad que realizan relevamientos controlados y necesitan un inventario y un diagnóstico exportables.
- Equipos de TI de pequeñas y medianas organizaciones que necesitan descubrir dispositivos, controlar disponibilidad, documentar cambios y comprobar problemas de conectividad.
- Proveedores de servicios gestionados que necesitan una herramienta local sencilla para primeras comprobaciones, con una posible evolución hacia una operación por sitios.

**Promesa de producto:** “Entender qué hay en la red, qué cambió y qué conviene comprobar a continuación, con evidencia local y sin afirmar más de lo que los datos permiten”.

La privacidad debe ser una ventaja de diseño verificable. En el panel de actividad y en cualquier fuente opcional de telemetría, la documentación debe dejar claro quién autoriza la captura, qué se registra, dónde se almacena, cómo se detiene y cómo se elimina. Evitar presentar telemetría de actividad como vigilancia familiar o laboral encubierta; para un cliente empresarial conviene hablar de *actividad y telemetría autorizada*, con consentimiento, alcance y retención explícitos.

## 3. Diferenciadores que conviene proteger

1. **Local-first de verdad.** Sin cuenta ni nube obligatoria; ningún dato se envía fuera por defecto. Toda integración externa debe ser visible, configurable y documentada.
2. **Alcance seguro.** Acciones de descubrimiento y comprobación explícitas, límites de tiempo y alcance, permisos mínimos y valores seguros por defecto.
3. **Resultados explicables.** Mostrar fuente, hora, evidencia, limitaciones y confianza. Un ping fallido, una MAC desconocida, un registro DNS o un certificado próximo a vencer no prueban por sí solos un compromiso.
4. **Interfaz simple para una tarea técnica.** Un resultado debe contestar: qué se observó, qué significa, cuán seguro es ese juicio y cuál es el próximo paso de bajo riesgo.
5. **Datos portables.** CSV/JSON y respaldos documentados para que el cliente no quede atrapado en la herramienta. Las exportaciones deben minimizar datos, evitar fórmulas activas y excluir secretos.
6. **Funcionalidad verificable.** Lo que la interfaz promete debe tener pruebas reproducibles; lo que depende de un SO, navegador o modelo de router debe tener una prueba manual documentada.

## 4. Prioridades de producto

### P0 — Confianza y calidad de la versión

- Completar los recorridos manuales en Windows, macOS y Linux: instalación, primer uso, descubrimiento, diagnóstico, monitorización, respaldo/restauración, importación/exportación y borrado selectivo.
- Probar el flujo de la extensión en Chrome/Edge, con opt-in, pausa, exclusiones, retención y saneamiento. Verificar tanto resultados esperados como límites y falsos positivos.
- Añadir una matriz de casos de aceptación para las herramientas DNS y TLS, incluidos timeout, entrada inválida, error de certificado y endpoint no disponible.
- Corregir inconsistencias de interfaz y documentación: mismo nombre para cada módulo, estado actual visible, errores accionables y avisos de privacidad junto al control que inicia la recolección.
- Publicar versiones solo cuando CI, empaquetado y recorridos manuales aplicables estén aprobados; las pruebas automatizadas no se deben describir como pruebas manuales.

### P1 — Motor de hallazgos con evidencia

Es el mayor salto funcional después de estabilizar los flujos actuales. Centralizar cambios del inventario, incidentes de disponibilidad y resultados de diagnóstico/TLS en una bandeja de hallazgos, sin mezclar simples observaciones con alertas de seguridad confirmadas.

Cada hallazgo debe incluir, como mínimo:
- identificador y categoría;
- activo afectado y fuente;
- primera y última observación;
- evidencia reproducible y contexto;
- severidad y confianza separadas;
- estado (nuevo, revisado, aceptado como riesgo, resuelto);
- explicación en lenguaje claro y siguiente comprobación recomendada;
- control para reconocer falsos positivos y registrar la razón.

No crear una puntuación opaca. No llamar “ataque”, “intrusión” o “dispositivo comprometido” a un evento sin evidencia suficiente. La correlación debe empezar con reglas deterministas y pruebas de regresión antes de considerar modelos heurísticos.

### P2 — Contexto real de activos e infraestructura

- Elegir un modelo concreto de router/AP/resolvedor a partir de hardware, necesidades y documentación/API disponibles; no desarrollar un adaptador genérico especulativo.
- Empezar con integraciones de solo lectura para información DHCP, dispositivos asociados y registros DNS/flujo realmente proporcionados por ese equipo.
- Mantener procedencia, marca de tiempo, estado de la conexión, límites de consulta y fixtures de ejemplo. No atribuir una IP o un nombre a una persona sin evidencia.
- Construir una topología basada en relaciones observadas, diferenciando relación confirmada, inferida e incierta.
- Añadir contexto de fabricante solo como indicio: una MAC, nombre o fabricante se puede falsear y no es identidad autenticada.

### P3 — Uso empresarial y operación en varias sedes

Esta etapa no debe adelantarse a la estabilización de la versión local. Antes de ofrecer uso remoto, centralizado o por varios clientes, hacen falta:

- autenticación robusta y autorización por rol y por sitio;
- alta explícita, identidad de agente, rotación y revocación de credenciales;
- TLS de transporte, protección contra repetición, limitación de tasa y registro de auditoría;
- aislamiento fuerte entre clientes/sitios y pruebas que intenten cruzar esos límites;
- migraciones de base de datos versionadas, estrategia de respaldo/restauración y actualización segura;
- política de retención y eliminación aplicable a todos los datos y exportaciones;
- configuración de secretos fuera del repositorio, la base de datos legible y los registros.

No exponer la API actual de ingestión a la LAN como atajo. El uso remoto requiere un diseño de seguridad específico y una revisión antes de habilitarlo.

### P4 — Integración operativa y ecosistema

Cuando exista un modelo de hallazgos confiable, agregar en este orden según demanda real:
1. exportación de informes de hallazgos con evidencia y remediación;
2. métricas Prometheus de cardinalidad acotada;
3. integraciones documentadas con webhooks y formatos de intercambio útiles para SIEM;
4. perfiles de red/sitio con aislamiento comprobado;
5. adaptadores adicionales y navegadores, solo cuando exista una fuente real y un caso de uso validado.

Una matriz de cobertura NIST CSF 2.0 puede indicar qué evidencia aporta NetSentinel y qué brechas permanecen. Debe ser una guía de trazabilidad, nunca una certificación automática ni una afirmación de cumplimiento.

## 5. Barra obligatoria para cualquier nueva función

Antes de aceptar una propuesta, responder por escrito:

- **Problema:** ¿quién tiene el problema y qué tarea concreta se vuelve mejor?
- **Evidencia:** ¿de qué dato parte y qué no permite concluir?
- **Autorización y alcance:** ¿quién inicia la acción, qué sistemas toca y cómo se limita?
- **Privacidad:** ¿qué datos recolecta, dónde quedan, quién puede verlos y cómo se detienen/eliminan?
- **Comportamiento ante fallos:** ¿hay timeout, manejo de entrada malformada, cancelación y mensajes comprensibles?
- **Seguridad:** ¿añade un endpoint, privilegio, secreto, dependencia o canal externo? Si es así, incluir modelo de amenazas y pruebas específicas.
- **Pruebas:** casos positivos, negativos, timeout, datos inválidos, regresiones y compatibilidad aplicable. No depender de Internet ni de equipos reales en las pruebas unitarias.
- **Operación:** ¿se documentaron instalación, límites, actualización, respaldo/restauración y recuperación?
- **UX:** ¿se entiende el resultado y el riesgo sin conocer los detalles internos?
- **Reversibilidad:** ¿puede desactivarse sin perder datos preexistentes? Las acciones destructivas deben tener previsualización y confirmación inequívoca.
- **Beneficio neto:** ¿la capacidad mejora de manera significativa el flujo actual o sería mejor integrarla con una herramienta especializada?

Si no puede responderse a estas preguntas, la función debe quedar como experimento o propuesta de diseño, no como capacidad lista para clientes.

## 6. Barra de seguridad del propio producto

- Mantener matriz CI para las versiones de Python y sistemas operativos realmente soportados, pruebas del frontend JavaScript y validación de los recursos del paquete.
- Incorporar progresivamente revisión de dependencias y vulnerabilidades, análisis estático, detección de secretos y revisión de cambios sensibles. Resolver hallazgos reales; no agregar herramientas como decoración de CI.
- Generar un SBOM para cada release y evaluar checksum, firma del artefacto y procedencia del build. SLSA documenta niveles incrementales de garantías y procedencia; no declarar un nivel que no se haya demostrado.
- Usar OWASP ASVS como lista de verificación para el panel web/API, adaptada a la arquitectura local, y revisar especialmente límites de confianza, entradas, autorización de escritura, CSRF/origen, exposición de datos y secretos.
- Versionar el esquema SQLite y probar migraciones con bases antiguas reales o fixtures representativos.
- Usar instalaciones limpias para comprobar que los lanzadores y los paquetes funcionan sin dependencias accidentales del entorno de desarrollo.
- Publicar matriz de sistemas probados, limitaciones conocidas, pasos para reportar vulnerabilidades y un proceso de respuesta a incidencias.

Referencias para orientar, no certificaciones obtenidas:
- [NIST Cybersecurity Framework 2.0](https://www.nist.gov/cyberframework) — resultados de gestión de riesgo, de Govern a Recover.
- [OWASP Application Security Verification Standard](https://owasp.org/www-project-application-security-verification-standard/) — verificación de seguridad de la aplicación web/API; usar una versión estable y fijada para cada ciclo de revisión.
- [SLSA](https://slsa.dev/spec/v1.2/) — seguridad de la cadena de suministro y procedencia de artefactos.
- [CISA Secure by Design](https://www.cisa.gov/securebydesign) — seguridad como responsabilidad del fabricante y condición de diseño.

## 7. Cómo medir si NetSentinel es más valioso

Evitar usar solamente cantidad de funciones o de líneas de código. Medir:
- tiempo desde el inicio hasta un inventario útil;
- porcentaje de recorridos críticos que terminan sin ayuda externa;
- tasa de falsos positivos y cantidad de hallazgos con evidencia suficiente;
- tiempo para entender y resolver un incidente de disponibilidad;
- porcentaje de fuentes con procedencia y fecha claras;
- regresiones por sistema operativo y tiempo para reproducirlas;
- fallos de actualización/restauración;
- permisos requeridos y cantidad de datos que salen de la computadora;
- interoperabilidad de exportaciones;
- tiempo necesario para instalar, probar y quitar la herramienta limpiamente.

## Criterio final

NetSentinel será más atractivo para una empresa de ciberseguridad cuando sea confiable, preciso, interoperable y fácil de operar; no cuando prometa hacerlo todo. La secuencia recomendada es: **estabilizar → evidenciar → correlacionar → integrar fuentes reales → asegurar operación multiusuario/remota → ampliar integraciones**.
