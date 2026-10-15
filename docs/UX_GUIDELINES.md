# Guía de consistencia visual y experiencia de uso

Esta guía mantiene una misma lógica de presentación en todas las secciones de NetSentinel. No busca que todas las pantallas tengan el mismo contenido: busca que se sientan parte de la misma aplicación.

## Marco común

- **Ancho máximo:** 1320 px para Inventario, Hallazgos, Monitorización, Herramientas y Actividad.
- **Márgenes laterales:** 24 px en escritorio, 16 px en pantallas medianas y 12 px en móviles.
- **Tipografía:** familia del sistema compartida, texto general de 14 px y títulos principales de 26 a 32 px.
- **Paneles:** radio de 16 px, relleno de 20 px en escritorio y 14–16 px en móvil.
- **Controles:** objetivo visual de 40 px de alto, con etiquetas legibles y foco visible al usar teclado.
- **Separación:** 16 px entre bloques relacionados y una separación estable entre encabezado y contenido.
- **Navegación:** los mismos enlaces principales, el mismo aspecto para la sección activa y la misma preferencia de tema.

Los valores centrales viven en `static/theme.css`. Cada página carga esa hoja después de su CSS específico para que el marco compartido tenga la última palabra.

## Responsabilidades de las hojas de estilo

`styles.css`, `findings.css`, `monitors.css`, `activity.css` y `tools.css` pueden definir las necesidades particulares de cada módulo: tablas, gráficos, formularios y tarjetas específicas. No deben volver a definir el ancho global de la página, el tamaño general del título, los márgenes del encabezado o una escala de controles distinta.

Cuando un componente necesite un ajuste propio, debe ser una excepción pequeña y justificada, no una segunda base de diseño.

## Comportamiento adaptable

- Las columnas se apilan cuando no hay espacio suficiente.
- Las tablas y los historiales largos se desplazan dentro de su contenedor, sin ensanchar la página completa.
- La navegación y los controles se acomodan en varias líneas en pantallas estrechas.
- Se reserva el espacio de la barra de desplazamiento para reducir movimientos laterales al cambiar de sección.
- Las animaciones se reducen cuando el sistema indica preferencia por movimiento reducido.

## Criterio de aceptación

Antes de dar por terminada una mejora visual, recorrer las cinco secciones en un navegador real y comprobar:

1. El marco y la alineación general no saltan de tamaño al navegar.
2. Los títulos, paneles, botones, campos y separaciones siguen una escala común.
3. La sección activa se identifica con claridad y los controles se pueden usar con teclado.
4. La pantalla sigue siendo cómoda en una ventana estrecha y no aparece desplazamiento horizontal en toda la página.
5. Los temas Oscuro, Medio y Claro conservan contraste legible.
6. Cualquier diferencia intencional queda explicada; las pruebas automatizadas no sustituyen esta revisión visual.

Seguimiento y resultados reales: [PROJECT_STATUS.md](PROJECT_STATUS.md) y [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md).
