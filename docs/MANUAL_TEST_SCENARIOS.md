# Escenarios de prueba manuales sintéticos

**Objetivo:** probar la importación y la presentación de datos sin depender de
tráfico real, credenciales, registros personales ni servicios externos.

Los archivos son artificiales. No representan una observación de NetSentinel,
no demuestran actividad de una persona y no deben mezclarse con una instalación
que contenga datos reales. El generador no accede a la red ni a SQLite.

## Generar los archivos

Desde la raíz del repositorio, en la rama que contiene este documento:

    python scripts/generate_manual_scenarios.py

Los archivos se guardan por defecto en
.netsentinel-test-artifacts/manual-scenarios, un directorio excluido por
.gitignore. Para usar una dirección del dispositivo que elegiste en el
inventario y relacionarla con los registros Zeek:

    python scripts/generate_manual_scenarios.py \
      --output-dir "$HOME/.netsentinel-test-artifacts/manual-scenarios" \
      --device-ip 192.168.1.25

Reemplazá 192.168.1.25 por una IP literal registrada para el dispositivo de
prueba. El generador se niega a sobrescribir cualquiera de sus archivos ya
existentes, salvo que agregues --force. Esa opción reemplaza únicamente los
archivos que crea el generador; no borra los demás archivos del directorio.

## Aislar la base de datos y preparar un dispositivo ficticio

No apuntes NETSENTINEL_DATA_DIR a la carpeta de tu instalación habitual.
El auxiliar de prueba se niega a trabajar con la ruta predeterminada
~/.netsentinel y también se niega a sobrescribir una base SQLite existente.

En macOS o Linux, desde la raíz del repositorio con el entorno virtual activado:

    export NETSENTINEL_DATA_DIR="$HOME/.netsentinel-synthetic-test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$NETSENTINEL_DATA_DIR"
    python scripts/seed_manual_test_database.py --device-ip 192.168.56.20
    python scripts/generate_manual_scenarios.py --device-ip 192.168.56.20
    ./run.sh

El primer comando crea un único activo ficticio en una base nueva; no ejecuta
un descubrimiento de red. El segundo genera archivos locales. Usá la misma IP
en ambos comandos. Para otra ejecución, elegí una carpeta de datos distinta.
Si el archivo SQLite ya existe, el auxiliar se detiene sin modificarlo.

La base de prueba queda separada de la instalación normal. Al cerrar la prueba,
guardá el resultado que necesitás y eliminá esa carpeta solamente cuando estés
seguro de que no contiene información que quieras conservar. El generador deja
sus archivos fuera de Git, en .netsentinel-test-artifacts/manual-scenarios.

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
La IP pública 1.1.1.1 aparece solo para ejercitar el enriquecimiento GeoIP: el
dominio de prueba no se afirma relacionado con esa IP. En el mapa mundial de la
PR #182, un punto solo debe aparecer si está disponible una base GeoLite2-City
válida y esta devuelve coordenadas utilizables. Sin esa base, es correcto que
no aparezca el marcador; la aplicación no debe inventar la ubicación. Como
1.1.1.1 es una dirección anycast, el punto es una aproximación y no una
ubicación exacta del equipo o de una persona.

## Prueba B: mapa mundial de IP

El mapa no está en main; esta prueba corresponde a la
[PR #182](https://github.com/JavierGrecco/NetSentinel/pull/182).

1. Conservá los archivos generados fuera del árbol del código y probá la rama
   de la PR en una copia de trabajo separada.
2. Configurá de forma local una base GeoLite2-City autorizada siguiendo
   docs/WORLD_IP_MAP.md de esa rama.
3. Importá activity.csv mediante Actividad y abrí /world-map.
4. Comprobá el resumen, los filtros y la tabla de destinos. El evento con
   1.1.1.1 puede dibujar un punto si la base local contiene una ubicación válida.
5. Verificá también los destinos de documentación 198.51.100.0/24 y
   203.0.113.0/24: no deben convertirse en marcadores geográficos públicos.
6. Repetí la prueba sin configurar la base GeoIP. La pantalla debe comunicar
   que falta el enriquecimiento y no mostrar coordenadas inventadas.

No hace falta consultar un dominio real para probar el mapa histórico. La
consulta DNS manual es una acción distinta y representa una resolución actual,
no la IP usada durante el evento de prueba.

## Prueba C: importación Zeek

El importador Zeek pertenece a la
[PR #177](https://github.com/JavierGrecco/NetSentinel/pull/177), apilada sobre
la rama del explorador de red. No está disponible en main. Probalo en otra
copia de trabajo y no mezcles esta rama de escenarios con las ramas funcionales.

1. Iniciá la rama candidata con una base de datos aislada.
2. En el inventario, seleccioná **Dispositivo sintético de prueba**, cuya dirección
   debe coincidir con la opción --device-ip que usaste para crear la base y los archivos.
   Si es necesario, actualizá primero el inventario en tu red autorizada.
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

## Pruebas automatizadas

El generador, la validación real del CSV y el auxiliar de inventario sintético tienen pruebas automatizadas que no necesitan conexión de red:

    python -m pytest -q tests/test_manual_scenario_generator.py

Para ejecutar toda la suite:

    python -m pytest -q

## Qué registrar

Anotá el SHA exacto de la rama probada, el sistema operativo, la versión de
Python, las acciones realizadas y los resultados aprobados/fallidos. Compartí
mensajes de error y capturas revisadas, pero no una base SQLite, inventario
real, CSV de actividad real, secretos ni datos personales.

Las pruebas sintéticas permiten comprobar la tubería de importación y la
interfaz. No equivalen a validar captura en vivo, integración con un router,
precisión de una base GeoIP ni cobertura de tráfico real.
