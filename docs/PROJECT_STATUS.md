# Estado actual del proyecto

**Actualizado:** 22 de octubre de 2026  
**Rama canónica:** `main`  
**Integración funcional:** [`f2f34a43`](https://github.com/JavierGrecco/NetSentinel/commit/f2f34a43fbbd88501782dda13baac6342b6ddcf4)  
**Estado:** integración consolidada; aceptación local aún pendiente.

## Fuente única de trabajo

La [PR #189](https://github.com/JavierGrecco/NetSentinel/pull/189) se integró mediante squash en `main`. Reúne en una sola versión el explorador LAN histórico, la importación controlada de Zeek, el mapa mundial con GeoIP local opcional, NetSentinel Forense y el asistente guiado de 12 pasos con datos sintéticos.

Los cambios de esas funciones ya no deben buscarse en PR de integración separadas. Para preparar la siguiente prueba, usá [el laboratorio de aceptación](EXPERT_ACCEPTANCE_LAB.md) y [los escenarios sintéticos](MANUAL_TEST_SCENARIOS.md), ambos actualizados para trabajar desde `origin/main`.

## Estado de validación

Sobre la cabeza integrada previa al merge (`a28dedb5c31345754f78b512fd6abcbbd0ca3ecb`) se registró:

- **CI:** 18/18 tareas correctas, incluida la suite Chromium responsive.
- **Interfaz:** 135/135 comprobaciones automatizadas responsive correctas.
- **Seguridad:** CodeQL y auditoría de dependencias correctos.
- **Cadena de suministro:** detección de secretos, construcción del paquete, SBOM y manifiesto de integridad correctos. La firma de procedencia se omite en la ejecución de una PR.

Ejecuciones previas al merge: [CI](https://github.com/JavierGrecco/NetSentinel/actions/runs/39875121099), [Security Analysis](https://github.com/JavierGrecco/NetSentinel/actions/runs/39875121139) y [Supply Chain Security](https://github.com/JavierGrecco/NetSentinel/actions/runs/39875121092).

**Esto no valida todavía la sesión real en tu Mac.** Antes de probar, verificá que los workflows estén completos y correctos para el commit exacto de `main` que descargaste: cada commit nuevo necesita sus propios checks.

## Corrección del control de secretos posterior al merge

El primer workflow de cadena de suministro en `main` detectó como posible secreto el nombre de una preferencia de `localStorage` usado por la prueba responsive; no era una credencial. Se cambió el identificador en el script para evitar que esa preferencia parezca un secreto. La corrección solo se considera validada cuando los workflows del commit actual finalicen correctamente.

## Puertas pendientes antes de considerar estable la versión 0.10.0

1. Ejecutar el recorrido guiado completo, usando solamente la base de datos y los archivos sintéticos de la guía. Registrar los 12 resultados, notas y SHA probado.
2. Confirmar la experiencia real con teclado y lector de pantalla, legibilidad, navegación entre módulos y tamaños de escritorio/móvil.
3. Revisar los informes, los errores recuperables y que fallos o pasos no comprobados nunca aparezcan como aprobados.
4. Registrar resultados y evidencias en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md), y abrir incidencias reproducibles para cualquier problema.
5. Verificar por separado la protección de `main` y los checks requeridos; el seguimiento administrativo continúa en [issue #73](https://github.com/JavierGrecco/NetSentinel/issues/73).

La base GeoLite2-City no se descarga junto con las dependencias Python y requiere una instalación local autorizada. NetSentinel Forense sigue siendo experimental: un hash detecta cambios, pero no autentica por sí solo al operador ni crea una firma digital o un anclaje externo independiente.

## Higiene de PR y ramas

Las PR de integración #157, #171, #177, #183, #184 y #188 se cerraron como supersedidas por #189. Sus comentarios y commits siguen disponibles para auditoría. **Cerrar esas PR no borra sus ramas.**

La enumeración de GitHub devolvió 174 ramas remotas. No se borraron referencias de rama en esta pasada, porque hacerlo sin comparar cada árbol contra `main` podría ocultar trabajo único. La limpieza física de ramas queda pendiente de una auditoría explícita de diferencias y de conservar cualquier cambio que no esté integrado. El alcance futuro se conserva en [FORENSIC_MODE_PROPOSAL.md](FORENSIC_MODE_PROPOSAL.md) como propuesta documental. No implica que los recolectores, categorías de artefactos o integraciones allí descritos estén implementados ni preparados para evidencia real.

## Documentación vigente

- [Laboratorio de aceptación](EXPERT_ACCEPTANCE_LAB.md)
- [Escenarios sintéticos](MANUAL_TEST_SCENARIOS.md)
- [Matriz de validación](VALIDATION_MATRIX.md)
- [Roadmap](ROADMAP.md)
- [Arquitectura](ARCHITECTURE.md)
- [Preparación manual en macOS](MACOS_MANUAL_TEST.md)
- [Matriz de preparación forense](FORENSIC_READINESS_MATRIX.md)
- [Propuesta estratégica de análisis forense — alcance futuro](FORENSIC_MODE_PROPOSAL.md)
- [Mapa mundial de IP](WORLD_IP_MAP.md)
- [Importación Zeek](ZEEK_CONNLOG_IMPORT.md)
- [Explorador de topología LAN](NETWORK_OBSERVABILITY_CONSOLE.md)

El seguimiento previo, con sus decisiones y evidencias históricas, se conserva en [PROJECT_STATUS_HISTORY_2026-10.md](PROJECT_STATUS_HISTORY_2026-10.md).
