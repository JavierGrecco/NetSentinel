# Plan de implementación — estado auditable

## Estado de esta rama

La rama de trabajo incorpora el núcleo de NetSentinel, herramientas DNS, historial de observaciones por dispositivo y una primera capa de actividad familiar. El código de la rama **no está validado hasta que CI termine correctamente**; tampoco se deben describir como operativas fuentes que aún no se conectaron.

### Implementado en código
- Inventario local y direcciones observadas, diagnóstico guiado, monitores e incidentes.
- DNS A/AAAA y PTR bajo demanda; lectura de configuración DNS local; caché PTR acotada.
- Sesiones de actividad opt-in y limitadas por dispositivo, API de ingestión con token aleatorio de un solo uso (solo se persiste su hash), CSV, retención y exportación.
- Eventos `page_visit` y `search_query` en la base de datos, con validación y sanitización de URL.
- Extensión Chromium en `browser-extension/`: registra navegación futura y consultas en motores reconocidos; guarda hasta 1.000 eventos localmente, con configuración visible, pausa, exclusiones, retención y exportación CSV.
- Importación manual en `/activity`, con asociación del CSV a un dispositivo inventariado.

### Límites actuales — no afirmar más que esto
- La extensión registra navegación solo en el navegador/dispositivo donde se instala y solo después de activar el seguimiento. No recupera historial anterior, no lee contenido de páginas ni formularios y no registra contraseñas.
- Las búsquedas se detectan solo en formatos de URL conocidos de motores compatibles. No abarca aplicaciones nativas ni consultas internas que no aparezcan en la URL.
- Los datos se transfieren a NetSentinel por exportación/importación CSV manual. No hay sincronización en vivo entre computadoras.
- El backend tiene modelos para DNS/flows/app events, pero no existe aún un adaptador nativo de router/AP ni un agente de uso de aplicaciones. Crear una sesión no activa automáticamente una captura.
- Las URLs se limpian de fragmentos y parámetros conocidos de credenciales/sesión/seguimiento. Ningún filtro genérico puede garantizar detectar todo dato personal que una web incluya en la ruta o en parámetros desconocidos.

## Próximos pasos por prioridad

### P0 — validar esta implementación
1. CI debe pasar tests, chequeo de sintaxis JS y empaquetado.
2. Verificar migración de SQLite conservando eventos de la iteración previa.
3. Probar en Chrome/Edge navegación normal, cambio de URL SPA, búsquedas compatibles, dominios excluidos, pausa y límite de retención.
4. Probar exportación CSV de la extensión, importación en NetSentinel, renderizado y retención local.
5. Ejecutar inicio/instalación en Windows, macOS y Linux; corregir todo fallo antes de publicar.

### P1 — experiencia operativa
1. Añadir previsualización/validación antes de importar y deduplicación idempotente para evitar dobles importaciones.
2. Permitir filtrar/exportar/descartar eventos por dispositivo y período.
3. Añadir más motores de búsqueda con pruebas explícitas, sin leer contenido de páginas ni formularios.
4. Revisar la sanitización URL con casos de OAuth, tokens, tracking, IPv6 y codificación percent.

### P2 — fuentes reales del hogar
1. Elegir el modelo exacto de router/AP/resolvedor y conseguir un ejemplo de sus logs o API.
2. Implementar un adaptador de solo lectura, parser probado con fixtures, límites de frecuencia y atribución explícita de fuente.
3. Diseñar sincronización en vivo entre dispositivos con autenticación, autorización por dispositivo, rotación/revocación de tokens y transporte seguro; no abrir directamente la API sin autenticación.
4. Añadir agente opcional de estadísticas de aplicaciones/tiempo de pantalla por OS, sin keylogging ni captura de contenido.

### P3 — otras mejoras conservadas en el plan
- DNS: timeout independiente; completar validación multiplataforma.
- Inventario: DNS inverso visible opcional con procedencia/fecha y opción de desactivación.
- Infraestructura: adaptadores DHCP/router/SNMP y secretos protegidos.
- Observabilidad: topología, Prometheus y perfiles de varias redes.
- Cualquier proxy de diagnóstico requerirá un diseño independiente y revisión de seguridad antes de entrar a la implementación.

## Criterios de cierre

Ninguna etapa se da por terminada solo por agregarse al roadmap. Para marcarla validada se requiere código revisado, pruebas automáticas verdes, empaquetado verificado, pruebas manuales donde corresponda y documentación actualizada. Las tareas no implementadas deben seguir en la sección de pendientes.
