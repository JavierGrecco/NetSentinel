# Laboratorio consolidado de aceptación para expertos

**Corte de documentación:** 27/11/2026.  
**Rama canónica:** `main`, HEAD `295a74e16986516d6f3d5d4b3214b59d186a6e81`.  
**Estado del laboratorio:** el asistente integrado en `main` tiene 12 pasos evaluables. La [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200) añade el paso `findings-correlation`; cuando #200 se integre, el recorrido final tendrá 13 pasos.  
**Cambios de procedencia:** la [PR #222](https://github.com/JavierGrecco/NetSentinel/pull/222) añade a la aceptación CSV los casos de `blocked` ausente, vacío y false explícito. Permanece en Draft hasta ejecutar esta extensión manualmente y registrar evidencia.  
**Estado general:** la aceptación manual, la revisión visual y la accesibilidad siguen pendientes; no inferir resultados manuales desde CI.

Este laboratorio reúne en una sola copia ejecutable los módulos que antes estaban repartidos en ramas distintas: mapa mundial GeoIP local, explorador de topología LAN histórica, importador Zeek, NetSentinel Forense y el asistente de aceptación dentro de la aplicación.

El asistente reemplaza la lista de casillas dispersas por un recorrido de **12 pasos evaluables, uno por pantalla**. Explica qué se comprueba y por qué importa; abre el módulo necesario en otra pestaña sin cerrar la guía; muestra resultados de API en las pruebas automáticas de solo lectura; y permite registrar cada resultado como correcto, fallido o no comprobado. El progreso y las notas se guardan en el navegador, con un indicador visible y una señal cuando se recupera una sesión anterior. Las fases alcanzadas permiten volver a un paso sin reiniciar el recorrido; en el resumen, cada fila tiene una acción para revisar directamente ese paso y un acceso al primer pendiente o con incidencias. La guía no envía `POST /api/scan` ni inicia descubrimientos.

## Cobertura de aceptación

| Área | Qué tiene que comprobarse | Resultado esperado |
|---|---|---|
| Inventario y procedencia | Dispositivo sintético e intervalo de observación | El activo de prueba queda marcado como fixture y no como descubrimiento real. |
| Explorador LAN (`/network`) | Captura sintética, subred, selección, filtros, zoom, detalle textual | El grafo usa la lectura persistida y no inventa enlaces; el endpoint de topología es de solo lectura. |
| Actividad CSV | Vista previa, importación, repetición, archivos negativos y procedencia de `blocked` | La vista previa no escribe; las repeticiones se deduplican; los archivos inválidos se rechazan sin escrituras parciales; ausencia, vacío y false explícito siguen siendo distintos. |
| Importador Zeek | TSV nativo y JSON Lines, atribución por IP/fecha, contadores, UID | La vista previa precede a la escritura; bytes IP ausentes permanecen desconocidos; los UID repetidos no crean duplicados. |
| Mapa mundial (`/world-map`) | Cartografía local, tabla, filtros y eventos de actividad | Las coordenadas solo aparecen con datos de GeoIP local válidos; una IP privada o no cubierta no se sitúa artificialmente. |
| Forense (`/forensics`) | Caso, registro de evidencia, hash coincidente y discrepante, ruta inválida, auditoría, manifiestos e informe | El cambio de contenido se detecta y los resultados quedan exportables; el sistema explica los límites de confianza. |
| Navegación y accesibilidad | Ocho enlaces de sección, selector Red/Forense, teclado, lector de pantalla, tema y móvil | No hay páginas aisladas, IDs duplicados ni funciones esenciales dependientes solo del ratón. |
| Empaquetado y seguridad | Tests, límites de arquitectura, recursos estáticos locales, cabeceras y dependencias | El mismo árbol integrado debe pasar la matriz, no solo los commits de sus ramas de origen. |

## Preparación en macOS o Linux

Para no pisar tu rama actual ni ningún cambio local, creá una copia de trabajo separada. Desde tu checkout actual del repositorio:

```bash
git fetch origin "refs/heads/main:refs/remotes/origin/main"
git worktree add --detach ../NetSentinel-acceptance-lab refs/remotes/origin/main
cd ../NetSentinel-acceptance-lab
printf "Commit exacto que vas a probar: "
git rev-parse HEAD
git status --short
```

Este modo deja intacta tu rama y tu directorio de trabajo actual. Si ya existe una carpeta `../NetSentinel-acceptance-lab`, elegí otro nombre de carpeta antes de ejecutar `git worktree add`.

**Por qué se usa este `fetch`:** al indicar solo el nombre de la rama, Git puede dejar el commit en `FETCH_HEAD` sin crear la referencia local `origin/main`. El refspec explícito crea o actualiza `origin/main` y evita el error `fatal: invalid reference`. La copia de trabajo queda fijada al commit descargado, sin cambiar tu rama original.

Si ya apareció ese error, el comando terminó; no hay un proceso bloqueado que necesite `Ctrl+C`. Volvé a ejecutar el bloque corregido desde la raíz del repositorio. Si Git informa que la carpeta de destino ya existe, revisá `git worktree list` o elegí otro nombre de carpeta; no borres una carpeta a ciegas.

Prepará un entorno virtual y las dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test,geoip]"
```

Después, desde la raíz del repositorio, creá una carpeta de datos exclusiva y una carpeta de escenarios única para esta ejecución:

```bash
export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-guided-test-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$NETSENTINEL_DATA_DIR"
export SCENARIO_DIR="$PWD/netsentinel-test-artifacts/manual-scenarios-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$(dirname "$SCENARIO_DIR")"
python scripts/generate_manual_scenarios.py --output-dir "$SCENARIO_DIR" --device-ip 192.168.56.20
python scripts/seed_manual_test_database.py --device-ip 192.168.56.20 --include-topology
mkdir -p "$NETSENTINEL_DATA_DIR/forensics-working-copies"
python -c 'from pathlib import Path; import os, hashlib; p=Path(os.environ["NETSENTINEL_DATA_DIR"])/"forensics-working-copies"/"netsentinel-forensic-sample.bin"; p.write_bytes(b"NetSentinel synthetic evidence v1"); print("SHA-256:", hashlib.sha256(p.read_bytes()).hexdigest())'
printf "NETSENTINEL_DATA_DIR=%s\nSCENARIO_DIR=%s\n" "$NETSENTINEL_DATA_DIR" "$SCENARIO_DIR"
./run.sh
```

**Guardá las dos rutas impresas.** No apuntes `NETSENTINEL_DATA_DIR` a `~/.netsentinel` ni a una carpeta que contenga tu base habitual. El generador y el auxiliar están diseñados para preparar datos ficticios; no ejecutan escaneo de red. La fixture de topología añade una única lectura sintética con tres activos.

Abrí [http://127.0.0.1:8765/guided-test](http://127.0.0.1:8765/guided-test). Pulsá **Empezar la prueba** y seguí la pantalla actual: primero ejecutá las comprobaciones de lectura; cuando se indique, abrí el módulo en la pestaña nueva, completá exactamente esa acción y volvé a la guía. Elegí **Coincide con lo esperado**, **Encontré un fallo** o **No pude comprobarlo**; añadí una nota cuando haya alguna diferencia. No se puede avanzar sin registrar un resultado en el paso actual.

En los pasos de CSV y Zeek, el enlace abre directamente **Actividad → Importar** en la pestaña nueva (`/activity#importar`). No empieces por Resumen: antes de la primera importación puede estar vacío porque todavía no hay eventos locales. En Importar, elegí el dispositivo sintético y el archivo del directorio `SCENARIO_DIR`; la guía permanece abierta en la otra pestaña.

