# Prueba manual del explorador de red

**Estado:** pendiente de aceptación manual sobre la integración de `main` antes de dar por cerrada la primera etapa.  
**Ruta:** `/network`  
**Rama canónica:** `main`

Estas pruebas verifican la experiencia del explorador, no demuestran que NetSentinel vea todo el tráfico de la red. No hace falta ejecutar pruebas contra redes ajenas ni instalar agentes.

## 1. Preparar la versión

Prepará una copia de trabajo independiente de la rama actual, siguiendo estas instrucciones desde la raíz de tu checkout actual:

```bash
git fetch origin "refs/heads/main:refs/remotes/origin/main"
git worktree add --detach ../NetSentinel-acceptance-lab refs/remotes/origin/main
cd ../NetSentinel-acceptance-lab
git rev-parse HEAD
git status --short
```

Si `../NetSentinel-acceptance-lab` ya existe por la guía de aceptación experta, no crees otra; usá esa copia y confirmá que el commit sea el que vas a probar.

En una terminal, iniciá NetSentinel con el lanzador normal de tu sistema. Abrí `http://127.0.0.1:8765/network` en el navegador.

## 2. Recorrido principal

Antes de una lectura, el explorador debe explicar que todavía no hay datos o mostrar la información previamente guardada. No debe inventar equipos ni líneas para decorar el mapa.

Ejecutá un descubrimiento solo en una red propia o autorizada. Después, recargá el explorador y comprobá:

- Se ven los equipos de la lectura y las subredes registradas. La cantidad coincide con los datos de inventario, sin duplicar el mismo dispositivo por tener más de una dirección.
- Buscá un nombre, una IP, una MAC y un fabricante, uno por vez. Los filtros deben reducir el grafo y poder limpiarse sin perder la página.
- En **Lectura del mapa**, seleccioná una captura anterior. Los selectores empiezan por las 100 lecturas más recientes. Usá **Cargar capturas anteriores** para avanzar por el historial y verificá que no haya duplicados ni saltos entre páginas. La lista de actividad del Inventario debe seguir mostrando solo 12 entradas para mantener la página clara. Comprobá que cambien la fecha, las direcciones y las relaciones según las observaciones históricas de esa captura; luego regresá a la más reciente.
- Abrí una lectura sin rangos de subred válidos. Si contiene observaciones, deben verse equipos sin líneas; los contadores de subredes y relaciones deben indicar que el alcance es desconocido, no cero confirmado.
- La respuesta de `GET /api/scans/{scan_id}/topology` debe contener `evidence_available`, `network_scope_available`, `nodes`, `edges`, `stats` y `warnings`. Cada línea debe ser de tipo `observed-subnet-membership` e incluir la IP y las fuentes disponibles.
- Seleccioná un equipo desde el dibujo y desde la alternativa textual. Ambos caminos deben abrir el mismo detalle.
- Verificá IP, MAC, fabricante si se conoce, estado, fecha y fuente de observación.
- Mirá el historial del equipo y los cambios registrados. Un evento debe mostrar fecha y contexto, sin presentarse como una captura completa de conexiones.
- En **Comparar lecturas**, elegí dos capturas distintas y comparalas. Revisá fechas, subredes compartidas, resumen y dispositivos con diferencias; si una captura informa errores o límites de alcance, el resultado debe advertirlo. En cada diferencia, confirmá que se muestre la IP, la hora y la fuente asociadas a la captura anterior y posterior. Usá **Ver equipo en el mapa** y comprobá que se abra la captura elegida, que los filtros se limpien y que quede seleccionado el equipo de esa diferencia. Si esa lectura no permite ubicarlo con evidencia suficiente, el mensaje debe aclarar la limitación sin afirmar que está desconectado.
- Elegí dos capturas sin subredes compartidas. La interfaz debe explicar que no son comparables y no atribuir las ausencias a equipos.
- Probá **Acercar**, **Alejar**, **Ajustar** y **Reordenar**. Después de elegir una posición, el mapa no debe saltar innecesariamente con cada actualización.
- Cambiá entre tema oscuro, medio y claro. Los nodos, el texto y los estados deben continuar distinguiéndose.

## 3. Confirmar que no se exagera la evidencia

Elegí un dispositivo que no esté en la lectura más reciente. La interfaz debe decir que no se observó en esa lectura, no afirmar que está apagado o desconectado.

