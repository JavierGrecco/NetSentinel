# Roadmap operativo de NetSentinel

Separamos código presente, validación pendiente y trabajo que todavía no está implementado. Una casilla marcada indica que existe código, no que CI o pruebas manuales estén aprobadas.

## Núcleo de inventario y diagnóstico
- [x] Inventario local, observaciones, historial de direcciones, etiquetas de confianza y eventos.
- [x] Descubrimiento local explícito y acotado a subredes privadas.
- [x] Monitores Ping/TCP/HTTP(S), incidentes, recuperación, tendencias, exportaciones y webhooks opcionales.
- [x] Consultas DNS A/AAAA, PTR bajo demanda, caché PTR acotada y diagnóstico de configuración DNS local.
- [ ] Pruebas manuales de instalación/flujos completos en Windows, macOS y Linux.
- [ ] Timeout DNS independiente del resolvedor del sistema y pruebas deterministas.
- [ ] Enriquecimiento DNS persistido/visible con procedencia, fecha y opción de desactivación.

## Actividad familiar: estado de código
- [x] Historial de presencia por dispositivo (fecha/IP/fuente), claramente distinto de páginas visitadas.
- [x] API/SQLite de sesiones acotadas, token temporal hasheado, CSV, retención y exportación JSON v4.
- [x] Extensión Chromium visible, opt-in y apagada por defecto para registrar páginas futuras y búsquedas por URL en el dispositivo local.
- [x] Importación manual de CSV de navegación y búsquedas; validación y saneamiento de URLs.
- [x] Importación manual de metadatos de correo autorizados: fecha, proveedor, emisor, destinatarios y asunto opcional.
- [x] Rechazo de columnas de cuerpo de mensaje, contenido o adjuntos; no hay extracción de bandejas.
- [x] Normalización inicial de alias CSV de Google Workspace (Date/Sender/Recipient/Subject or Message ID) y Microsoft 365 (receivedDateTime/senderAddress/recipientAddress/subject).
- [x] CI automatizada verde en la matriz de Python 3.10–3.14 en Windows/macOS/Linux y validación del paquete para la integración anterior.
- [x] Pruebas Node automatizadas del ciclo de extensión: apagada por defecto, opt-in, subframes/privado, exclusiones, opciones de captura, retención/límite y deduplicación.
- [x] Pruebas CSV del popup para comillas, comas, saltos de línea, fórmulas y BOM UTF-8; comprobación automática del manifest MV3 y permisos mínimos.
- [ ] Pruebas manuales de importación/extensión en Chrome/Edge y Windows/macOS/Linux; los cambios de deduplicación también deben pasar CI.
- [x] Refuerzo de saneamiento URL y pruebas automáticas: OAuth/redirect, nombres doblemente codificados, tracking, IPv6, términos de búsqueda y segmentos de ruta reconocibles (correo, teléfono, UUID, token opaco).
- [ ] Validación manual con URLs reales y revisión de falsos positivos; no es posible reconocer de forma fiable cualquier identificador arbitrario de ruta.
- [x] Previsualización CSV sin escritura: valida el archivo completo, informa duplicados y muestra hasta 10 filas normalizadas antes de confirmar.
- [x] Deduplicación idempotente de filas CSV manuales por dispositivo; las filas idénticas ya importadas se omiten y se contabilizan.
- [x] Filtros de eventos por dispositivo, tipo y rango de fechas UTC; exportación CSV filtrada con neutralización de fórmulas, hasta 10.000 filas.
- [x] Borrado selectivo de eventos por dispositivo, tipo o fechas: previsualización sin escritura y confirmación exacta `BORRAR N` comprobada de forma transaccional; no puede ejecutarse sin al menos un filtro.
- [x] Filtros de actividad, exportación y borrado selectivo también por fuente (`router_dns`, `router_flow`, `device_agent`, `manual_import`); valores admitidos validados por servidor.
- [ ] Pruebas manuales de UX para flujos de borrado.
- [ ] Sincronización en vivo desde equipos supervisados, tras añadir autenticación, autorización por dispositivo, cifrado de transporte, revocación y protección contra reenvío. No exponer la API actual a la LAN como atajo.
- [ ] Extensión Firefox u otros navegadores compatibles.
- [ ] Adaptador de auditoría para un proveedor concreto de correo, tras verificar qué registros admite el tipo de cuenta y con permisos válidos.
- [ ] Agente opcional de tiempo de pantalla/uso de apps por SO, sin keylogging ni lectura de formularios.
- [ ] Adaptador real de DNS/flows de router/AP/resolvedor doméstico, después de elegir modelo y formato.

## Adaptadores de infraestructura
- [ ] Adaptadores DHCP/router/SNMP de solo lectura, con límites de tiempo, compatibilidad documentada, auditoría y fixtures.
- [ ] Gestión de credenciales de adaptadores fuera del repositorio y de logs.
- [ ] Integración de DNS/destinos IP/puerto del router sin inferir identidad personal.
- [ ] Guía de despliegue local segura; loopback como valor predeterminado.

## Observabilidad y usabilidad
- [ ] Topología basada en relaciones observadas y nivel de incertidumbre.
- [ ] Métricas Prometheus de cardinalidad acotada.
- [ ] Perfiles de varias redes/ubicaciones aislados entre sí.
- [ ] Exportación selectiva por dispositivo/período/fuente.

## TLS y contenido privado
- [ ] No implementar recuperación/interceptación de contraseñas, captura de formularios, keylogging, lectura de mensajes o cuerpos HTTP.
- [ ] No realizar descifrado/proxy TLS general. Cualquier futura herramienta de diagnóstico TLS requiere diseño independiente, consentimiento visible, aislamiento y revisión de seguridad.

## Orden de trabajo recomendado
1. Cerrar el fallo actual de CI y ejecutar toda la matriz; no declarar validada ninguna función antes de esa comprobación.
2. Probar manualmente la extensión: navegación normal, SPA, Google/Bing/YouTube, exclusiones, pausa, retención, exportación e importación.
3. Mejorar el importador con previsualización, validación, deduplicación y borrado/exportación selectiva.
4. Elegir proveedor de correo y fuente concreta; primero solo auditoría de metadatos autorizada, nunca contenido.
5. Elegir router/AP/resolvedor y desarrollar adaptador read-only con fixtures.
6. Diseñar sincronización segura entre equipos; no exponer la API de ingestión en LAN sin autenticación.
7. Añadir agente de uso de aplicaciones/tiempo de pantalla por SO.

## Criterios para cerrar tareas
1. Código integrado y revisado.
2. Tests reproducibles sin red real ni privilegios administrativos.
3. CI verde en Linux/Windows/macOS y empaquetado comprobado.
4. Pruebas manuales para flujos dependientes de navegador, SO o router.
5. Documentación de permisos, datos, retención, límites y eliminación.
6. Changelog/versión estable solo después de validación; el roadmap no sustituye al código.
