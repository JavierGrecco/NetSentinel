# Plan de implementación — estado auditable

## Implementado en la rama
- Inventario local, observaciones, monitores e incidentes.
- DNS A/AAAA, PTR bajo demanda y configuración DNS local.
- Historial por dispositivo, sesiones de actividad temporales y tokens de ingestión cuya versión en claro se muestra una sola vez.
- Importación CSV de metadatos de red, páginas, búsquedas compatibles y metadatos de correo de auditoría autorizada.
- Extensión Chromium visible y apagada al instalarse; registra navegación futura y búsquedas por URL compatibles, y exporta CSV.
- Sanitización URL en cliente y servidor; rechazo de columnas de cuerpo de correo, contenido y adjuntos.
- Importaciones CSV manuales idempotentes: compara eventos normalizados del mismo dispositivo, omite duplicados exactos y muestra el recuento omitido.
- Vista previa CSV de solo lectura: valida todas las filas, estima altas/duplicados y presenta hasta 10 filas de metadatos normalizados antes de guardar.
- Filtros de actividad por dispositivo, fuente, tipo de evento y fechas UTC inclusivas; exportación CSV filtrada hasta 10.000 filas con neutralización de fórmulas de hoja de cálculo.
- Saneamiento URL reforzado en extensión y backend: OAuth/redirect, claves doblemente codificadas, más claves de seguimiento, IPv6 canónico y redacción heurística de rutas reconocibles; pruebas Python y Node.
- Pruebas Node del ciclo del service worker para apagado por defecto, opt-in, navegación de subframe/privada, exclusiones, toggles de página/búsqueda, retención y deduplicación.
- Borrado selectivo de eventos por dispositivo, fuente, tipo o fechas con previsualización de alcance, prohibición de alcance vacío, confirmación exacta basada en el recuento actual y borrado transaccional; no elimina sesiones ni registros de inventario.
- Retención configurable de 1 a 90 días y exportación de metadatos sin hash de token.

## Límites actuales
- La extensión funciona solo en el navegador donde se instala y solo después de activarla; no recupera historia previa ni ve formularios, contenido, contraseñas o búsquedas internas de apps nativas.
- La transferencia desde la extensión a la base central es manual mediante CSV.
- El backend no captura tráfico por sí solo. No hay todavía adaptador para un router/AP ni agente de uso de aplicaciones.
- El soporte de correo es importación manual de metadatos; no se conecta a proveedores, no lee bandejas y no guarda cuerpo ni adjuntos.
- No puede garantizarse que un saneador URL detecte cualquier dato personal incrustado en rutas/parámetros desconocidos.
- La CI y pruebas manuales siguen pendientes hasta que la matriz esté verde.

## P0 — Validación y estabilización
1. Corregir fallos de CI y ejecutar tests, chequeo JS y empaquetado en la matriz.
2. Validar migración SQLite conservando eventos existentes al ampliar esquema.
3. Probar extensión Chrome/Edge: páginas normales, navegación SPA, motores, exclusiones, pausa, retención y exportación CSV.
4. Importar el CSV a NetSentinel y comprobar eventos, fechas, términos y saneamiento.
5. Probar metadatos de correo con CSV sintético autorizado; no incluir mensajes completos ni adjuntos.
6. Probar instalación y flujo en Windows, macOS y Linux.

## P1 — Experiencia de importación
1. Validación manual del saneamiento URL con casos reales y evaluación de falsos positivos en rutas largas.
2. Validar los alias CSV de Google Workspace y Microsoft 365 con exportaciones reales; elegir después un proveedor y confirmar permisos/cobertura antes de implementar un conector API.
3. Pruebas manuales del flujo de borrado y revisión de usabilidad multi-SO/navegador.

## P2 — Fuentes domésticas reales
1. Elegir el modelo de router/AP/resolvedor y conseguir log de ejemplo o API documentada.
2. Implementar parser read-only, fixtures, timeouts, atribución de fuente y límites.
3. Diseñar sincronización en vivo con autenticación, autorización, rotación/revocación de tokens y transporte seguro.
4. Añadir agente opcional de uso de aplicaciones/tiempo de pantalla por SO, sin keylogging ni captura de contenido.

## P3 — Resto del plan conservado
- DNS: timeout propio, pruebas multiplataforma y enriquecimiento opcional del inventario.
- Infraestructura: adaptadores DHCP/router/SNMP y gestión segura de secretos.
- Observabilidad: topología, métricas Prometheus y perfiles multired.
- Extensión Firefox y otros navegadores compatibles.
- Cualquier diagnóstico TLS futuro requiere diseño independiente; no debe capturar credenciales ni contenido privado.

## Criterio de finalización
Una tarea no se da por terminada solo por escribir el código o marcarla en el roadmap. Requiere tests verdes, empaquetado comprobado, pruebas manuales aplicables, documentación precisa y un mecanismo para desactivar/eliminar los datos.
