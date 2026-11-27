# Plan técnico de implementación de NetSentinel

**Propósito:** conservar las decisiones de arquitectura y los criterios técnicos para evolucionar NetSentinel sin perder la identidad del producto ni acumular integraciones innecesarias.

Este documento conserva las decisiones técnicas y los contratos de largo plazo. Mientras haya trabajo pendiente, el orden y la prioridad se mantienen en [ROADMAP.md](ROADMAP.md), y el seguimiento operativo en el [issue temporal #219](https://github.com/JavierGrecco/NetSentinel/issues/219). Ambos son temporales: al completar todas las fases se eliminan el roadmap y el issue. Este plan técnico, [PROJECT_STATUS.md](PROJECT_STATUS.md) y [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md) permanecen como documentación de arquitectura, estado y evidencia. La aceptación humana se registra en la matriz.

## 1. Dirección de producto

NetSentinel evolucionará como **Network Operations & Intelligence**, una plataforma local-first para observar, comprender, monitorizar, diagnosticar, investigar y, mediante proveedores externos, intervenir sobre infraestructura autorizada.

Se divide en tres dominios funcionales:

1. **NetSentinel Red:** producto principal. Inventario, observaciones, topología, monitorización, diagnóstico, hallazgos, investigaciones e informes.
2. **NetSentinel Forense:** gestión de casos y evidencias, integridad/custodia, análisis estático y dinámico mediante herramientas especializadas, inteligencia de amenazas e informes.
3. **Acceso e intervención:** integraciones opcionales para SSH, RDP, VNC, SFTP y administración remota. No es un gestor propio de credenciales ni una plataforma de acceso privilegiado.

Los dominios comparten identificadores de activos, investigaciones y referencias a evidencias cuando corresponda, pero no mezclan responsabilidades ni permisos. Un evento de Red puede vincularse a un caso Forense si existe evidencia explícita de esa relación; no se crea una relación por coincidencia de nombre o cercanía temporal.

No presentar NetSentinel como SIEM, SOC, NDR, EDR, antivirus integral, plataforma de adquisición forense universal ni sistema certificado de cadena de custodia mientras esas capacidades no estén implementadas y validadas.

## 2. Arquitectura general

Mantener una **aplicación modular de despliegue único** con Python/FastAPI, SQLite y una interfaz web local. No introducir microservicios, Kubernetes ni PostgreSQL por anticipación. La separación de procesos sí se justifica para ejecutar parsers y motores que reciben archivos no confiables, por aislamiento de seguridad y no por una preferencia arquitectónica.

Capas y responsabilidades:

- **Composición:** crea la aplicación, configura dependencias y registra routers.
- **API:** valida contratos HTTP y delega casos de uso; no ejecuta SQL ni contiene reglas de dominio.
- **Servicios de aplicación/dominio:** aplican reglas deterministas, producen resultados tipados y no dependen de FastAPI.
- **Puertos/proveedores:** definen contratos pequeños para fuentes de inventario, sondas, análisis, inteligencia y acceso remoto.
- **Adaptadores:** encapsulan protocolos, bibliotecas, procesos externos y APIs de terceros.
- **Persistencia:** cada dominio es dueño de sus consultas y escrituras; las migraciones son versionadas, aditivas cuando sea viable y probadas con bases antiguas.
- **Workers aislados:** ejecutan parsers/motores sobre copias de trabajo, con límites de recursos y permisos mínimos.

La integración entre módulos dentro del monolito usa interfaces Python tipadas; no HTTP/RPC interno. Un proceso externo se comunica por un contrato explícito y una interfaz restringida. Las dependencias deben tener una dirección definida y sin ciclos. No mover archivos por estética: modularizar cuando se trabaje sobre una responsabilidad con pruebas y contrato definidos.

## 3. Contratos de datos y trazabilidad

Los datos procedentes de fuentes distintas deben conservar, según corresponda:

- Identificador estable del objeto (activo, evidencia, investigación o tarea).
- Fuente/proveedor y versión del adaptador.
- Identificador de origen y formato.
- Hora observada, hora recibida y zona/offset cuando estén disponibles.
- Alcance, método, parámetros no secretos y versión de herramienta.
- Calidad, frescura, cobertura, estado y errores parciales.
- Transformación aplicada y vínculo al dato original.
- Confianza separada de severidad y de conclusión.

No usar IP/MAC/hostname como identidad permanente del activo. Una IP o MAC es una observación vinculada a un activo durante un período; puede cambiar, ser compartida, aleatorizada o suplantada.

La semántica debe distinguir valores válidos, ausentes, vacíos, inválidos, ambiguos y desconocidos. Nunca convertir ausencia en cero, false o desconexión sin preservar que el dato original no estaba disponible. Las sugerencias no deben convertirse en autocorrecciones silenciosas. Las unidades y conversiones deben ser explícitas, dimensionalmente válidas y reproducibles.

La información se clasifica como:
- **Observación:** lo que reportó directamente una fuente.
- **Dato derivado:** transformación determinista de una o más observaciones.
- **Hipótesis:** interpretación posible que aún requiere comprobación.
- **Conclusión:** interpretación aceptada por un responsable y sustentada en evidencia.
- **Pendiente/inconcluso:** fuente, cobertura o análisis insuficiente.

La proximidad temporal no prueba causalidad. La ausencia de registros no prueba ausencia de actividad.

## 4. NetSentinel Red

### 4.1 Activos e inventario
Consolidar identidad estable, IP/MAC/hostname, interfaces, fabricantes como indicio, observaciones históricas, primera/última observación, cambios y confianza. Cada dato debe conservar procedencia, fecha y alcance de la lectura.

### 4.2 Topología
Distinguir vínculos observados directamente, importados desde fuentes externas, inferidos y desconocidos. Las capturas históricas deben conservar el contexto exacto del scan_id; no sustituir IP pasadas por valores actuales ni dibujar relaciones físicas solo porque dos equipos aparecieron en la misma subred.

### 4.3 Monitorización y diagnóstico
Fortalecer primero Ping, TCP, HTTP/HTTPS, DNS y TLS, incluyendo timeouts, errores, reintentos, latencia, disponibilidad, incidentes, recuperación, retención y frescura. Un check no ejecutado, una fuente no disponible y un resultado vacío son estados diferentes. La evaluación debe explicar qué se comprobó y qué no.

### 4.4 Hallazgos e investigaciones
Unificar observaciones de inventario, monitores, DNS/TLS persistidos y fuentes importadas autorizadas. Las reglas de correlación deben ser deterministas, acotadas, explicables y parametrizadas. Mostrar el intervalo temporal y las condiciones de correlación; no afirmar causa raíz, identidad o intrusión por coincidencia.

### 4.5 Fuentes de infraestructura: SNMP
La primera ampliación de infraestructura será SNMPv3 de solo lectura. Prototipar con PySNMP y SNMPSim antes de integrar equipos reales. Empezar por identidad del dispositivo, interfaces, estado y contadores disponibles. Después evaluar LLDP, CDP, BRIDGE-MIB, VLAN y relación switch/puerto en equipos compatibles. Credenciales fuera del inventario y de logs; consultas con timeouts, límites y manejo de errores parciales; no habilitar SNMP SET.

Referencias de diseño, no dependencias obligatorias:
- Netdisco: relaciones entre dispositivos, interfaces, switches y puertos.
- NetBox: integración de API, no recrear su función de fuente de verdad de infraestructura.
- Netmiko + TextFSM + NTC Templates: CLI multivendor opcional más adelante.
- Nornir: ejecución coordinada multi-equipo cuando exista un caso concreto.
- Prometheus Python client: exponer métricas propias de cardinalidad limitada cuando haya necesidad.
- NetworkX: solo si aparecen algoritmos de grafo que el modelo actual no cubra.

### 4.6 Informes
Conservar CSV/JSON portables, seguros y documentados. PDF se agrega como presentación legible de resultados ya estructurados, no como única fuente de verdad. Las exportaciones minimizan datos, excluyen secretos y evitan fórmulas activas.

## 5. NetSentinel Forense

### 5.1 Preservación y custodia
Mantener separados:
1. Original recibido.
2. Adquisición/copia maestra verificada.
3. Copia de análisis.

NetSentinel no debe escribir en el original ni improvisar un recolector universal de discos, memoria o móviles. Registrar autorización, alcance, fuente, persona que entrega/recibe, tiempos, herramienta y versión, hashes, transferencias, errores, copias, verificaciones y disposición.

Los hashes detectan diferencias respecto de una referencia; no demuestran por sí solos autenticidad, autoría ni cadena de custodia íntegra. La auditoría encadenada actual necesita autenticación real de operadores, roles, separación de tareas y anclaje/firma externos con clave fuera del equipo. Un administrador capaz de reescribir SQLite puede alterar toda la base y recalcular sus digests.

Mantener el módulo experimental hasta completar pruebas sintéticas, aceptación manual, revisión independiente, identidad autenticada, controles de acceso, anclaje externo, backup/restauración y procedimientos institucionales. No afirmar certificación pericial automática.

### 5.2 Motor de análisis de archivos
Definir un contrato pequeño FileAnalysisProvider con capacidades, versiones, formatos, parámetros permitidos, límites, resultado, errores y cobertura. Cada análisis se vincula a una evidencia y a una copia de trabajo previamente verificada.

Flujo obligatorio:
1. Seleccionar copia de análisis autorizada.
2. Verificar hash inicial.
3. Identificar tipo real por contenido, no solo extensión.
4. Ejecutar motor en entorno aislado.
5. Registrar motor/build, firmas/reglas, parámetros, límites y errores.
6. Preservar salida original y normalizar hallazgos por separado.
7. Verificar nuevamente hash de la copia.
8. Vincular hallazgos a evidencia, copia, motor y versión.
9. Emitir informe con límites y cobertura.

Límites de seguridad: tamaño, cantidad de archivos, profundidad de archivos anidados, ratio de expansión, CPU, memoria, tiempo, concurrencia y espacio temporal. Rechazar rutas inseguras, traversal, symlinks no autorizados y extracción fuera del directorio de trabajo. El worker no accede a credenciales, carpetas del usuario, secretos ni red por defecto. Limpiar el entorno al finalizar y registrar fallos sin volcar contenidos sensibles a logs.

### 5.3 Motores y estrategia de integración

| Proyecto | Función | Integración recomendada |
|---|---|---|
| ClamAV | Firmas antivirus para archivos generales | Proceso/servicio externo opcional; respetar GPL-2.0 |
| YARA-X | Reglas de detección de patrones | Motor preferido para reglas nuevas; BSD-3-Clause; comprobar compatibilidad de reglas |
| YARA clásico | Compatibilidad con reglas existentes | Adaptador opcional cuando una regla no sea compatible con YARA-X |
| Androguard | Estructura, manifiesto, DEX y análisis estático Android | Biblioteca Python con versión publicada fijada; Apache 2.0 |
| MobSF | Análisis móvil estático/dinámico | Servicio externo opcional por API; GPL-3.0-only; no copiar código al núcleo MIT |
| APKiD | Identificar packers/ofuscadores | Evaluar licencia dual y uso comercial antes de integrar |
| Quark Engine | Reglas de comportamiento Android | Servicio opcional; GPL-3.0; no incorporar al núcleo sin análisis legal |
| CAPEv2 | Sandbox de ejecución de muestras | Laboratorio externo, separado y descartable; GPL-3.0 declarada en LICENSE; resolver discrepancias de metadatos antes de reutilizar código |

Androguard 5 en el repositorio principal no debe tratarse como release estable mientras su distribución publicada y documentación de empaquetado no estén resueltas. No seguir ciegamente una rama de desarrollo; fijar la versión exacta probada.

El análisis dinámico Android necesita emulador/dispositivo dedicado y preparación específica. CAPE necesita máquinas virtuales descartables. Ninguna muestra sospechosa se ejecuta dentro del proceso principal de NetSentinel ni en CI normal. Usar EICAR y muestras sintéticas/benignas en pruebas automatizadas; no alojar malware activo en el repositorio público.

Estados de resultado: **malicioso**, **sospechoso**, **sin detecciones** e **inconcluso**. Nunca traducir “sin detecciones” en “seguro”. Una APK ofuscada o con permisos amplios no es automáticamente malware; el informe debe explicar evidencia y contexto.

### 5.4 Inteligencia de amenazas y VirusTotal
Implementar HashReputationProvider desacoplado de los motores locales.

Orden de evaluación:
- CIRCL hashlookup como primer proveedor para identificar archivos conocidos (no es antivirus).
- MalwareBazaar y ThreatFox para muestras/indicadores, sujeto a términos y condiciones de sus APIs comunitarias/comerciales.
- URLhaus para reputación de URL que distribuyen malware.
- VirusTotal como proveedor opcional, nunca como dependencia obligatoria.

VirusTotal:
- Preferir consulta por SHA-256 de reportes existentes; no subir evidencia por defecto.
- La clave pertenece a cada usuario y se guarda localmente de manera segura; nunca en el repositorio, fixtures o logs.
- Activación expresa, aviso de qué dato (hash) se envía, proveedor destinatario, caché, límites, cuotas y manejo de errores.
- Public API solo en escenarios no comerciales/académicos permitidos por sus términos vigentes; no asumir que un proyecto open source y gratuito autoriza usos comerciales de consultoras, MSP o clientes.
- Para un uso comercial, requerir autorización/licencia adecuada. La modalidad de análisis privado es distinta del análisis estándar y no debe prometer los mismos veredictos.
- Ofrecer también apertura manual de un reporte por hash sin API.
- Desactivar proveedor externo no debe impedir análisis local.

No enviar muestras, secretos, datos personales o evidencia sensible a servicios externos sin autorización explícita y evaluación de términos.

## 6. Acceso remoto e intervención

Definir un contrato RemoteAccessProvider y perfiles de conexión sin secretos. Registrar proveedor, activo vinculado, protocolo, referencia remota, operador, hora, estado y resultado. No almacenar passwords, tokens, claves privadas ni grabaciones de terminal de otros proveedores.

Primer paso: exportar perfiles OpenSSH estándar con Host, HostName, User, Port y ProxyJump cuando aplique. Después elegir un solo proveedor según necesidad:
- Apache Guacamole: gateway web para RDP/VNC/SSH; Apache 2.0.
- MeshCentral: administración de endpoints con agente, escritorio, terminal y archivos; Apache 2.0.
- ShellHub: SSH centralizado para Linux/dispositivos detrás de NAT; Community Apache 2.0.
- Teleport: acceso privilegiado con identidad/MFA/políticas; evaluar AGPL y complejidad.
- Nexo y RustDesk: proveedores/alternativas posibles, no dependencias preferidas.

No integrar tres plataformas a la vez ni copiar sus servidores completos. Primero perfiles; luego una acción real end-to-end y asociación de sesión con investigación. La elección entre Guacamole, MeshCentral y ShellHub depende de la primera necesidad validada; no hay un ganador universal.

El servidor NetSentinel seguirá en loopback hasta que existan autenticación, autorización, TLS, protección de origen/CSRF, enrolamiento, revocación, auditoría, threat model y pruebas negativas. El proveedor remoto administra sus propias credenciales, MFA y revocaciones.

## 7. Preparación empresarial

Solo con necesidad y adopción demostradas:
- usuarios, organizaciones, sitios, roles y aislamiento;
- colectores remotos autenticados, enrolamiento, rotación/revocación, anti-replay y límites;
- PostgreSQL cuando concurrencia y multiusuario lo requieran;
- API estable, métricas Prometheus e integración NetBox;
- backup/restauración y controles de seguridad por sitio.

No convertir el producto local en una plataforma centralizada por anticipación. Conservar el monolito modular y separar procesos solo por seguridad, escalabilidad demostrada o ciclo de despliegue distinto.

## 8. Licencias, dependencias y procedencia

La licencia MIT de NetSentinel no cambia la licencia de herramientas externas, reglas, firmas, modelos ni datasets. Antes de incorporar cada componente:
1. registrar repositorio, tag/commit, mantenedor y fecha de revisión;
2. identificar licencia real de cada componente y recurso;
3. revisar dependencias transitivas, avisos, marcas y restricciones de uso;
4. distinguir biblioteca integrada, proceso independiente, API y servicio administrado;
5. fijar versión, verificar mantenimiento, CVEs y compatibilidad;
6. documentar atribución en THIRD_PARTY_NOTICES.md, SBOM y notas de distribución;
7. definir estrategia de actualización y alternativa si el proveedor deja de mantenerse.

No asumir que ejecutar un programa externo elimina todas las obligaciones de distribución o uso. En caso de duda sobre copyleft, licencia dual, marcas o condiciones de API, dejar la integración deshabilitada hasta resolverlo.

## 9. Estrategia de pruebas y puertas de calidad

- **Unitarias:** normalización, contratos, parsers, reglas de confianza, hashes, límites y funciones puras.
- **Integración:** API/SQLite, migraciones, permisos, repositorios, procesos y respuestas externas simuladas.
- **Seguridad:** entradas malformadas, traversal, archivos comprimidos anidados, límites, timeouts, errores, SSRF, origen/CSRF, secretos, permisos y aislamiento.
- **Compatibilidad:** matriz OS/Python, versiones de motores, formato de archivos y wheel.
- **Supply chain:** dependencias fijadas, análisis de vulnerabilidades, detección de secretos, SBOM, manifiesto y procedencia.
- **Manual:** instalación limpia, actualización, restauración, accesibilidad, interacción visual y pruebas contra un equipo/fuente real autorizada.
- **Reproducibilidad:** fixtures sintéticos con resultados y hashes esperados, versiones y comandos registrados.

Cada cambio debe pasar los controles aplicables en el SHA exacto que se integra. Las pruebas automáticas no sustituyen aceptación manual, revisión independiente ni validación del proveedor real. Ninguna función se declara disponible hasta que esté integrada en main y su estado esté actualizado en PROJECT_STATUS.md.

## 10. Criterios para considerar el producto maduro

NetSentinel mejora cuando un operador puede completar tareas reales y reproducibles, entender la procedencia y los límites de los datos, investigar sin perder el contexto, actuar con autorización y producir informes útiles.

Medir utilidad, confiabilidad, seguridad, interoperabilidad y mantenibilidad. No utilizar como indicadores principales el número de dependencias, commits, ramas, módulos o integraciones.
