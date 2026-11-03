# Auditoría de presentación y mantenimiento del repositorio

**Fecha de revisión:** 3 de noviembre de 2026  
**Rama de trabajo:** `docs/portfolio-presentation-2026-11`  
**Base revisada:** `main` en `299360f088f1eb92c766d29e448133ce3608142a`

## Objetivo

Mejorar la lectura del repositorio para usuarios, reclutadores y responsables técnicos sin alterar el comportamiento de la aplicación, ocultar trabajo en curso ni duplicar el código en otro repositorio.

## Hallazgos

### 1. El README mezcla presentación, manual de usuario y laboratorio

El README explica con bastante detalle instalación, uso, límites y pruebas. Esa información es útil, pero el índice también expone desde el inicio el módulo Forense, sus documentos de prueba, escenarios sintéticos, mapa mundial y laboratorio de aceptación.

**Decisión:** conservar las instrucciones necesarias para ejecutar el producto, pero ordenar la lectura desde el propósito principal hacia las capacidades, la arquitectura, la validación y, finalmente, los módulos experimentales y la investigación.

### 2. La investigación tiene demasiado protagonismo para la página principal

Hay documentos separados para las dos referencias llamadas NetSentinel, una matriz de adopción, un plan de reingeniería y una comparación amplia.

**Decisión:** conservar los documentos y añadir un índice editorial único. Las referencias se presentan como investigación y decisiones propias, no como una lista de proyectos que el producto intenta imitar.

### 3. Forense necesita una jerarquía inequívoca

La documentación actual lo identifica como experimental y describe límites importantes. El README, sin embargo, lo introduce en el segundo párrafo, antes de explicar el flujo principal de inventario y monitorización.

**Decisión:** mantener sus advertencias y documentación, pero trasladar su presentación a una sección secundaria de módulos complementarios/experimentales. No ocultar el módulo ni llamarlo terminado.

### 4. Los documentos de estado no reflejan el HEAD actual

En la revisión, `main` apunta a `299360f088f1eb92c766d29e448133ce3608142a`, mientras que `PROJECT_STATUS.md` y `ROADMAP.md` todavía describen una fotografía del 23 de octubre y un SHA anterior.

**Decisión:** actualizar el estado solo cuando se consulten las evidencias del SHA actual. No reciclar cifras históricas de CI como si fueran actuales.

### 5. La auditoría de ramas y PR necesita distinguir el snapshot del estado vigente

La primera consulta del 3/11 registró 190 ramas remotas: `main` y 189 adicionales. Ese inventario se conserva en [BRANCH_SNAPSHOT_2026-11.csv](BRANCH_SNAPSHOT_2026-11.csv) como fotografía histórica, no como inventario vivo. Después de la consolidación de actualizaciones de mantenimiento, la consulta posterior devuelve 188 ramas: `main` y 187 adicionales. Tres referencias de Dependabot que figuraban en el snapshot ya no aparecen; no se emitieron órdenes de borrado como parte de esta reorganización.

La consulta actual encuentra cuatro PR abiertas: #200 (correlación Zeek, Draft), #208 (presentación documental), #209 (corrección de Actividad → Importar) y #210 (consolidación de dependencias). Las siete actualizaciones originales #201–#207 están agrupadas en #210 y no deben contarse como siete PR abiertas ni como funcionalidades pendientes.

En el HEAD revisado de `main`, `299360f088f1eb92c766d29e448133ce3608142a`, la matriz Python multiplataforma, CodeQL y auditoría de dependencias de aplicación aparecen correctas. El historial agregado no debe describirse como totalmente verde: la ejecución de Supply Chain Security asociada al HEAD terminó con fallo el 2/11; las últimas ejecuciones programadas de Dependabot del 26/10 también fallaron por errores de respuesta del servicio/API. La CI del HEAD de `main` terminó correctamente el 23/10. Estos resultados corresponden a `main`, no a los heads de PR.

