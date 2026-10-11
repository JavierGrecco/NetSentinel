# Plan de versiones

Este documento resume qué está implementado y qué falta.

## 0.1 — Base local
- [x] Aplicación instalable y panel web.
- [x] Inventario inicial, confianza manual, eventos, exportación y diagnóstico a demanda.

## 0.2 — Inventario más fiable
- [x] Proveedores de descubrimiento intercambiables y tolerancia a fallos.
- [x] Direcciones IPv4/IPv6 por dispositivo con historial.
- [x] Detección de cambios de IP y base OUI local opcional.
- [x] Pruebas multiplataforma.

## 0.3 — Monitorización
- [x] Controles de ping, TCP y HTTP/HTTPS configurables.
- [x] Historial de comprobaciones y latencia.
- [x] Incidentes deduplicados y recuperación automática.
- [x] Webhook HTTPS opcional.
- [x] Página independiente de monitorización.
- [x] CSS separado del HTML y documentación más clara.

## 0.4 — Diagnóstico e integraciones
- [ ] Asistente guiado para distinguir problemas de puerta de enlace, DNS e Internet.
- [ ] Adaptadores opcionales para DNS, DHCP y routers compatibles.
- [ ] Mejor visualización de tendencias e informes exportables.

## Más adelante
- [ ] Mapa de topología respaldado por datos.
- [ ] Métricas para Prometheus y supervisión de varias redes.
- [ ] Proxy HTTP/S independiente, después de definir límites de privacidad claros.

Las integraciones y acciones que modifiquen la red seguirán siendo explícitas, opcionales y documentadas.
