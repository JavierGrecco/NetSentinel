# Laboratorio consolidado de aceptación para expertos

**Rama aislada:** `qa/expert-acceptance-consolidated-2026-10`  
**Estado:** candidata para pruebas manuales; no equivale a una versión estable ni está fusionada en `main`.

Este laboratorio reúne en una sola copia ejecutable los módulos que antes estaban repartidos en ramas distintas: mapa mundial GeoIP local, explorador de topología LAN histórica, importador Zeek, NetSentinel Forense y la prueba guiada dentro de la aplicación. Su finalidad es que la revisión manual compruebe la integración real de la combinación, además de las pruebas aisladas de cada módulo.

## Cobertura de aceptación

| Área | Qué tiene que comprobarse | Resultado esperado |
|---|---|---|
| Inventario y procedencia | Dispositivo sintético e intervalo de observación | El activo de prueba queda marcado como fixture y no como descubrimiento real. |
| Explorador LAN (`/network`) | Captura sintética, subred, selección, filtros, zoom, detalle textual | El grafo usa la lectura persistida y no inventa enlaces; el endpoint de topología es de solo lectura. |
| Actividad CSV | Vista previa, importación, repetición, archivos negativos | La vista previa no escribe; las repeticiones se deduplican y los archivos inválidos se rechazan sin importación parcial. |
| Importador Zeek | TSV nativo y JSON Lines, atribución por IP/fecha, contadores, UID | La vista previa precede a la escritura; bytes IP ausentes permanecen desconocidos; los UID repetidos no crean duplicados. |
| Mapa mundial (`/world-map`) | Cartografía local, tabla, filtros y eventos de actividad | Las coordenadas solo aparecen con datos de GeoIP local válidos; una IP privada o no cubierta no se sitúa artificialmente. |
| Forense (`/forensics`) | Caso, registro de evidencia, hash coincidente y discrepante, ruta inválida, auditoría, manifiestos e informe | El cambio de contenido se detecta y los resultados quedan exportables; el sistema explica los límites de confianza. |
| Navegación y accesibilidad | Ocho enlaces de sección, selector Red/Forense, teclado, lector de pantalla, tema y móvil | No hay páginas aisladas, IDs duplicados ni funciones esenciales dependientes solo del ratón. |
| Empaquetado y seguridad | Tests, límites de arquitectura, recursos estáticos locales, cabeceras y dependencias | El mismo árbol integrado debe pasar la matriz, no solo los commits de sus ramas de origen. |

## Preparación en macOS o Linux

Hacé la prueba en un checkout de esta rama. Si todavía no la tenés:

```bash
git fetch origin qa/expert-acceptance-consolidated-2026-10
git switch --track origin/qa/expert-acceptance-consolidated-2026-10
```

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

Abrí [http://127.0.0.1:8765/guided-test](http://127.0.0.1:8765/guided-test). La página contiene nueve escenarios y 24 casillas de control. Ejecutá cada acción, confirmá el resultado en la vista correspondiente y marcá la casilla solo después de observarlo. El progreso se guarda en el navegador y no es un veredicto automático.

## Orden sugerido para la prueba manual

1. **Preparación e inventario sintético.** Confirmá las rutas aisladas y que no se inició un descubrimiento real.
2. **CSV en Actividad.** Elegí `activity.csv`, revisá la vista previa, importá y repetí la importación; después probá los CSV negativos.
3. **Topología histórica.** En la guía pulsá *Comprobar API*; luego abrí `/network`, seleccioná la lectura con origen `synthetic-test-fixture` y probá búsqueda, filtros, zoom, selección y detalle textual.
4. **Zeek.** En `/activity`, elegí el activo ficticio `192.168.56.20`, cargá `$SCENARIO_DIR/zeek-conn.tsv`, previsualizá, revisá atribución y contadores, importá y repetí. Guardá si alguna fila se atribuye de forma inesperada.
5. **Mapa mundial.** En `/world-map`, revisá tabla, filtro, estados vacíos y mensajes de cobertura. Para comprobar marcadores geográficos se necesita una base GeoLite2-City autorizada y vigente instalada localmente; instalar el paquete Python no descarga esa base.
6. **Forense.** Creá el caso con valores ficticios de la propia guía, registrá la muestra, compará el hash inicial, cambiá la copia de trabajo con el comando propuesto y repetí la comparación. Revisá el registro de auditoría, manifiestos y las exportaciones JSON/Markdown.
7. **Cierre.** Recorré los enlaces entre Red/Forense, la navegación por teclado y los tamaños de escritorio/móvil. Anotá la versión de Python, SO, SHA de la rama, resultado observado y cualquier fallo.

## Pruebas automatizadas locales

Con el entorno virtual activado y desde la raíz:

```bash
python -m pytest -q
python scripts/check_architecture_boundaries.py
```

La prueba responsive requiere el navegador Playwright y una instancia de laboratorio. Seguí su ayuda antes de ejecutarla; no la apuntes a una aplicación que use datos personales. La CI del PR integrado debe validar esta misma cabeza antes de dar por aprobada la integración.

## Límites que deben quedar visibles al experto

- El mapa de LAN es una reconstrucción histórica de observaciones del inventario; las líneas no prueban tráfico ni enlaces físicos directos.
- Zeek importa metadatos exportados por la persona usuaria. No captura paquetes, no instala agentes ni se conecta a un sensor.
- La geolocalización IP es aproximada, requiere datos locales y no identifica personas ni dispositivos exactos.
- Los hashes detectan cambios de contenido, pero no autentican la identidad del operador. Los informes no tienen firma digital ni anclaje externo de auditoría.
- Los datos sintéticos no sustituyen la validación con datos autorizados reales, revisión visual manual, pruebas de accesibilidad ni recuperación de copias de seguridad.
- El laboratorio es una rama de aceptación: no publicar ni usar como versión estable sin revisar todos los checks de esta combinación y cerrar las brechas de la matriz forense.

## Limpieza

Detené NetSentinel con `Ctrl+C`. Revisá las dos rutas impresas y eliminá únicamente la carpeta que empiece por `netsentinel-test-artifacts/manual-scenarios-` de esta ejecución y el directorio dedicado `~/.netsentinel-guided-test-` correspondiente. No elimines `~/.netsentinel` ni otra carpeta de datos. Conservá los logs y capturas que ayuden a reproducir un fallo, sin incluir información personal o de tu red real.
