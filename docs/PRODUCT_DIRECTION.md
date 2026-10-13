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

## 4. Prioridades de producto y secuencia de ejecución

El orden exacto, las tareas y el estado se mantienen en [ROADMAP.md](ROADMAP.md), que es la fuente única de verdad. Las fases de abajo describen la secuencia de producto y sus puertas; las casillas de implementación, los IDs de tarea y la evidencia de pruebas viven en el roadmap y en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

### Fase 0 — Estabilización de la versión local

- Completar recorridos manuales en Windows, macOS y Linux: instalación limpia, primer uso, descubrimiento, monitorización, DNS/TLS, backup/restauración, importación/exportación y borrado selectivo.
- Probar Chrome y Edge con opt-in, pausa, exclusiones, retención y saneamiento; revisar falsos positivos y límites.
- Alinear metadatos de versión, changelog y wheel; comprobar CI, seguridad, supply chain y configuración de protección de main.
- Publicar 0.10.0 solo cuando se cumplan los criterios de salida de la Fase 0 del roadmap. Las pruebas automáticas no se deben describir como validaciones manuales.

### Fase 1 — Hallazgos explicables y evidencia

La primera iteración ya expone la API y una bandeja visual a partir de eventos persistidos de inventario e incidentes de disponibilidad. Antes de incorporar DNS/TLS persistidos, definir esquema, migraciones, retención, eliminación y controles de falsos positivos.

- Registrar fuente, hora, activo, evidencia, estado, severidad y confianza por separado.
- Introducir reglas deterministas, agrupación/deduplicación y transiciones de estado reproducibles.
- Permitir revisar y exportar evidencia sin renderizar contenido externo como HTML.
- No atribuir causa raíz ni declarar un equipo comprometido basándose solo en una señal ambigua.

### Fase 2 — Fuentes reales de infraestructura

- Elegir un router/AP/resolvedor concreto a partir de su API y un caso de uso real.
- Empezar con lecturas acotadas y de solo lectura; registrar fuente, hora, frescura y limitaciones.
- Incorporar timeouts, límites de consulta, fixtures sanitizados, manejo de errores parciales y secretos fuera de logs/repositorio.
- Ampliar a DHCP/SNMP u otras fuentes solo después de validar utilidad y compatibilidad de la primera integración.

### Fase 3 — Informes, métricas y usabilidad operativa

- Producir informes reproducibles por activo/periodo que incluyan evidencia, fuentes, tiempos y limitaciones, con exportaciones seguras y datos sensibles mínimos.
- Añadir métricas Prometheus de cardinalidad limitada; no etiquetar métricas con URL, IP arbitraria, identificadores personales o secretos.
- Mejorar accesibilidad, errores accionables, navegación entre hallazgos y datos de origen.
- Diseñar perfiles de red/sitio con aislamiento para evitar mezclar direcciones coincidentes entre ubicaciones.
- Medir utilidad mediante tareas completadas, tiempo hasta un inventario útil, restauración y falsos positivos reportados; no enviar telemetría de uso externa por defecto.

### Fase 4 — Operación remota y multi-sede

No abrir la API actual a la LAN como atajo. Antes de habilitar operación remota hacen falta diseño de amenazas y pruebas específicas de:

- TLS, autenticación, autorización por dispositivo/rol/sitio y enrolamiento explícito;
- expiración, rotación y revocación de credenciales;
- anti-replay, idempotencia, límites de tasa/tamaño y auditoría;
- aislamiento probado entre sitios y recuperación segura de datos;
- migraciones versionadas, respaldo/restauración y actualización segura.

La función remota se habilita solo después de que las pruebas negativas de autenticación, autorización, repetición e aislamiento estén verdes y la configuración segura por defecto se haya verificado.

### Fase 5 — Integración y ecosistema

- Versionar el contrato de webhooks y formatos de intercambio antes de integrar un SIEM.
- Seleccionar cualquier conector de auditoría de correo a partir de permisos y capacidades verificados de un proveedor concreto; limitarse inicialmente a metadatos autorizados.
- Evaluar Firefox u otros agentes opt-in después de probar la base actual y definir desactivación, retención y eliminación.
- Mantener una matriz de evidencia/brechas frente a marcos pertinentes como NIST CSF 2.0 o CISA CPG; nunca presentarla como certificación automática.

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
