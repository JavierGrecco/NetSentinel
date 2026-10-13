# Plan técnico de implementación

Este documento describe cómo abordar técnicamente las fases. **El orden, el estado y la definición de prioridades se mantienen exclusivamente en [ROADMAP.md](ROADMAP.md)**. Los criterios de pruebas manuales se registran en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).

## 1. Arquitectura existente y alcance confirmado

La aplicación es local-first: Python/FastAPI, SQLite y paneles HTML/CSS servidos localmente. El paquete define su versión en src/netsentinel/__init__.py y pyproject.toml la obtiene de forma dinámica; no mantener un segundo número de versión independiente en pyproject.toml.

Módulos/capacidades implementados en el código revisado:

- **Inventario y observaciones:** dispositivos, direcciones IPv4/IPv6 observadas, fabricantes como indicio, historial y etiquetas de confianza.
- **Descubrimiento local:** bajo demanda y con límites explícitos para subredes IPv4 privadas; no equivale a un escaneo exhaustivo de IPv6 o de toda la red.
- **Monitorización:** checks Ping/TCP/HTTP(S), muestras, incidentes, recuperación, tendencias, retención y webhook opcional.
- **Diagnóstico:** conectividad, configuración/consultas DNS bajo demanda y handshake TLS puntual con validación de certificado; la prueba TLS no solicita contenido HTTP.
- **Hallazgos:** vista y API compuestas de solo lectura a partir de eventos de inventario e incidentes de monitorización persistidos; todavía no ofrece correlación de causa raíz ni ingiere automáticamente resultados DNS/TLS puntuales.
- **Actividad autorizada:** sesiones locales acotadas, importación/exportación CSV, filtros y borrado selectivo. La extensión Chromium está apagada por defecto y su transferencia al backend sigue siendo manual.
- **Correo:** importación de metadatos de auditoría autorizados; no existe conexión automática a buzones ni se guardan cuerpos o adjuntos.
- **Distribución:** CLI, lanzadores por sistema operativo, paquete wheel y recursos estáticos; CI multiplataforma, tests Node de la extensión, análisis de seguridad y workflow de cadena de suministro.

La disponibilidad de código y tests automáticos no demuestra por sí sola que un recorrido real de instalación, navegador, router o restauración haya sido probado. Esos estados deben tomarse de la matriz de validación.

## 2. Reglas de implementación

### Contratos de datos y migraciones

- Las entidades procedentes de distintas fuentes deben conservar source/provenance, hora de observación, identificador de origen y calidad/frescura del dato.
- No equiparar una observación a una conclusión de seguridad. Mantener evidencia, severidad y confianza como campos diferentes.
- Las migraciones SQLite deben ser aditivas cuando sea viable, versionadas y probadas contra fixtures de bases anteriores; ninguna migración debe borrar datos silenciosamente.
- Cada política de retención debe indicar qué tabla/dato afecta, el valor por defecto, rango configurable y si los incidentes o el inventario quedan fuera de la limpieza.
- Toda eliminación masiva requiere alcance explícito, previsualización y confirmación inequívoca, con comprobaciones transaccionales.

### Conectores y adaptadores

- Empezar por un proveedor real cuya API/documentación pueda verificarse; no programar un “adaptador genérico” sin contrato operativo.
- Hacer llamadas de solo lectura cuando sea posible y aplicar timeouts, límites de resultados, paginación y manejo de errores parciales.
- Nunca guardar credenciales, tokens, archivos de clientes o datos reales sensibles en el repositorio, fixtures, trazas o mensajes de error.
- Utilizar fixtures sanitizados para que la CI sea determinista sin conectarse a routers ni servicios personales.
- Mostrar origen, momento de captura, limitaciones y errores de actualización al operador.

### Seguridad de API y operación remota

- El despliegue de referencia sigue limitado a loopback y el backend no debe exponerse en LAN/Internet como atajo.
- Cualquier cambio de endpoints, origen/CSRF, cabeceras, CSP, autenticación, secretos o recepción de datos requiere tests negativos además de casos válidos.
- Antes de ingestión remota son obligatorios diseño de amenazas, TLS, autenticación/autorización por dispositivo, enrolamiento, revocación, anti-replay, límites de tasa y tamaño, auditoría, aislamiento por sitio y recuperación segura.
- No agregar datos sensibles a etiquetas de métricas, logs, exportaciones ni atributos de error.

## 3. Orden técnico vinculado al roadmap

| Fase del roadmap | Trabajo técnico principal | Puerta de aceptación |
|---|---|---|
| Fase 0 — 0.10.0 | Validación de flujos existentes, compatibilidad, recuperación, revisión de dependencias y versión de prerelease | Todas las tareas REL aplicables cerradas y matriz manual documentada |
| Fase 1 — Hallazgos | Definición de esquema/evidencia/retención, migración, estados, correlación determinista y filtros | Evidencia reproducible, no duplicados, manejo de falsos positivos y borrado correcto |
| Fase 2 — Fuentes reales | Selección de proveedor, contrato de adaptador, fixtures, timeouts y primera integración read-only | Pruebas automatizadas con fixtures y verificación manual contra proveedor compatible |
| Fase 3 — Operación | Informes, métricas limitadas, perfiles y accesibilidad | Exportaciones reproducibles, cardinalidad acotada y pruebas de aislamiento |
| Fase 4 — Remoto | Threat model, autenticación, TLS, autorización por agente/sitio, auditoría y recuperación | Suite de pruebas negativas de seguridad e inspección específica antes de habilitar |
| Fase 5 — Integraciones | Webhooks/formatos versionados, SIEM, auditoría de correo y navegadores opcionales | Contrato estable, permisos mínimos, idempotencia, retención y desconexión/borrado probados |

Este cuadro es una explicación de implementación; no sustituye el estado de las casillas del roadmap.

## 4. Estrategia de pruebas

1. **Unitarias:** parsers, normalización, reglas de confianza, rangos de IP, saneamiento, límites, fórmulas CSV y funciones puras.
2. **Integración:** API/SQLite, migraciones, permisos, sesiones, retención, exportación, transacciones y seguridad de origen.
3. **Frontend/extensión:** sintaxis JavaScript, pruebas Node, CSP, manifest/permisos mínimos, render seguro de texto remoto y comportamiento por defecto.
4. **Paquete:** instalación del wheel, metadatos, archivos estáticos, CLI y ejecución desde una carpeta limpia.
5. **CI:** matriz OS/Python, dependencias mínimas declaradas, CodeQL, auditoría de dependencias, detección de secretos y SBOM/manifiesto.
6. **Manual:** sistemas operativos, navegador, interacción de usuario, endpoints TLS autorizados, hardware y restauración, cuando el entorno real pueda cambiar el resultado.

Registrar la prueba manual con versión/commit, sistema operativo, versiones relevantes, pasos, resultado y referencia del error. Una casilla de roadmap no sustituye ese registro.

## 5. Política de versión y releases

La versión de desarrollo se representa como 0.10.0.dev0 y la release estable como 0.10.0. La fuente autorizada es src/netsentinel/__init__.py; el campo dinámico de pyproject.toml debe seguir leyéndola en vez de duplicar el número. No etiquetar ni anunciar una versión estable antes de superar la puerta de release de la Fase 0.

Consultar [GITHUB_SETUP.md](GITHUB_SETUP.md) para la secuencia de publicación, comprobación de wheel/SBOM, SHA-256 y procedencia. El changelog describe los cambios del ciclo y no constituye prueba de que se hayan validado manualmente.
