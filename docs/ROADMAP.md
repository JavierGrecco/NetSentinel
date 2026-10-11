# Roadmap y criterios de aceptación

## Hito 0.1 — Base inicial (completado)

- [x] Aplicación Python instalable con servidor local en loopback.
- [x] Lectura pasiva de tablas de vecinos.
- [x] Inventario SQLite, confianza manual, eventos y exportación.
- [x] Panel web y diagnóstico explícito.

## Hito 0.2 — Inventario más fiable (completado en código; requiere validar CI remota)

- [x] Contrato `DiscoveryProvider` para fuentes intercambiables y aisladas.
- [x] Combinación de proveedores con tolerancia a fallos individuales.
- [x] Parser para IPv4/IPv6, salidas `ip neigh`, `arp` y `ndp` comunes.
- [x] Seguimiento de varias direcciones por MAC y de primera/última observación.
- [x] Evento de cambio de IPv4 principal con lenguaje no concluyente.
- [x] Base OUI local opcional con MA-L/MA-M/MA-S, procedencia y fecha de consulta.
- [x] Indicador de MAC localmente administrada sin declarar automáticamente que sea intrusa.
- [x] Vista de historial de lecturas y direcciones, API de historial y exportación JSON v2.
- [x] Migración aditiva de base SQLite de v0.1.
- [x] Pruebas reproducibles, incluidas salidas IPv6 y migración.

Criterio: la falla de una fuente no aborta el inventario; cada dirección queda asociada a una fuente y fecha; una ausencia de la caché no se interpreta como desconexión.

## Hito 0.3 — Diagnóstico e incidentes

- [ ] Objetivos locales y externos configurables, con límites de tiempo y validaciones.
- [ ] Métricas de latencia y pérdida con estado correcto/fallido/no comprobado.
- [ ] Incidentes con evidencias, deduplicación, silenciamiento y mantenimiento.
- [ ] Exportación de informes de incidente en HTML/PDF.

## Hito 0.4 — Integraciones

- [ ] Adaptadores de solo lectura para DHCP/SNMP y AdGuard Home/Pi-hole.
- [ ] Capacidad de integración declarada, configuración validada y pruebas contractuales.
- [ ] Secretos fuera de logs y exportaciones por defecto.
- [ ] Escritura administrativa a routers solo después de revisión de seguridad, confirmación y mecanismo de reversión.

## Hito 0.5+ — Funciones avanzadas

- [ ] Mapa topológico con relaciones verificadas y grado de confianza.
- [ ] Nmap opcional, solo para redes autorizadas y con alcance visible.
- [ ] Exportador de métricas y nodos remotos autenticados.
- [ ] Proxy opcional aislado del inventario.

## Regla de ingeniería

Cada nuevo módulo debe incluir pruebas, límites de alcance, procedencia de los datos y documentación. No se deben convertir indicios en afirmaciones automáticas de intrusión.
