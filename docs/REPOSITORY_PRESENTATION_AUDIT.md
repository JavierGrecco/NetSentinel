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

### 5. La auditoría de ramas quedó desactualizada

La auditoría publicada registra 174 referencias incluyendo `main`. La consulta del 3/11 encontró 190 ramas remotas: `main` y 189 ramas adicionales. El inventario completo con SHA y prefijo se conserva en [BRANCH_SNAPSHOT_2026-11.csv](BRANCH_SNAPSHOT_2026-11.csv), y la interpretación en [BRANCH_AUDIT_2026-11.md](BRANCH_AUDIT_2026-11.md). Las cifras de la auditoría anterior deben tratarse como una fotografía histórica.

La consulta encontró diez PR abiertas: siete actualizaciones automatizadas de dependencias/acciones, la PR #200 de correlación Zeek, la PR #208 de presentación documental y la PR #209 de corrección del asistente. No se debe interpretar esa cantidad como diez funcionalidades de producto sin terminar.

En el HEAD revisado de `main`, `299360f088f1eb92c766d29e448133ce3608142a`, la matriz Python multiplataforma, CodeQL, auditoría de dependencias y generación de SBOM/manifiesto aparecen correctas. Sin embargo, el estado agregado de checks figura pendiente: el escaneo histórico de Gitleaks falla por dos coincidencias del nombre de una clave de almacenamiento local de preferencias de la topología en `scripts/check_responsive_ui.py` (commits `f2f34a4` y `190bee2`), no por una credencial real visible en el código revisado. Además, hay ejecuciones programadas de Dependabot fallidas por errores del servicio/API (`missing response` y respuesta no JSON al consultar versiones bloqueadas). Para Gitleaks añadí `.gitleaksignore` con **26 huellas exactas** (commit, archivo, regla y línea): dos proceden de pruebas, dos de una primera versión de este informe que reprodujo accidentalmente el identificador, once corresponden a SHA de Git del snapshot inicial y once a los SHA del CSV detectados al consolidar esta PR en un solo commit. Los logs confirman que las coincidencias son claves locales de `localStorage` y hashes de commits, no credenciales. Cada excepción identifica un único commit, archivo, regla y línea; no excluye archivos, reglas ni commits completos. En la ejecución de seguimiento sobre el commit `40a6e04d78d481f77aee1064e25d74ffd9c983d4`, el job `Detect committed secrets` pasó sin hallazgos. La CI completa del HEAD definitivo debe terminar antes de marcar la PR como lista para revisión. Los fallos de Dependabot corresponden a ejecuciones del servicio de actualización, no a los tests de la aplicación; siguen siendo un problema de automatización que conviene vigilar, pero no deben mezclarse con los resultados de CI del código. Evidencia consultada el 3/11/2026; puede cambiar.

**Decisión:** actualizar el inventario de ramas y PR antes de cualquier eliminación. No borrar ramas durante esta reorganización documental.

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
