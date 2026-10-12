# Roadmap operativo de NetSentinel

Separamos código presente, validación pendiente y trabajo que todavía no está implementado. Una casilla marcada indica que existe código, no que CI o pruebas manuales estén aprobadas.

## Núcleo de inventario y diagnóstico
- [x] Inventario local, observaciones, historial de direcciones, etiquetas de confianza y eventos.
- [x] Descubrimiento local explícito y acotado a subredes privadas.
- [x] Monitores Ping/TCP/HTTP(S), incidentes, recuperación, tendencias, exportaciones y webhooks opcionales.
- [x] Consultas DNS A/AAAA, PTR bajo demanda, caché PTR acotada y diagnóstico de configuración DNS local.
- [ ] Pruebas manuales de instalación/flujos completos en Windows, macOS y Linux.
- [x] Timeout DNS independiente del resolvedor del sistema, con proceso hijo terminable y pruebas deterministas de éxito, error y timeout.
- [x] Herramienta TLS puntual en Herramientas: valida certificado, fechas, nombre, versión TLS y cifrado negociado; no solicita contenido HTTP ni persiste el resultado.
- [x] CLI fail-closed para enlace remoto: solo loopback, validación de puerto y pruebas para bloquear exposición accidental sin autenticación.
- [x] Política CSP/Permissions-Policy para respuestas del servidor, con excepción acotada de Swagger UI y pruebas de cabeceras de seguridad en rutas válidas y rechazos.
- [x] `script-src` hash-only por pantalla para las cinco interfaces principales; CI verifica el hash exacto de cada bloque y rechaza manejadores JavaScript inline.
- [x] Eliminar `style-src unsafe-inline`: externaliza estilos de página, sustituye atributos inline por clases y valida los CSS incluidos en el wheel y servidos localmente.
- [x] Retirar `script-src unsafe-inline` de `/api/docs`: el inicializador generado por Swagger se autoriza mediante hash SHA-256 calculado por respuesta; el CDN conserva alcance exclusivo a la documentación.
- [x] Primera iteración del motor de hallazgos: API de solo lectura y exportación JSON para cambios del inventario e incidentes de monitorización, con procedencia, evidencia, estado, severidad y confianza separadas; evita duplicar transiciones de monitorización.
- [x] Bandeja visual `/findings` conectada al motor de hallazgos, con filtros por estado, evidencia/procedencia, reconocimiento de eventos del inventario y exportación JSON; respuestas locales sin caché.
- [ ] Ampliar el motor para incluir resultados DNS/TLS persistibles solo después de definir retención, eliminación, consentimiento cuando corresponda y control de falsos positivos.
- [ ] Pruebas manuales de TLS con endpoints autorizados (certificado válido, próximo a vencer, no confiable, timeout y puerto no TLS) en Windows, macOS y Linux.
- [ ] Enriquecimiento DNS persistido/visible con procedencia, fecha y opción de desactivación.

## Actividad y telemetría autorizada: estado de código
- [x] Historial de presencia por dispositivo (fecha/IP/fuente), claramente distinto de páginas visitadas.
- [x] API/SQLite de sesiones acotadas, token temporal hasheado, CSV, retención y exportación JSON v4.
- [x] Extensión Chromium visible, opt-in y apagada por defecto para registrar páginas futuras y búsquedas por URL en el dispositivo local.
- [x] Importación manual de CSV de navegación y búsquedas; validación y saneamiento de URLs.
- [x] Importación manual de metadatos de correo autorizados: fecha, proveedor, emisor, destinatarios y asunto opcional.
- [x] Rechazo de columnas de cuerpo de mensaje, contenido o adjuntos; no hay extracción de bandejas.
- [x] Normalización inicial de alias CSV de Google Workspace (Date/Sender/Recipient/Subject or Message ID) y Microsoft 365 (receivedDateTime/senderAddress/recipientAddress/subject).
- [x] CI automatizada verde en la matriz de Python 3.10–3.14 en Windows/macOS/Linux y validación del paquete para la integración anterior.
- [x] Pruebas Node automatizadas del ciclo de extensión: apagada por defecto, opt-in, subframes/privado, exclusiones, opciones de captura, retención/límite y deduplicación.
- [x] Pruebas CSV del popup para comillas, comas, saltos de línea, fórmulas y BOM UTF-8; el manifest MV3 solicita solo permisos necesarios y CI comprueba los permisos mínimos.
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
- [x] Inspección explícita de un único handshake TLS con validación normal del certificado; metadatos temporales y hallazgos orientativos, sin petición HTTP.
- [ ] Valorar alertas persistentes de vencimiento únicamente después de diseñar retención, destino de avisos y tratamiento de resultados.
- [ ] No implementar recuperación/interceptación de contraseñas, captura de formularios, keylogging, lectura de mensajes o cuerpos HTTP.
- [ ] No realizar descifrado/proxy TLS general. Cualquier futura herramienta de diagnóstico TLS requiere diseño independiente, consentimiento visible, aislamiento y revisión de seguridad.

## Orden de trabajo recomendado

1. **Validación real y confianza en los resultados.** Ejecutar flujos manuales en Windows, macOS y Linux: inventario, DNS, monitorización, informes, extensión Chromium/Edge, importación/exportación y borrado selectivo. Probar TLS con certificados válidos, próximos a vencer, no confiables, puertos sin TLS y timeouts. La CI verde no sustituye estas comprobaciones.
2. **Motor de hallazgos de seguridad.** La primera capa ya unifica por API eventos persistidos del inventario e incidentes de monitorización. El siguiente paso es ofrecer una bandeja visual y, solo después de definir retención y eliminación, integrar resultados DNS/TLS persistibles. Mantener severidad, evidencia, procedencia y confianza separadas; no marcar como comprometido un equipo solo por ser desconocido.
3. **Adaptador de infraestructura de solo lectura.** Elegir un router/AP/resolvedor concreto según hardware y APIs disponibles; incorporar DHCP, DNS o flujos realmente soportados con límites de tiempo, fixtures, origen de datos y pruebas sin equipo real. No prometer visibilidad completa sin una fuente que la provea.
4. **Sincronización remota segura.** Antes de exponer NetSentinel a una LAN o desplegarlo en varias sedes, implementar autenticación, autorización por equipo/rol, alta explícita, credenciales revocables, transporte cifrado, protección contra repetición, límites de tasa y registro de auditoría.
5. **Informes e integración SOC.** Añadir informes de hallazgos con evidencia y recomendaciones; después métricas Prometheus e integración SIEM. Una matriz de cobertura frente a NIST CSF 2.0/CISA CPG debe mostrar evidencia y brechas, nunca una certificación automática.
6. **Ampliación de fuentes.** Incorporar enriquecimiento DNS opcional con fecha/procedencia, adaptador de auditoría de correo para un proveedor elegido y exportaciones selectivas. Priorizar Firefox y agente voluntario de uso de aplicaciones después de validar las funciones actuales y la política de datos.
7. **Cierre de calidad.** Cada módulo requiere tests deterministas, CI multiplataforma, pruebas manuales cuando dependa de SO/navegador/router, documentación de permisos/retención y un mecanismo de desactivación y eliminación.

## Criterios para cerrar tareas
1. Código integrado y revisado.
2. Tests reproducibles sin red real ni privilegios administrativos.
3. CI verde en Linux/Windows/macOS y empaquetado comprobado.
4. Pruebas manuales para flujos dependientes de navegador, SO o router.
5. Documentación de permisos, datos, retención, límites y eliminación.
6. Changelog/versión estable solo después de validación; el roadmap no sustituye al código.
