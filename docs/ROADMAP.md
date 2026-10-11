# Plan de versiones

Este documento separa el núcleo estable de los módulos que se incorporarán de forma incremental. Las funciones que generan tráfico deben ser explícitas, acotadas, documentadas y probadas sin depender de una red real.

## Versiones completadas

- [x] **0.1 — Base local:** aplicación instalable, panel web, inventario inicial, confianza manual, eventos y diagnóstico a demanda.
- [x] **0.2 — Inventario fiable:** fuentes de descubrimiento intercambiables, direcciones IPv4/IPv6, historial de cambios y base OUI opcional.
- [x] **0.3 — Monitorización:** controles Ping/TCP/HTTP(S), historial, incidentes deduplicados, recuperación y webhook opcional.
- [x] **0.4 — Diagnóstico guiado:** explicación de resultados y próximos pasos sin equiparar un ping fallido con una caída confirmada.
- [x] **0.5–0.6 — Descubrimiento local:** detección automática de subredes RFC 1918, límites de sondeo, exclusión de interfaces virtuales conocidas y auditoría de alcance/duración.
- [x] **0.7 — Distribución y protección:** lanzadores para Windows/macOS/Linux, protección Host/Origin, cabeceras defensivas y respaldo SQLite.
- [x] **0.8 — Informes y tendencias:** analítica de monitorización, latencia histórica, exportaciones CSV seguras y métricas de incidentes.
- [x] **0.9 — Exportación de incidentes:** filtros de incidentes y tendencias históricas exportables.

## 0.10 — Primer módulo de herramientas: DNS de solo lectura

- [x] Resolver nombres de host mediante el resolvedor configurado en el sistema operativo.
- [x] Validar la entrada como nombre de host; no aceptar URL, rutas, credenciales ni opciones de consulta arbitrarias.
- [x] Devolver direcciones IPv4/IPv6 deduplicadas y ordenadas.
- [x] Mantener la operación bajo demanda, sin escaneos ni cambios de configuración.
- [x] Incorporar una pantalla independiente `/tools` con formulario explícito y estados accesibles.
- [ ] Completar pruebas manuales en Windows/macOS/Linux antes de marcar el módulo como listo para usuarios finales.

## Próximos módulos — orden recomendado

### 0.11 — Diagnóstico DNS ampliado (en progreso)
- [x] Consultar resolución inversa PTR para una IP ingresada explícitamente.
- [x] Mostrar una lectura de configuración DNS local, de solo lectura, con fuente y límites explícitos.
- [x] Diferenciar nombre no encontrado, fallo temporal del resolvedor y error general en la API y los mensajes de consulta.
- [ ] Mantener límites de tiempo independientes para consultas DNS y pruebas deterministas.
- [x] Reducir consultas PTR repetidas con caché en memoria acotada, fecha de resolución y procedencia explícita.

### 0.12 — Inventario enriquecido
- [ ] Añadir nombres DNS inversos opcionales al inventario, con caché y sin bloquear la carga de la tabla.
- [ ] Mostrar procedencia y fecha de cada dato enriquecido; nunca presentar un nombre como identidad verificada.
- [ ] Permitir desactivar consultas automáticas.

### 0.13 — Integraciones de infraestructura
- [ ] Adaptadores opcionales de DHCP y routers, primero en modo lectura.
- [ ] Credenciales guardadas fuera del repositorio y nunca expuestas por la API o los registros.
- [ ] Compatibilidad por fabricante/modelo documentada y pruebas con respuestas simuladas.

### Más adelante
- [ ] Vista de topología basada solo en relaciones observadas y con incertidumbre explícita.
- [ ] Exportador Prometheus con métricas de bajo cardinalidad.
- [ ] Supervisión de varias redes/perfiles de ubicación.
- [ ] Proxy HTTP/S independiente solo después de definir límites de privacidad, autenticación y aislamiento.

## Criterios de aceptación de cada módulo

1. Separación clara entre lógica, API y presentación.
2. Pruebas automatizadas sin Internet, red real ni privilegios de administrador.
3. Validación de entradas, límites de tiempo y errores comprensibles.
4. Documentación del tráfico generado, permisos, privacidad y límites.
5. Activación explícita para funciones que consulten redes externas o modifiquen sistemas.
6. Actualización de README, changelog y versión solo cuando el módulo esté integrado y probado.
