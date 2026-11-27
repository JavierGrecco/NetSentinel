# ADR-002: mantener FastAPI/Python y JavaScript nativo

- **Estado:** aceptada
- **Fecha:** 27 de noviembre de 2026
- **Sustituye:** no sustituye ADR-001; la complementa

## Contexto

NetSentinel se distribuye hoy como una aplicación local de una sola instalación. FastAPI sirve la API y las páginas estáticas; Python contiene el descubrimiento de red, los diagnósticos, las reglas de negocio y el acceso a SQLite; JavaScript implementa la interfaz del navegador y la extensión Chromium Manifest V3.

El backend y la extensión tienen responsabilidades distintas. La extensión es un cliente opcional, no otro servidor. La instalación no necesita PHP ni un proceso Node en tiempo de ejecución. El panel se mantiene vinculado a loopback porque todavía no ofrece autenticación y autorización para acceso remoto.

Laravel es un framework de aplicación backend escrito en PHP. No es una capa que fortalezca JavaScript ni reemplaza los controles de seguridad del navegador. Agregarlo implicaría mantener un segundo backend, runtime, gestión de dependencias, contratos y modelo de despliegue sin resolver una necesidad actual del producto.

## Decisión

1. **Mantener Python + FastAPI como único backend de la aplicación.** Python conserva las tareas de red, el acceso al sistema operativo, la lógica de dominio, la validación autoritativa y la persistencia SQLite.
2. **Mantener JavaScript nativo para la interfaz y la extensión.** No introducir React, Vue, Angular, Laravel, Express ni un framework frontend/backend adicional por razones puramente estéticas o de moda.
3. **Usar Node solo como herramienta de desarrollo y prueba.** Node 24 comprueba sintaxis de los scripts propios y ejecuta pruebas de la extensión; no forma parte del runtime de NetSentinel ni añade dependencias de producción.
4. **Mantener un monolito modular.** Separar responsabilidades mediante routers, servicios, repositorios y módulos JavaScript cohesivos. No dividir en microservicios mientras el producto siga siendo una instalación local.
5. **Mantener la validación del backend como autoridad.** Los filtros del navegador reducen la recopilación innecesaria y mejoran la experiencia, pero el backend vuelve a validar los datos antes de aceptarlos o persistirlos.

## Seguridad que acompaña la decisión

La elección de framework no sustituye controles de seguridad. La arquitectura actual se refuerza mediante:

- Escucha local en `127.0.0.1`; el CLI oficial rechaza la exposición en otras interfaces.
- Validación de `Host`, `Origin` y Fetch Metadata para mitigar DNS rebinding y CSRF en los flujos cubiertos.
- CSP con scripts locales y sin `unsafe-inline`, respuestas `no-store` y cabeceras defensivas.
- Datos locales en SQLite, permisos restrictivos donde el sistema operativo los permite y copias consistentes.
- Extensión con permisos mínimos `storage` y `webNavigation`, sin permisos generales de acceso a sitios.
- CodeQL para Python, JavaScript/TypeScript y GitHub Actions; auditoría de dependencias, detección de secretos, SBOM y validaciones CI en varias plataformas.
- Pruebas JavaScript en Node y pruebas de navegador con Chromium, además de la suite Python.

Estas medidas reducen riesgos concretos, pero no constituyen autenticación ni convierten la aplicación en segura para acceso remoto. No se debe cambiar el host de escucha para habilitar LAN/Internet con esta arquitectura de despliegue.

## Cuándo revisar esta decisión

Reabrir la decisión cuando exista una necesidad demostrable de alguno de estos escenarios:

- varios usuarios concurrentes con identidades y permisos diferenciados;
- despliegue remoto, multi-sede o colectores que se conecten a un servidor central;
- una API pública o integraciones de terceros que requieran credenciales y límites por usuario;
- operación distribuida que supere la capacidad del despliegue local y SQLite.

En ese momento se debe realizar un threat model y una ADR nueva que cubra, como mínimo, autenticación, autorización por recurso/sitio, sesiones, protección CSRF, TLS, gestión y rotación de secretos, rate limiting, auditoría, migración de datos, despliegue y recuperación. Se compararán alternativas por requisitos operativos y experiencia disponible. Laravel podría evaluarse si PHP encaja en ese contexto, pero no será la elección automática ni se usará para “proteger JavaScript”.

## Consecuencias

- Menos runtimes, frameworks, dependencias y superficie de mantenimiento en el producto.
- Una sola autoridad para reglas de negocio y persistencia.
- La interfaz sigue siendo ligera y compatible con la extensión Chromium.
- Las futuras necesidades multiusuario/remotas se tratarán como un cambio de arquitectura y seguridad, no como una simple instalación de un framework.
