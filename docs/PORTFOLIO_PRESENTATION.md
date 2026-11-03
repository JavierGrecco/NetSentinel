# Presentación profesional de NetSentinel

**Propósito:** definir cómo presentar el producto a reclutadores, responsables técnicos y evaluadores sin exagerar capacidades ni ocultar trabajo en curso.

## Posicionamiento

NetSentinel es una aplicación local-first para inventario, observabilidad y diagnóstico de redes autorizadas. Ayuda a descubrir dispositivos, registrar cambios, comprobar servicios y revisar evidencia de actividad importada explícitamente.

La propuesta central es la visibilidad operativa local, explicable y con límites claros. No debe presentarse como un SIEM, NDR, EDR, escáner integral de vulnerabilidades ni plataforma SOC.

## Qué debe entender un visitante en el primer minuto

1. **Qué es:** una herramienta local para conocer una red y comprobar servicios.
2. **Qué problema resuelve:** reúne inventario, historial y comprobaciones en una interfaz sencilla sin exigir una plataforma central.
3. **Cómo funciona:** descubrimiento bajo demanda, persistencia local y resultados con procedencia.
4. **Qué demuestra:** diseño de software, arquitectura modular, API, persistencia, pruebas automatizadas, seguridad y atención a la experiencia de usuario.
5. **Cuál es su estado:** desarrollo activo; no declarar una versión estable hasta completar la aceptación manual y la gobernanza de integración.

## Capacidades que pueden presentarse como parte del producto

La documentación y el código de `main` describen estas áreas:

- Inventario de dispositivos y observaciones históricas.
- Descubrimiento local bajo demanda y acotado.
- Topología LAN histórica basada en observaciones persistidas.
- Monitorización configurada de ping, TCP y HTTP/HTTPS.
- Diagnósticos DNS y comprobaciones TLS puntuales.
- Hallazgos derivados de inventario y monitorización, con evidencia y límites.
- Importación manual de metadatos CSV y registros Zeek autorizados.
- Mapa de IP públicas observadas, condicionado a una base GeoIP local válida.

La existencia de una ruta, pantalla o prueba automatizada no demuestra por sí sola que el flujo esté aceptado por una persona. Para el estado de validación prevalece `docs/PROJECT_STATUS.md` y la evidencia registrada en `docs/VALIDATION_MATRIX.md`.

## Capacidades que requieren una etiqueta especial

### NetSentinel Forense

Debe presentarse como módulo experimental. Registra casos, metadatos, operaciones y manifiestos con hashes, pero no proporciona por sí solo una cadena de custodia legalmente validada, autenticación independiente del operador ni garantías frente a quien pueda reescribir la base de datos.

No debe ocupar el primer plano de la presentación general mientras siga pendiente su aceptación específica.

### Mapa mundial y GeoIP

La vista puede existir aunque no haya datos geográficos disponibles. Las ubicaciones dependen de una base GeoLite2-City válida instalada localmente y son aproximadas. No presentar el mapa como geolocalización exacta ni atribuir ubicaciones a direcciones privadas.

### Zeek y actividad importada

NetSentinel permite importar registros explícitamente. No afirmar que captura tráfico en vivo, ejecuta Zeek, inspecciona paquetes automáticamente ni ve toda la actividad de la red.

## Estructura recomendada para la página principal

1. Nombre y descripción de una frase.
2. Captura real y reciente de la aplicación.
3. Problema que resuelve y flujo de uso de principio a fin.
4. Capacidades principales, con límites breves.
5. Arquitectura y decisiones técnicas.
6. Instalación y ejecución.
7. Pruebas reproducibles y evidencia por commit.
8. Estado actual y limitaciones.
9. Documentación técnica, investigación y créditos.

El README no debe ser un índice de cada documento interno ni una cronología de todas las ideas exploradas. Debe orientar al usuario y ofrecer profundidad mediante enlaces.

## Caso de estudio para un portfolio separado

El repositorio de portfolio debe enlazar a este repositorio como fuente única del código. No debe copiar el código, mantener una rama paralela del producto ni publicar una segunda distribución.

El caso de estudio debería incluir:

- Objetivo y usuarios previstos.
- Capturas auténticas de una versión identificada.
- Diagrama de arquitectura generado a partir de la estructura vigente.
- Dos o tres decisiones técnicas difíciles y sus alternativas.
- Un problema real, su diagnóstico y la solución comprobada.
- Evidencia automatizada asociada a un SHA concreto.
- Validación manual efectivamente realizada.
- Limitaciones conocidas y próximos pasos acotados.

No publicar números de tests, porcentajes, versiones o estados sin indicar el commit y el alcance de la comprobación. No utilizar mockups como si fueran capturas del producto.

## Criterios para afirmar que está terminado

No declarar una versión estable ni usar expresiones como «production-ready» hasta que:

- La aceptación manual de los flujos principales esté registrada sobre un SHA concreto.
- La instalación y el inicio estén comprobados en los sistemas operativos anunciados.
- Los flujos de respaldo y recuperación estén verificados.
- La revisión de accesibilidad y uso básico esté documentada.
- Los controles de integración de `main` estén configurados y probados.
- Los límites de las funciones experimentales sean visibles para el usuario.

## Mensaje recomendado

> NetSentinel es una herramienta local para inventariar dispositivos, observar cambios y comprobar servicios de red. Está diseñada para trabajar con acciones explícitas, datos locales y resultados cuya procedencia y limitaciones puedan entenderse.

Este mensaje describe el propósito sin atribuir capacidades de captura, detección o respuesta que el producto no ofrece.