La última revisión totalmente validada de la PR #208 es el HEAD `63b689f90ccfe15a145fc352926583f2ebe7dc06`: 23 checks exitosos y 1 omisión esperada de firma de procedencia, sin fallos. En una combinación Python 3.14/Ubuntu se ejecutaron 855 pruebas en 12,38 s; Chromium completó 135/135 comprobaciones sobre nueve vistas y quince tamaños de ventana. CI [run 41641279934](https://github.com/JavierGrecco/NetSentinel/actions/runs/41641279934), seguridad [run 41641279778](https://github.com/JavierGrecco/NetSentinel/actions/runs/41641279778) y cadena de suministro [run 41641279787](https://github.com/JavierGrecco/NetSentinel/actions/runs/41641279787) terminaron correctamente. La rama añade 26 huellas Gitleaks exactas (commit, archivo, regla y línea); no excluye archivos, reglas ni commits completos. Las excepciones limitan falsos positivos confirmados de nombres de claves locales de preferencias y SHA de Git. Los commits documentales siguientes vuelven a ejecutar los workflows; los resultados deben consultarse por SHA y no se heredan automáticamente.

**Decisión:** mantener separados el inventario histórico, el estado vivo de GitHub y los resultados de cada SHA. No borrar ramas durante esta reorganización documental.

### 6. Protección de la rama principal sin confirmar

La API de ramas informa `protected: false` para `main`. Esto no demuestra por sí solo el estado completo de todos los rulesets, pero sí impide afirmar que la protección clásica está habilitada.

**Decisión:** mantener la gobernanza como pendiente hasta comprobar el alcance del ruleset, los checks requeridos y una prueba efectiva sobre una PR.

### 7. El README también funcionaba como manual extenso

El README inicial tenía más de 18 KB y mezclaba la presentación del producto con instrucciones detalladas para cada módulo y una guía de aceptación.

**Decisión aplicada:** el README se redujo a una entrada de producto de aproximadamente 4,3 KB. El contenido operativo se conserva en `docs/USER_GUIDE.md` (aproximadamente 14,3 KB), con los enlaces relativos adaptados. No se eliminó ninguna instrucción de instalación, uso, privacidad o pruebas.

### 8. La arquitectura necesitaba una lectura de una página

`ARCHITECTURE.md` contiene el inventario técnico detallado de routers, servicios y repositorios. Para una primera evaluación faltaba una explicación visual de cómo se conectan los límites principales.

**Decisión aplicada:** se añadió [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) con un diagrama Mermaid de la instalación local, API, servicios, dominios, repositorios, SQLite y fuentes opcionales. El detalle técnico existente se conserva y el README enlaza primero a la vista general.

## Decisiones de esta rama

- Añadir una guía de presentación para el portfolio.
- Añadir un índice único para investigación y referencias.
- Mantener el detalle de investigación y los avisos de terceros.
- No modificar código de ejecución ni tests.
- No eliminar ramas ni PR.
- No crear una copia del producto.
- Preparar una revisión posterior del README y del estado del proyecto con evidencia actualizada.

## Trabajo que todavía requiere comprobación

- Ejecutar aceptación manual sobre el HEAD que vaya a publicarse.
- Resolver la experiencia de la guía que tuvo problemas durante la prueba local.
- Revisar accesibilidad y uso con teclado/lector de pantalla.
- Confirmar la protección efectiva de `main`.
- Auditar nuevamente los SHA de las ramas antes de cualquier poda.
- Definir la versión y las capturas reales que se usarán en el caso de estudio.

## Criterio de salida

Esta reorganización documental puede integrarse cuando los enlaces estén correctos, la lectura del README sea coherente y los cambios no introduzcan afirmaciones no verificadas. No declara terminado el producto ni sustituye la aceptación funcional.


**Verificación de enlaces:** se comprobaron 109 enlaces relativos internos en los 12 documentos Markdown modificados por la PR; no se encontraron rutas rotas. Esta cifra corresponde a la validación de la rama en el momento de la consulta y debe repetirse si se agregan o renombran documentos.