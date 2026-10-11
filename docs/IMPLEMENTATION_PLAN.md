# Plan de implementación

La aplicación se entrega en hitos pequeños y acumulativos. Cada hito debe poder instalarse, probarse y entenderse sin tener que habilitar todas las funciones avanzadas.

## 0.1 — Base funcional

Panel local, FastAPI, SQLite, lectura pasiva inicial, lista de confianza, notas, eventos, diagnósticos explícitos y exportación.

## 0.2 — Inventario más fiable (implementado)

- Fuentes de descubrimiento intercambiables, con fallos aislados.
- Combinación y deduplicación de fuentes disponibles en cada sistema.
- Seguimiento de varias direcciones IPv4/IPv6 por una MAC.
- Eventos de cambios de IPv4 con mensaje prudente.
- Fabricantes a partir de `oui.csv` local opcional.
- Registro de origen/fecha de lectura, historial accesible por API e interfaz.
- Migración SQLite desde v0.1 y pruebas con fixtures de sistemas operativos.

Criterios: `pytest` funciona sin red real; la API muestra la versión adecuada; los datos de v0.1 permanecen disponibles; la falla de una fuente no aborta el resto.

## 0.3 — Diagnóstico e incidentes

- Configuración validada de objetivos de comprobación.
- Estado diferenciado entre fallo y prueba no disponible.
- Deduplicación y silenciamiento de incidentes.
- Evidencias por incidente y exportación de informe.

## 0.4 — Integraciones

- Adaptadores de lectura para DHCP, SNMP, AdGuard Home y Pi-hole.
- Contratos de capacidades, estado de conexión y permisos.
- Manejo de secretos fuera del código y los registros.
- Cualquier acción que modifique un router debe requerir confirmación, auditoría y reversión.

## 0.5+ — Observabilidad avanzada

Mapa topológico conservador, métricas, nodos remotos autenticados y proxy HTTP opcional separado del servicio principal.

## Verificación de cada entrega

1. Pruebas unitarias y de API sin depender de una red real.
2. Comprobación de instalación/compilación del paquete.
3. Actualización del README, changelog y documentación técnica.
4. Validación en GitHub Actions para Windows, macOS y Linux; no declarar que pasó hasta consultar ejecuciones remotas.
