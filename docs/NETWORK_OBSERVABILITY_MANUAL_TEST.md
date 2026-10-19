# Prueba manual del explorador de red

**Estado:** pendiente de completar por una persona usuaria antes de dar por cerrada la primera etapa.  
**Ruta:** `/network`  
**Rama:** `feat/network-observability-console-2026-10`

Estas pruebas verifican la experiencia del explorador, no demuestran que NetSentinel vea todo el tráfico de la red. No hace falta ejecutar pruebas contra redes ajenas ni instalar agentes.

## 1. Preparar la versión

Actualizá la rama del proyecto:

```bash
git fetch origin
git switch feat/network-observability-console-2026-10
git pull --ff-only origin feat/network-observability-console-2026-10
```

En una terminal, iniciá NetSentinel con el lanzador normal de tu sistema. Abrí `http://127.0.0.1:8765/network` en el navegador.

## 2. Recorrido principal

Antes de una lectura, el explorador debe explicar que todavía no hay datos o mostrar la información previamente guardada. No debe inventar equipos ni líneas para decorar el mapa.

Ejecutá un descubrimiento solo en una red propia o autorizada. Después, recargá el explorador y comprobá:

- Se ven los equipos de la lectura y las subredes registradas. La cantidad coincide con los datos de inventario, sin duplicar el mismo dispositivo por tener más de una dirección.
- Buscá un nombre, una IP, una MAC y un fabricante, uno por vez. Los filtros deben reducir el grafo y poder limpiarse sin perder la página.
- Seleccioná un equipo desde el dibujo y desde la alternativa textual. Ambos caminos deben abrir el mismo detalle.
- Verificá IP, MAC, fabricante si se conoce, estado, fecha y fuente de observación.
- Mirá el historial del equipo y los cambios registrados. Un evento debe mostrar fecha y contexto, sin presentarse como una captura completa de conexiones.
- Probá **Acercar**, **Alejar**, **Ajustar** y **Reordenar**. Después de elegir una posición, el mapa no debe saltar innecesariamente con cada actualización.
- Cambiá entre tema oscuro, medio y claro. Los nodos, el texto y los estados deben continuar distinguiéndose.

## 3. Confirmar que no se exagera la evidencia

Elegí un dispositivo que no esté en la lectura más reciente. La interfaz debe decir que no se observó en esa lectura, no afirmar que está apagado o desconectado.

Revisá la explicación de las líneas. Una línea entre dispositivo y subred solo agrupa una IP observada con un rango registrado. No confirma cableado, puerto de switch, tráfico entre dispositivos ni acciones de una aplicación.

Si no hay registros asociados al dispositivo, el panel de cambios debe explicar que no hay eventos recientes. No debe completar los espacios con actividad simulada.

## 4. Teclado y tamaños de ventana

Navegá con `Tab` y `Shift+Tab`. Debe ser posible usar los filtros, los controles del mapa y la lista textual sin depender de arrastrar nodos. Los controles deben tener foco visible y nombres comprensibles para lectores de pantalla.

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