El progreso y las notas se guardan solo en el navegador de esta máquina. El asistente no adivina el resultado de acciones manuales: el resumen final distingue éxitos declarados, fallos y pasos sin comprobar. Completar el recorrido no equivale a certificar el producto ni sustituye revisión técnica.

## Orden sugerido para la prueba manual

1. **Preparación e inventario sintético.** Confirmá las rutas aisladas y que no se inició un descubrimiento real.
2. **CSV en Actividad.** Elegí `activity.csv`, revisá la vista previa e importá. La segunda importación debe indicar 0 eventos nuevos y 6 duplicados omitidos; después probá los CSV negativos. Para la aceptación de #222, ejecutá también la extensión de procedencia descrita debajo de este recorrido.
3. **Topología histórica.** En la guía pulsá **Comprobar ahora** y revisá los nodos/enlaces observados; luego abrí `/network`, seleccioná la lectura con origen `synthetic-test-fixture` y probá búsqueda, filtros, zoom, selección y detalle textual.
4. **Zeek.** En `/activity`, elegí el activo ficticio `192.168.56.20`, cargá `$SCENARIO_DIR/zeek-conn.tsv`, previsualizá y revisá atribución y contadores. Importá dos veces: la segunda debe mostrar 0 registros nuevos y 2 duplicados omitidos. Anotá cualquier atribución inesperada.
5. **Mapa mundial.** En `/world-map`, revisá tabla, filtro, estados vacíos y mensajes de cobertura. Para comprobar marcadores geográficos se necesita una base GeoLite2-City autorizada y vigente instalada localmente; instalar el paquete Python no descarga esa base.
6. **Forense.** Creá el caso con valores ficticios de la guía, registrá la muestra, compará el hash inicial, cambiá la copia de trabajo con el comando propuesto y repetí la comparación. Revisá transferencias, auditoría y manifiestos; creá también el informe sin firma, descargá JSON/Markdown y verificá el JSON desde una segunda terminal.
7. **Cierre.** Recorré los enlaces entre Red/Forense, la navegación por teclado y los tamaños de escritorio/móvil. Anotá la versión de Python, el SO, el SHA exacto probado (`git rev-parse HEAD`), el resultado observado y cualquier fallo.


