# Roadmap operativo de NetSentinel

Este documento distingue **código presente en la rama** de **validación completada** y de **trabajo todavía no implementado**. Una casilla marcada significa que la función está codificada, no que CI o pruebas manuales estén aprobadas.

## Estado real de la rama de trabajo

### Núcleo de inventario/diagnóstico
- [x] Inventario local con IPv4/IPv6, direcciones históricas, etiquetas de confianza, fabricante OUI local opcional y eventos.
- [x] Descubrimiento local opt-in acotado a subredes privadas RFC 1918, una búsqueda a la vez, con datos de alcance/duración.
- [x] Monitorización Ping/TCP/HTTP(S), incidentes, recuperación, tendencias, exportaciones y webhook opcional.
- [x] Lectura DNS A/AAAA, PTR bajo demanda, caché PTR acotada y diagnóstico de configuración DNS local en Windows/macOS/Linux.
- [ ] Pruebas manuales de instalación y flujo completo de DNS/paquete en Windows, macOS y Linux.
- [ ] Límites de tiempo DNS independientes del resolvedor del sistema y pruebas deterministas de timeout.
- [ ] Enriquecimiento DNS persistido/visible en inventario con procedencia, fecha y desactivación de consultas automáticas.

### Actividad e historial familiar — implementación inicial
- [x] Historial de observaciones por dispositivo (fecha/IP/fuente); no equivale a páginas visitadas.
- [x] Modelo SQLite y API para sesiones temporales, ingestión de metadatos autenticada por token temporal, CSV, retención y exportación JSON v4.
- [x] Migración de la tabla de eventos de la iteración temprana a eventos de visita/búsqueda sin eliminar eventos existentes.
- [x] Sanitización de URL: HTTP(S) únicamente, sin credenciales embebidas ni fragmentos, filtrado de parámetros conocidos de autenticación/sesión, búsqueda y seguimiento.
- [x] Extensión Chromium visible y opt-in, apagada en la primera instalación, para páginas y búsquedas de navegadores compatibles; exporta CSV local para importación manual.
- [x] La interfaz de actividad muestra páginas y términos de búsqueda junto con fuente, dispositivo y hora.
- [ ] CI debe quedar verde; ejecutar pruebas manuales de backend y de la extensión en Chrome/Edge antes de considerar validada la función.
- [ ] Verificar límites de sanitización con URLs de autenticación reales y ampliar la lista de motores según necesidad.
- [ ] Sincronización central en vivo entre dispositivos con autenticación, permisos por dispositivo, transporte seguro, revocación de credenciales y protección contra reenvíos. No exponer la API actual a la LAN como sustituto.
- [ ] Extensión Firefox u otros navegadores que soporten una API equivalente.
- [ ] Agente opcional por sistema operativo para uso de aplicaciones/tiempo de pantalla, sin keylogging ni lectura de formularios.
- [ ] Fuente real de DNS/flows del router/AP/resolvedor; requiere seleccionar modelo/fuente y probar con sus registros exportados o API.

## Pendientes de infraestructura y evolución

### Adaptadores de red
- [ ] Adaptadores DHCP/router/SNMP, en modo lectura inicialmente, con compatibilidad por marca/modelo, timeouts, límites, auditoría y pruebas con fixtures.
- [ ] Gestión segura de credenciales de adaptadores, fuera del repositorio, sin exponerlas por la API ni en logs.
- [ ] Integración de flujos de destino IP/puerto y DNS del router; distinguir evento observado de usuario/identidad.
- [ ] Guía de despliegue seguro para una instalación doméstica central; el panel debe seguir en loopback por defecto.

### Observabilidad
- [ ] Topología basada en relaciones observadas, con incertidumbre explícita.
- [ ] Métricas Prometheus de cardinalidad acotada.
- [ ] Perfiles para varias redes/ubicaciones sin mezclar observaciones por error.
- [ ] Mejoras de reportes y exportación selectiva por dispositivo/período.

### Inspección HTTP/TLS
- [ ] No implementar interceptación general de TLS, recuperación de credenciales, captura de formularios ni cargas útiles.
- [ ] Cualquier proxy de diagnóstico explícito debe diseñarse aparte, con autenticación, aislamiento, consentimiento visible, exclusiones y revisión de seguridad antes de aprobarlo; no es un componente comprometido para la versión actual.

## Orden recomendado de implementación

1. Hacer pasar CI del estado actual y arreglar fallos; no publicar como validado mientras haya jobs pendientes o fallidos.
2. Probar manualmente la extensión en Chrome/Edge: visita normal, navegación SPA, Google/Bing/YouTube, exclusiones, pausa, límite y exportación CSV; importar en NetSentinel en Windows/macOS.
3. Mejorar el flujo de importación (previsualización, deduplicación, asociación y eliminación selectiva) sin convertir importación manual en falsa sincronización.
4. Elegir una fuente doméstica concreta para DNS/flows. Implementar primero parser/read-only con ejemplos de logs y fixtures, luego adaptador.
5. Diseñar sincronización local segura solo después de añadir autenticación real, autorización por dispositivo, transporte y una configuración explícita; loopback sigue siendo predeterminado.
6. Evaluar un agente de tiempo de pantalla por sistema operativo y mantener independientes los datos de uso de aplicaciones y los metadatos.

## Criterios para marcar una tarea como completada

1. Código integrado a la rama y estado documentado con precisión.
2. Pruebas automatizadas reproducibles sin Internet, red real ni privilegios de administrador.
3. CI verde en matriz Linux/Windows/macOS y prueba de empaquetado satisfactoria.
4. Pruebas manuales multiplataforma para flujos que dependan de navegador, OS o router real.
5. Documentación de fuentes, permisos, datos guardados, límites y cómo desactivar/borrar registros.
6. Actualizar changelog/versión estable solo después de revisión; no confundir funciones planificadas con código presente.
