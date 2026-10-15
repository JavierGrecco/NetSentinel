# Visibilidad de red sin instalar un agente en cada equipo

## Qué queremos lograr

Poder observar metadatos de actividad de dispositivos autorizados de una red, sin instalar un programa en cada notebook, teléfono o televisor. Es posible cuando la infraestructura de red ya reúne esa información y permite compartirla con un colector.

Eso no significa que el router pueda mostrar absolutamente todo lo que hace un dispositivo. El resultado depende del modelo, de las funciones habilitadas, del tipo de tráfico y de los protocolos de privacidad.

## Qué hace NetSentinel hoy

- **Inventario y descubrimiento:** identifica direcciones observables durante un descubrimiento local solicitado por la persona usuaria. Esto ayuda a conocer qué equipos aparecen, pero no demuestra qué aplicaciones usan ni qué páginas visitan.
- **Monitorización:** realiza comprobaciones puntuales o programadas contra objetivos configurados —ping, TCP o HTTP/HTTPS— mientras NetSentinel está abierto y el equipo está despierto. Mide disponibilidad del objetivo, no toda la actividad del dispositivo.
- **Actividad y telemetría:** puede recibir eventos compatibles durante una sesión temporal con token, y puede importar registros CSV normalizados. La extensión Chromium es una fuente distinta, instalada explícitamente en un navegador autorizado.
- **Integración de router:** las opciones de fuente DNS/flujo de la pantalla todavía no traen un adaptador de router listo para configurar. Abrir una ventana crea una ventana temporal de recepción y un token; por sí solo no activa los registros del router ni empieza a recopilar actividad.

## Opciones sin instalar un agente en cada dispositivo

### 1. Registros DNS del router o del punto de acceso

Si el router, firewall o controlador Wi-Fi registra las consultas DNS y permite exportarlas, un adaptador puede relacionar eventos como el dominio consultado y la hora con la IP del cliente. Para identificar el dispositivo con más confianza también hacen falta datos de DHCP, inventario o asignaciones conocidas.

**No revela una página completa ni lo que se hizo dentro de ella.** DNS cifrado (DoH/DoT), una VPN, la caché del dispositivo o consultas resueltas por otra vía pueden reducir lo que se observa. Los dominios tampoco prueban quién usó el dispositivo.

### 2. Registros de conexiones o flujos

Algunos routers, firewalls o equipos gestionables pueden exportar metadatos NetFlow/IPFIX/sFlow u otros registros de sesiones. Según la fuente, pueden incluir IP de origen y destino, puerto, protocolo, horarios y contadores.

Estos datos ayudan a responder con qué destinos se comunicó una dirección y cuándo. No revelan el contenido de HTTPS, mensajes, contraseñas ni la página exacta; no todos los equipos de red producen estos registros.

### 3. Firewall, proxy o controlador de red existente

Si ya existe una herramienta central que registra conexiones autorizadas, puede ser más seguro reutilizar su API o exportación antes de añadir otro sensor. Hay que confirmar autenticación, alcance, retención y permisos de lectura.

### 4. Captura centralizada en un puerto espejo o TAP

En una red administrada se puede copiar tráfico a un colector mediante una función de espejo de puerto (SPAN) o un TAP. Esto requiere configurar infraestructura de red y un colector; no equivale a instalar software en cada dispositivo. Una Mac conectada normalmente a una red conmutada no recibe automáticamente todo el tráfico unicast de los demás equipos. El cifrado sigue limitando la visibilidad del contenido.

## Qué no alcanza

- Ver una IP, una MAC o una respuesta ping no permite deducir qué está haciendo el usuario.
- Una tabla de DHCP/ARP ayuda a relacionar dispositivos e IP, pero no es un historial de actividad.
- Capturar metadatos de red no demuestra identidad humana, intención o causa raíz.
- No es correcto prometer visibilidad completa de navegación HTTPS, correo, mensajes o actividad de aplicaciones sin una fuente autorizada que exponga esos datos.
- El descubrimiento local actual no es un analizador persistente de todo el tráfico.

## Diseño recomendado para NetSentinel

1. **Primero, identificar capacidades de la infraestructura:** fabricante/modelo, disponibilidad de registros DNS o flujos, modo de exportación, permisos y si la red usa VPN o DNS cifrado.
2. **Implementar una primera integración sin agente:** priorizar una fuente central y de solo lectura —por ejemplo, syslog/API de registros DNS— con configuración explícita, prueba de conexión y mensajes claros cuando no se reciben eventos.
3. **Mantener un adaptador separado por familia de fuentes:** no asumir que todos los routers usan el mismo formato. Validar, normalizar y sanear los datos al entrar.
4. **Proteger el acceso:** credenciales fuera del repositorio y de SQLite sin protección, permisos mínimos, secretos redactados en logs, límites de tamaño, retención configurable y opción de desconectar/borrar los registros importados.
5. **Mostrar procedencia y cobertura:** cada evento debe decir qué fuente lo reportó, cuándo se observó y qué campos están disponibles. La interfaz debe señalar cuándo la fuente está desconectada o no cubre todo el tráfico.
6. **Probar con datos de ejemplo antes de conectar equipos reales:** pruebas de parsing, duplicados, timestamps, IP malformadas, privacidad, desconexión, expiración de credenciales y ausencia de datos.

## Decisión práctica

La alternativa más prometedora para observar varios dispositivos sin instalar software en cada uno es usar registros del router/firewall/controlador central, si el equipo los ofrece. El primer paso técnico es identificar el modelo y sus funciones documentadas; después se puede elegir e implementar el adaptador apropiado.

Hasta que ese adaptador exista y esté configurado, las opciones DNS/flujo de la pantalla son una selección del tipo de fuente esperado, no una integración funcional automática.