### Extensión de aceptación de procedencia — PR #222

Ejecutar en la misma base sintética aislada, con una fecha UTC actual y una IP de destino distinta por archivo. No reutilices tu base habitual.

1. Importá un CSV cuya cabecera **no incluya** la columna `blocked`; el evento debe quedar con `blocked_observation=missing` y la interfaz debe mostrar **No informado (campo ausente)**.
2. Importá otro CSV que incluya `blocked` pero deje la celda vacía; debe quedar `empty` y mostrarse **No informado (campo vacío)**.
3. Importá un tercero con `blocked=false`; debe quedar `reported_false` y mostrarse **No bloqueado**.
4. Como control adicional, importá un evento `event_type=blocked` sin la columna; debe mostrar **Bloqueado por tipo de evento**. Un `blocked=false` explícito en un evento de ese tipo debe rechazarse por contradicción.
5. Exportá los eventos. Comprobá que el CSV incluya `blocked_observation`; importalo en otro dispositivo sintético o en otra base aislada y verifica que los tres estados no se colapsen.
6. Sobre una copia de una base anterior al cambio, ejecutá la migración. Los valores históricos 0/1 de `blocked` deben mantenerse y la procedencia debe ser `legacy_unknown`. Un registro histórico con 1 debe seguir visualizándose como bloqueado, aclarando que su procedencia no fue conservada.
7. Generá un backup y restauralo en una ubicación de prueba. Confirmá que los valores y estados de procedencia sobreviven a la restauración.

Registrar el SHA exacto probado, sistema/navegador, resultado de cada caso y evidencia sanitizada en [VALIDATION_MATRIX.md](VALIDATION_MATRIX.md). Ninguna casilla se marca por el hecho de que CI haya pasado.

## Pruebas automatizadas locales

Con el entorno virtual activado y desde la raíz:

```bash
python -m pytest -q
python scripts/check_architecture_boundaries.py
```

La prueba responsive requiere el navegador Playwright y una instancia de laboratorio. Seguí su ayuda antes de ejecutarla; no la apuntes a una aplicación que use datos personales. Antes de probar, comprobá en Actions que CI, seguridad y cadena de suministro hayan finalizado correctamente para el commit exacto de `main` que descargaste. Los checks de la PR anterior no validan automáticamente commits posteriores.

## Límites que deben quedar visibles al experto

- El mapa de LAN es una reconstrucción histórica de observaciones del inventario; las líneas no prueban tráfico ni enlaces físicos directos.
- Zeek importa metadatos exportados por la persona usuaria. No captura paquetes, no instala agentes ni se conecta a un sensor.
- La geolocalización IP es aproximada, requiere datos locales y no identifica personas ni dispositivos exactos.
- Los hashes detectan cambios de contenido, pero no autentican la identidad del operador. Los informes no tienen firma digital ni anclaje externo de auditoría.
- Los datos sintéticos no sustituyen la validación con datos autorizados reales, revisión visual manual, pruebas de accesibilidad ni recuperación de copias de seguridad.
- El laboratorio ya está integrado en `main`, pero no es una versión estable ni está aprobado para uso operativo hasta cerrar la aceptación local y las brechas de la matriz forense.

## Limpieza

Detené NetSentinel con `Ctrl+C`. Revisá las dos rutas impresas y eliminá únicamente la carpeta que empiece por `netsentinel-test-artifacts/manual-scenarios-` de esta ejecución y el directorio dedicado `~/.netsentinel-guided-test-` correspondiente. No elimines `~/.netsentinel` ni otra carpeta de datos. Conservá los logs y capturas que ayuden a reproducir un fallo, sin incluir información personal o de tu red real.
