# Escenarios de prueba manuales sintéticos

**Objetivo:** probar la importación y la presentación de datos sin depender de
tráfico real, credenciales, registros personales ni servicios externos.

Los archivos son artificiales. No representan una observación de NetSentinel,
no demuestran actividad de una persona y no deben mezclarse con una instalación
que contenga datos reales. El generador no accede a la red ni a SQLite.

**Para la aceptación de correlación antes del merge**, usá la rama de la [PR #200](https://github.com/JavierGrecco/NetSentinel/pull/200) indicada en [el laboratorio de aceptación experto](EXPERT_ACCEPTANCE_LAB.md), y recorré `/guided-test`. `main` todavía no incluye ese paso mientras la PR siga abierta. El resto de este documento detalla archivos y casos por módulo; no requiere cambiar de rama ni repetir la preparación sobre una base que ya esté sembrada. Una vez fusionada la PR, repetí la verificación sobre el nuevo HEAD de `main`.

## Generar los archivos

Desde la raíz del checkout del código que vas a probar (la rama de la PR #200 mientras la correlación todavía no esté fusionada):

    python scripts/generate_manual_scenarios.py

Los archivos se guardan por defecto en
netsentinel-test-artifacts/manual-scenarios, un directorio excluido por
.gitignore. Para usar una dirección del dispositivo que elegiste en el
inventario y relacionarla con los registros Zeek:

    python scripts/generate_manual_scenarios.py \
      --output-dir "$HOME/netsentinel-test-artifacts/manual-scenarios" \
      --device-ip 192.168.1.25

Reemplazá 192.168.1.25 por una IP literal registrada para el dispositivo de
prueba. El generador se niega a sobrescribir cualquiera de sus archivos ya
existentes, salvo que agregues --force. Esa opción reemplaza únicamente los
archivos que crea el generador; no borra los demás archivos del directorio.

## Aislar la base de datos y preparar un dispositivo ficticio

No apuntes NETSENTINEL_DATA_DIR a la carpeta de tu instalación habitual.
El auxiliar de prueba se niega a trabajar con la ruta predeterminada
~/.netsentinel y también se niega a sobrescribir una base SQLite existente.

En macOS o Linux, desde la raíz del repositorio, prepará el entorno una sola vez
antes de usar el auxiliar. El script importa módulos reales de NetSentinel, por
eso no alcanza con tener Python instalado:

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -e ".[test]"

Con el entorno activado, generá los archivos de prueba:

    python scripts/generate_manual_scenarios.py --device-ip 192.168.56.20
    export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-synthetic-test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$NETSENTINEL_DATA_DIR"
    python scripts/seed_manual_test_database.py --device-ip 192.168.56.20 --include-topology --include-findings-correlation
    ./run.sh

El primer comando genera los archivos locales. Después, el auxiliar de base
crea un activo ficticio y, con `--include-topology`, una lectura LAN histórica de
tres dispositivos. Con `--include-findings-correlation` agrega además un único
hallazgo sintético explícito para probar la correlación. No inicia descubrimiento
ni captura tráfico real.
Generá los archivos antes de crear el activo para que las fechas sintéticas queden
dentro del intervalo histórico. Usá la misma IP en ambos comandos. Para otra
ejecución, elegí una carpeta de datos distinta.
Si el archivo SQLite ya existe, el auxiliar se detiene sin modificarlo. Al
iniciar la app, usá el entorno virtual de esta misma copia de trabajo y mantené
el mismo `NETSENTINEL_DATA_DIR` para que use la base de prueba.

La base de prueba queda separada de la instalación normal. Al cerrar la prueba,
guardá el resultado que necesitás y eliminá esa carpeta solamente cuando estés
seguro de que no contiene información que quieras conservar. El generador deja
sus archivos fuera de Git, en netsentinel-test-artifacts/manual-scenarios.

## Prueba A: importación CSV en Actividad

Esta parte utiliza el importador CSV de la aplicación principal.

1. Iniciá NetSentinel con la base aislada y abrí la sección Actividad.
2. Seleccioná el dispositivo **Dispositivo sintético de prueba** creado por el auxiliar y abrí la opción de importar CSV.
3. Elegí activity.csv del directorio generado y ejecutá primero la vista previa.
   Deben aparecer seis filas válidas. La vista previa no debe crear eventos.
4. Confirmá la importación y verificá que el resumen indique cuántas filas se
   guardaron.
5. Repetí la importación del mismo archivo. Las filas repetidas deberían
   reconocerse como duplicadas, sin crear una segunda copia de cada evento.
6. Probá activity-invalid-sensitive.csv. La importación debe rechazarlo por
   privacidad. Probá también activity-invalid-duplicate-header.csv: debe
   rechazar las cabeceras ambiguas.
7. Confirmá que los errores no guarden una parte del archivo.

Los dominios con sufijo .invalid se reservan para ejemplos y no deben resolverse.
La IP 1.1.1.1 aparece solo para ejercitar el enriquecimiento GeoIP: el dominio
de prueba no se afirma relacionado con esa IP. Como es anycast, cualquier
ubicación de su base GeoIP es aproximada, no una localización exacta de una
persona o equipo.

## Prueba B: mapa mundial de IP

El mapa está integrado en `main`. No hace falta cambiar de rama; comprobá que
la copia de trabajo use el commit de `origin/main` que vas a aceptar.

1. En Actividad, elegí el dispositivo **Dispositivo sintético de prueba** e
   importá `activity.csv`. Primero usá la vista previa; después confirmá la
   importación. La repetición debe reconocer los registros duplicados.
2. Abrí `http://127.0.0.1:8765/world-map`. El mapa base y la tabla deben
   cargarse de forma local. En la tabla deberían aparecer los destinos de los
   registros importados, aunque no estén geolocalizados.
3. Sin una base GeoLite2-City válida, la pantalla debe indicar que GeoIP no está
   disponible y no dibujar marcadores inventados. Esto es un resultado esperado,
   no un fallo del mapa. La base de países se incluye en el proyecto, pero no
   contiene las coordenadas de IP.
4. Para probar marcadores reales, instalá una base GeoLite2-City autorizada
   según `docs/WORLD_IP_MAP.md` y reiniciá la aplicación. Una IP pública solo
   recibe un punto si esa base devuelve coordenadas válidas.
5. Comprobá también los destinos de documentación `198.51.100.0/24` y
   `203.0.113.0/24`: no deben convertirse en ubicaciones geográficas públicas.

No hace falta consultar un dominio real para probar el mapa histórico. La
consulta DNS manual del mapa es una acción distinta, representa una resolución
actual y no confirma la IP utilizada durante el evento de prueba.

## Prueba C: importación Zeek en Actividad (detalle complementario)

El importador Zeek base está integrado en `main`. La correlación Hallazgos–Zeek está en la PR #200 hasta que se fusione. Este procedimiento amplía
el paso Zeek del asistente con detalle adicional; no instala Zeek, no inicia captura
y no se conecta a un sensor. Para el recorrido principal, seguí `/guided-test`.

1. Iniciá NetSentinel desde la copia de trabajo de `main` con una base de datos aislada.
2. En Actividad, seleccioná **Dispositivo sintético de prueba**, cuya dirección
   debe coincidir con la opción --device-ip que usaste para crear la base y los archivos.
   No ejecutes descubrimientos ni cambies el inventario de tu red real para completar este escenario.
3. En Actividad, elegí ese dispositivo y previsualizá zeek-conn.jsonl.
   Confirmá que se reconocen origen, destino, protocolo, puerto e ID de Zeek.
4. Repetí la vista previa con zeek-conn.tsv. Debe reconocer las directivas
   nativas #separator, #path, #fields y #types.
5. Verificá la conexión en la que el dispositivo aparece como origen y la que
   lo muestra como destino. Los contadores de envío/recepción deben orientarse
   desde la perspectiva del dispositivo seleccionado, sin invertir las
   direcciones originales del registro.
6. Los contadores ausentes deben seguir como desconocidos. Un cero escrito en
   el registro debe seguir siendo cero.
7. Importá un archivo válido y volvé a previsualizarlo; los UID ya guardados
   deben reconocerse como duplicados. Luego previsualizá zeek-invalid.jsonl:
   la fila malformada debe hacer fallar el lote completo, sin importación
   parcial.

El importador Zeek usa el historial temporal de IP para atribuir eventos. Si
la IP no corresponde al dispositivo seleccionado o el evento queda fuera del
intervalo observado, puede omitirse. Eso es preferible a atribuirlo al equipo
equivocado; no debilites esa validación para que el ejemplo aparezca.

## Prueba D: correlación de Hallazgos con conexiones Zeek

Para este escenario, generá `zeek-conn.tsv` con el generador y usá una base
nueva preparada con `--include-findings-correlation`. El registro añadido por el
auxiliar dice explícitamente que es una fixture; no es una observación de red.

1. En Actividad, seleccioná `192.168.56.20` y previsualizá `zeek-conn.tsv`.
2. Confirmá la importación y verificá que la segunda importación reporte cero
   registros nuevos y dos duplicados omitidos.
3. Abrí Hallazgos. Localizá el mensaje `Fixture sintética: evento de laboratorio
   para validar correlación Zeek` y revisá el UID, el activo y el intervalo.
4. Abrí el enlace de una conexión relacionada. Actividad debe mostrar el filtro
   exacto de UID y `zeek_conn_log`, y mantener el foco visible del registro.
5. Confirmá que la interfaz presenta esto como contexto para investigar, no como
   detección confirmada, causalidad ni prueba de intrusión.

Los registros del ejemplo se generan dentro de la ventana temporal de ±300
segundos. Como se generan unos 105 segundos antes del momento actual, si pasan
más de dos minutos entre la generación de los archivos y la preparación de la
base, regenerá los archivos en una carpeta nueva; no modifiques la fecha guardada.

## Prueba E: explorador LAN con topología sintética (detalle complementario)

En la aceptación integrada, la preparación de `docs/EXPERT_ACCEPTANCE_LAB.md` ya
crea la lectura sintética con tres activos. No vuelvas a ejecutar el auxiliar sobre
esa base: se niega a sobrescribir una base SQLite existente. Para un ensayo aislado
del explorador, prepará una base nueva y exclusiva.

Desde el checkout que contiene este script:

    export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-synthetic-topology-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$NETSENTINEL_DATA_DIR"
    python scripts/seed_manual_test_database.py --device-ip 192.168.56.20 --include-topology

Este modo opcional agrega una lectura y tres observaciones de dispositivos ficticios
relacionados con una subred RFC1918, etiquetadas como `synthetic-test-fixture`. No ejecuta
descubrimiento, ping ni comandos del sistema. Para abrir esa base con el
explorador, abrí `/network` en la misma copia de NetSentinel usando el mismo
`NETSENTINEL_DATA_DIR`, sin ejecutar dos instancias contra la misma base.

1. Abrí la página **Explorador de red** y elegí la única lectura sintética.
2. Verificá que el dispositivo `192.168.56.20` se relacione con
   `192.168.56.0/24` y la interfaz `synthetic-fixture`.
3. Revisá el detalle textual, selección, filtros y vista en escritorio/móvil.
4. La lectura debe indicar que es sintética; no la interpretes como prueba de
   un escaneo real. La base dedicada puede eliminarse al acabar la prueba.

La fixture tiene una única lectura con tres dispositivos: sirve para revisar
nodos, pertenencia a subred, selección y detalle, pero no prueba comparaciones
entre varias lecturas ni cambios de IP históricos. Esos escenarios deben
verificarse mediante las regresiones automatizadas específicas o ampliando
explícitamente la fixture, siempre con datos etiquetados como ficticios.

## Pruebas automatizadas

El generador, la validación real del CSV y el auxiliar de inventario sintético tienen pruebas automatizadas que no necesitan conexión de red:

    python -m pytest -q tests/test_manual_scenario_generator.py

Para ejecutar toda la suite:

    python -m pytest -q

## Qué registrar

Anotá el SHA exacto del commit probado, el sistema operativo, la versión de
Python, las acciones realizadas y los resultados aprobados/fallidos. Compartí
mensajes de error y capturas revisadas, pero no una base SQLite, inventario
real, CSV de actividad real, secretos ni datos personales.

Las pruebas sintéticas permiten comprobar la tubería de importación y la
interfaz. No equivalen a validar captura en vivo, integración con un router,
precisión de una base GeoIP ni cobertura de tráfico real.