Revisá la explicación de las líneas. Una línea entre dispositivo y subred solo agrupa una IP observada con un rango registrado. No confirma cableado, puerto de switch, tráfico entre dispositivos ni acciones de una aplicación.

Si no hay registros asociados al dispositivo, el panel de cambios debe explicar que no hay eventos recientes. No debe completar los espacios con actividad simulada.

## 4. Teclado y tamaños de ventana

Navegá con `Tab` y `Shift+Tab`. Debe ser posible usar los filtros, los controles del mapa y la lista textual sin depender de arrastrar nodos. Al seleccionar un equipo de la lista con `Enter` o `Espacio`, el foco debe permanecer en ese equipo y su estado seleccionado debe anunciarse mediante `aria-pressed`. Los controles deben tener foco visible y nombres comprensibles para lectores de pantalla.

Repetí el recorrido con una ventana angosta y una amplia. Confirmá que no haya desplazamiento horizontal en toda la página, controles recortados ni texto ilegible. Repetí el cambio de tema y la selección de un equipo en ambos tamaños.

## 5. Pruebas automáticas

Desde el entorno virtual del proyecto:

```bash
python -m pip install -e ".[test,ui-test]"
python -m playwright install chromium
python -m pytest
python scripts/check_responsive_ui.py
node --test tests/topology_model.test.cjs
```

En Windows, usá el intérprete del entorno virtual, por ejemplo `.venv\Scripts\python.exe`, para los comandos Python. Si alguna prueba falla, guardá el mensaje completo y anotá el tamaño de ventana y los pasos que lo provocaron.

## 6. Registro del resultado

Anotá fecha, sistema operativo, navegador, tema visual y tamaño de ventana. Para cada fallo, registrá los pasos, lo que esperabas ver y lo que ocurrió. No incluyas direcciones IP públicas, MAC reales ni datos sensibles en capturas o reportes compartidos.

- [ ] Mapa y detalle verificados.
- [ ] Historial y cambios registrados verificados.
- [ ] Búsqueda y filtros verificados.
- [ ] Zoom, ajustar y reorganizar verificados.
- [ ] Tres temas visuales verificados.
- [ ] Teclado y alternativa textual verificados.
- [ ] Ventana angosta y amplia verificadas.
- [ ] Resultado de las pruebas automáticas anotado.

**No cerrar la etapa ni presentar el proyecto como producto maduro hasta registrar esta prueba manual.** La actividad real por dispositivo sigue siendo una etapa aparte y requiere una fuente autorizada que entregue esos eventos.


### Alcance de lectura desconocido

- Si una lectura no tiene observaciones y su informe de subredes está ausente o dañado, el mapa debe mostrar un mensaje de alcance desconocido.
- No debe clasificar todos los dispositivos del inventario como “no vistos” cuando no se puede confirmar qué subredes se revisaron.
- Si sí hay observaciones, deben verse los dispositivos con la advertencia correspondiente y sin líneas inventadas.


### Lectura válida sin dispositivos

- Elegí una lectura que tenga subred registrada y ninguna observación de dispositivo.
- El mapa debe conservar el nodo de subred. No debe reemplazarlo por el mensaje de “sin coincidencias” ni dibujar conexiones.
- El detalle de una subred con exploración limitada debe decir que las ausencias no son concluyentes y no asumir siempre que el límite fue /24.
- Si no se puede interpretar el alcance de una lectura sin observaciones, la vista debe avisar que el alcance es desconocido; no debe declarar ausente a todo el inventario.


### Posiciones guardadas del mapa

- Arrastrá un dispositivo a una ubicación fácil de recordar y soltalo.
- Recargá la página y comprobá que la disposición se conserve para los mismos nodos.
- En Chromium, el verificador también debe poder recuperarse si la preferencia local está corrupta; al guardar de nuevo, cada coordenada tiene que ser finita y estar dentro del rango validado, con un máximo de 1200 entradas.
- Las posiciones son preferencias visuales locales; no deben modificar las lecturas guardadas ni las relaciones de red.


### Equipos fuera del alcance o con descubrimiento limitado

- Al abrir una lectura con la subred `192.168.1.0/24`, un activo cuya IP pertenece a otra subred no debe aparecer como “no visto” en esa lectura.
- Si el informe marca esa subred como limitada, los activos del inventario que no se observaron en esa lectura no deben presentarse como ausencias confirmadas.
- Los activos que sí se observaron se mantienen visibles, aunque el descubrimiento haya sido parcial.
