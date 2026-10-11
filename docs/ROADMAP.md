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

### 0.12 — Historial por dispositivo (primera etapa)
- [x] Consultar las observaciones históricas del inventario por dispositivo, con límite de resultados y origen/fecha/IP.
- [x] Acceder al historial desde la fila del dispositivo sin bloquear la carga del inventario.
- [ ] Incorporar eventos de conexiones/servicios mediante una fuente compatible (telemetría del router/AP o captura autorizada en una interfaz que realmente vea el tráfico).
- [ ] Distinguir DNS, destinos IP/puerto y SNI TLS cuando estén disponibles, documentando que no equivale a URLs completas ni al contenido HTTPS.
- [x] Añadir retención configurable y estado explícito de seguimiento; las pruebas de API con eventos normalizados están incorporadas.
- [ ] Añadir una prueba de integración con una fuente de tráfico real una vez elegido el adaptador.

### 0.11 — Diagnóstico DNS ampliado (en progreso)
- [x] Consultar resolución inversa PTR para una IP ingresada explícitamente.
- [x] Mostrar una lectura de configuración DNS local, de solo lectura, con fuente y límites explícitos.
- [x] Diferenciar nombre no encontrado, fallo temporal del resolvedor y error general en la API y los mensajes de consulta.
- [ ] Mantener límites de tiempo independientes para consultas DNS y pruebas deterministas.
- [x] Reducir consultas PTR repetidas con caché en memoria acotada, fecha de resolución y procedencia explícita.

### 0.12 — Inventario enriquecido
- [x] Exponer una consulta PTR por dispositivo bajo demanda, desde la tabla de inventario, usando su dirección observada más reciente y la caché existente; no altera el inventario ni bloquea su carga.
- [ ] Añadir nombres DNS inversos visibles en el inventario solo tras validar la experiencia de usuario y los límites de tiempo.
- [ ] Mostrar procedencia y fecha de cada dato enriquecido; nunca presentar un nombre como identidad verificada.
- [ ] Permitir desactivar consultas automáticas.

### 0.14 — Actividad familiar y metadatos (implementación inicial)
- [x] Vista local `/activity` para elegir un dispositivo y una fuente, con ventanas temporales de 5 minutos a 12 horas.
- [x] Aceptar eventos normalizados solo durante sesiones activas y exigir token aleatorio de ingestión cuyo hash es el único valor persistido.
- [x] Admitir metadatos de DNS, conexiones, SNI visible, aplicación reportada y eventos de bloqueo, sin URLs completas, credenciales ni payloads.
- [x] Importar CSV normalizado local (1 MB/1.000 filas máximo) y rechazar columnas desconocidas/sensibles.
- [x] Configurar retención de 1 a 90 días; incluir eventos y sesiones en exportación JSON v4 y copia SQLite, sin exponer hashes de tokens.
- [ ] Crear adaptador nativo para una fuente concreta de router/AP o resolvedor (depende de marca/modelo y formato disponible).
- [ ] Proporcionar un agente explícito para telemetría de aplicaciones/tiempo de uso por sistema operativo, sin capturar teclado, contraseñas ni contenido.
- [ ] Añadir pruebas manuales e integración de una fuente real tras completar CI.

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
