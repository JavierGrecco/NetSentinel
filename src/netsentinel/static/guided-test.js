/* Asistente de aceptación de NetSentinel: una prueba por pantalla, resultados persistentes y consultas automáticas de solo lectura. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "netsentinel.acceptance-wizard.v3";
  const LEGACY_STEP_IDS = [
    "welcome", "lab", "topology", "csv-preview", "csv-import", "csv-rejections",
    "world-map", "zeek", "forensics-case", "forensics-hash", "forensics-safety",
    "forensics-manifests", "forensics-report", "summary"
  ];
  const DEVICE_IP = "192.168.56.20";
  const STATUS_TEXT = {
    passed: "Correcto",
    failed: "Falló",
    blocked: "No pude comprobarlo",
    pending: "Pendiente"
  };

  const steps = [
    {
      id: "welcome",
      type: "intro",
      phase: "Bienvenida",
      title: "Vamos a validar NetSentinel juntos",
      lead: "No vas a recorrer una lista larga ni a saltar de una pantalla a otra sin saber por qué. Este asistente te mostrará una prueba a la vez y conservará el resultado al volver de otro módulo.",
      objective: "Comprobar la instalación local, revisar los módulos importantes y registrar claramente lo que viste.",
      why: "Una prueba útil no consiste solo en marcar casillas: tiene que demostrar qué se intentó, qué resultado apareció y qué quedó pendiente.",
      instructions: [
        "Primero validaremos la base de laboratorio y la lectura sintética.",
        "Cuando haya que mirar otro módulo, se abrirá en una pestaña nueva. No cierres esta guía: volvé haciendo clic en su pestaña; no hace falta cerrar la otra ventana para que funcionen los controles.",
        "Al volver, elegí «Coincide con lo esperado», «Encontré un fallo» o «No pude comprobarlo». No hace falta memorizar nada.",
        "Al final podrás copiar o descargar el informe del recorrido."
      ],
      expected: "La prueba usa el activo ficticio 192.168.56.20, los archivos generados para el laboratorio y una base de datos aislada. No uses datos de tu red ni evidencia real.",
      track: false
    },
    {
      id: "lab",
      type: "auto",
      phase: "Preparación",
      title: "1. Comprobar que el laboratorio está preparado",
      lead: "Esta comprobación consulta el servicio, el activo ficticio y la lectura de topología. No escribe datos ni inicia descubrimientos.",
      objective: "Verificar que la aplicación responde y que estás probando la base de laboratorio que contiene el dispositivo y la captura sintéticos.",
      why: "Si la aplicación está usando otra base, las pruebas siguientes podrían mostrar resultados vacíos o mezclar datos. Primero comprobamos el contexto, antes de tocar ningún módulo.",
      instructions: [
        "Pulsá «Comprobar ahora». La guía consultará las API locales de salud, inventario e historial.",
        "Leé cada fila del resultado. Si falta el dispositivo o la lectura sintética, no sigas con CSV o topología: abrí «¿Faltan los datos sintéticos?» en la columna izquierda y seguí la recuperación indicada.",
        "No pulses «Descubrir dispositivos» en Inventario; este recorrido no necesita escanear la red."
      ],
      expected: "La API de salud responde, aparece «Dispositivo sintético de prueba» con IP 192.168.56.20 y existe una lectura cuyo origen es synthetic-test-fixture.",
      checkKey: "lab",
      track: true
    },
    {
      id: "topology",
      type: "manual",
      phase: "Red",
      title: "2. Ver la topología guardada",
      lead: "Vamos a distinguir entre una lectura histórica y un descubrimiento nuevo. La prueba de API mostrará los nodos que están realmente guardados.",
      objective: "Comprobar que el explorador utiliza la lectura sintética persistida y que presenta el contexto y el detalle de sus nodos.",
      why: "Una visualización de red puede inducir a error si no identifica de qué lectura salen los datos. Las líneas de este grafo no demuestran tráfico en vivo ni enlaces físicos.",
      instructions: [
        "Primero pulsá «Comprobar ahora» y revisá el identificador de la lectura, el número de nodos y el número de enlaces obtenidos de la API.",
        "Después abrí «Mapa de red» en otra pestaña. En «Lectura del mapa», seleccioná la lectura identificada como synthetic-test-fixture.",
        "Buscá 192.168.56.20. Probá seleccionar un nodo, usar búsqueda y filtros, cambiar el zoom y leer la alternativa textual o el detalle del dispositivo.",
        "Volvé a esta pestaña y registrá si lo que viste coincide con el resultado de la API."
      ],
      expected: "La lectura sintética aparece con tres activos, incluye 192.168.56.20 y permite inspeccionar los detalles sin iniciar un escaneo.",
      checkKey: "topology",
      needsManual: true,
      link: "/network",
      linkLabel: "Abrir Mapa de red en otra pestaña ↗",
      track: true
    },
    {
      id: "csv-preview",
      type: "manual",
      phase: "Actividad",
      title: "3. CSV: revisar antes de importar",
      lead: "La primera prueba de Actividad comprueba la vista previa. Todavía no queremos escribir los eventos en la base.",
      objective: "Confirmar que el importador interpreta correctamente el archivo y permite revisarlo antes de guardarlo.",
      why: "Una vista previa fiable evita persistir columnas interpretadas mal, datos sensibles o filas que no corresponden al dispositivo seleccionado.",
      instructions: [
        "Abrí Actividad en la pestaña nueva. No cierres esta guía ni la pestaña de Actividad: para volver, hacé clic en la pestaña de esta guía. La sección Resumen puede estar vacía; es normal porque todavía no importamos registros.",
        "La pestaña se abrirá directamente en «Importar». Si no ocurre, elegí «Importar» en la barra de Actividad.",
        "En «Asociar al dispositivo», elegí «Dispositivo sintético de prueba» (192.168.56.20).",
        "En «Archivo CSV», elegí activity.csv dentro de la carpeta indicada por SCENARIO_DIR en la terminal. En el selector de macOS, presioná ⌘⇧G, pegá la ruta completa de SCENARIO_DIR y presioná Intro.",
        "Pulsá «Previsualizar CSV». Leé el resumen y las filas: tienen que aparecer seis filas válidas. No pulses todavía «Importar metadatos».",
        "Volvé a esta guía haciendo clic en su pestaña (no hace falta cerrar Actividad) y anotá cualquier diferencia si la vista previa no muestra las seis filas."
      ],
      expected: "La vista previa presenta seis filas válidas y explica qué se importaría sin guardar todavía los eventos.",
      link: "/activity#importar",
      linkLabel: "Abrir Actividad en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "csv-import",
      type: "manual",
      phase: "Actividad",
      title: "4. CSV: importar una vez y comprobar duplicados",
      checkKey: "csv-events",
      checkAfterAction: true,
      actionDescription: "En la otra pestaña, importá activity.csv. Después previsualizá el mismo archivo e importalo una segunda vez. Volvé aquí y pulsá «Comprobar ahora» para ver el recuento guardado.",
      lead: "Ahora que revisaste la vista previa, comprobaremos qué ocurre al confirmar la importación y al repetirla.",
      objective: "Validar que los eventos se guarden una vez y que una nueva importación del mismo archivo no cree duplicados.",
      why: "Sin idempotencia, volver a importar un archivo puede inflar contadores y distorsionar el historial de actividad.",
      instructions: [
        "En la pestaña de Actividad que ya abriste, confirmá «Importar metadatos». Leé cuántos eventos se importaron y cuántos se omitieron. No hace falta volver a elegir el archivo si sigue seleccionado.",
        "Sin cambiar el dispositivo ni el archivo, pulsá «Previsualizar CSV» otra vez. Debe indicar 6 filas válidas, 0 nuevas y 6 duplicadas que se omitirían.",
        "Pulsá «Importar metadatos» una segunda vez. El resultado esperado es 0 eventos importados y 6 duplicados omitidos.",
        "Revisá «Eventos» y volvé a esta guía haciendo clic en su pestaña; no cierres Actividad. Registrá lo observado y no marques correcto si los contadores no coinciden."
      ],
      expected: "La primera importación guarda los seis eventos válidos; la repetición identifica los registros duplicados y no vuelve a contarlos como eventos nuevos.",
      link: "/activity#importar",
      linkLabel: "Volver a Actividad en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "csv-rejections",
      type: "manual",
      phase: "Actividad",
      title: "5. CSV: rechazar archivos inválidos",
      checkKey: "csv-rejections",
      checkAfterAction: true,
      actionDescription: "Previsualizá y rechazá los dos CSV inválidos en la otra pestaña. Volvé aquí y pulsá «Comprobar ahora»: se revisará que los seis eventos válidos sigan presentes y que el marcador sensible no haya sido guardado.",
      lead: "Esta prueba negativa verifica que los datos problemáticos se rechacen por completo y dejen un mensaje comprensible.",
      objective: "Comprobar el rechazo de cabeceras sensibles y cabeceras duplicadas sin escrituras parciales.",
      why: "Aceptar un archivo inválido o solo una parte puede guardar datos sensibles o cambiar silenciosamente el significado de las columnas.",
      instructions: [
        "En «Importar», elegí el mismo dispositivo sintético.",
        "En «Archivo CSV», elegí activity-invalid-sensitive.csv. En el selector de macOS podés usar ⌘⇧G y pegar la ruta de SCENARIO_DIR. Pulsá «Previsualizar CSV»: debe rechazarse por la cabecera sensible.",
        "Luego elegí activity-invalid-duplicate-header.csv y pulsá «Previsualizar CSV»: debe rechazarse por cabeceras duplicadas. No pulses «Importar metadatos» para ninguno de los archivos inválidos.",
        "Abrí «Eventos» y comprobá que ninguno de los lotes rechazados quedó importado. No hace falta borrar nada.",
        "Volvé a esta guía haciendo clic en su pestaña; no cierres Actividad. Indicá si los dos archivos se rechazaron sin escrituras parciales."
      ],
      expected: "Ambos CSV se rechazan con un mensaje entendible y no aparece ningún evento procedente de esos archivos inválidos.",
      link: "/activity#importar",
      linkLabel: "Abrir Actividad en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "world-map",
      type: "manual",
      phase: "Geolocalización",
      title: "6. Mapa mundial: datos reales, no ubicaciones inventadas",
      lead: "La guía va a comprobar la API y el recurso cartográfico. Después revisarás qué explica la interfaz si no hay una base GeoIP instalada.",
      objective: "Validar que el mapa y la tabla muestran destinos guardados y que solo ubican una IP cuando hay coordenadas válidas de GeoIP.",
      why: "La ubicación de una IP es aproximada. Un mapa atractivo no debe sugerir una localización exacta cuando la base de datos no puede respaldarla.",
      instructions: [
        "Pulsá «Comprobar ahora» y revisá el estado de la API, el número de eventos con IP destino y el estado de GeoLite2-City.",
        "Abrí «Mapa mundial» en la pestaña nueva. La API puede responder bien aunque no haya eventos para dibujar; la tabla y los marcadores solo tendrán contenido después de importar activity.csv. Volvé a esta guía desde la barra de pestañas; no cierres ninguna.",
        "Si GeoLite2-City figura como no disponible, comprobá que la interfaz explique esa limitación y no dibuje marcadores inventados. No necesitás instalar la base geográfica para validar ese estado vacío.",
        "Si la base está disponible, comprobá que los puntos correspondan a eventos guardados y que las IP sin coordenadas sigan en la tabla.",
        "Volvé a esta guía y registrá el resultado."
      ],
      expected: "La API y la cartografía local cargan. Las ubicaciones aparecen solo cuando hay datos GeoIP válidos; si falta la base City, la falta de cobertura se comunica claramente.",
      checkKey: "map",
      needsManual: true,
      link: "/world-map",
      linkLabel: "Abrir Mapa mundial en otra pestaña ↗",
      track: true
    },
    {
      id: "zeek",
      type: "manual",
      phase: "Actividad",
      title: "7. Zeek: previsualizar e importar conn.log",
      checkKey: "zeek-events",
      checkAfterAction: true,
      actionDescription: "Previsualizá e importá zeek-conn.tsv. Luego repetí la importación del mismo archivo para comprobar duplicados. Volvé aquí y pulsá «Comprobar ahora» para ver los UID guardados.",
      lead: "Este escenario usa un archivo exportado y sintético. No arranca Zeek, no captura paquetes y no consulta un sensor.",
      objective: "Verificar la lectura de TSV nativo de Zeek, la atribución por IP y fecha, el tratamiento de contadores ausentes y la deduplicación por UID.",
      why: "Los contadores ausentes no equivalen a cero, y una conexión solo debe atribuirse cuando el dispositivo y el intervalo temporal coinciden con los datos guardados.",
      instructions: [
        "En Actividad, abrí «Importar conexiones de Zeek (conn.log)».",
        "Elegí «Dispositivo sintético de prueba» (192.168.56.20). Para encontrar zeek-conn.tsv, presioná ⌘⇧G en el selector de macOS, pegá la ruta completa indicada por SCENARIO_DIR en la terminal y elegí el archivo.",
        "Pulsá «Previsualizar registros». Revisá los UID, la hora, la IP de origen/destino y los contadores. Los campos marcados como ausentes deben permanecer desconocidos.",
        "Si la vista previa corresponde a la IP y al intervalo del activo, pulsá «Importar conexiones». Volvé a previsualizar el archivo: debe indicar 0 nuevas y 2 duplicadas.",
        "Pulsá «Importar conexiones» una segunda vez. El resultado esperado es 0 registros importados y 2 duplicados omitidos. Volvé a esta guía haciendo clic en su pestaña; no cierres Actividad.",
        "Anotá cualquier atribución, contador o cantidad inesperada."
      ],
      expected: "La vista previa explica filas aceptadas y omitidas; los contadores ausentes siguen como desconocidos y los UID repetidos no generan duplicados.",
      link: "/activity#importar",
      linkLabel: "Abrir Actividad y Zeek en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "findings-correlation",
      type: "manual",
      phase: "Hallazgos",
      title: "8. Hallazgos: revisar el contexto de conexiones Zeek",
      checkKey: "findings-correlation",
      checkAfterAction: true,
      actionTitle: "Abrí Hallazgos y compará el evento sintético con Actividad",
      actionDescription: "Después de importar zeek-conn.tsv, abrí Hallazgos en otra pestaña. Buscá el hallazgo sintético, revisá las conexiones y abrí el enlace hacia Actividad. Volvé a esta guía haciendo clic en su pestaña; no hace falta cerrar Hallazgos. Pulsá «Comprobar ahora».",
      lead: "Esta comprobación une un evento sintético de inventario con conexiones Zeek importadas de forma explícita. No inicia captura ni consulta tráfico real.",
      objective: "Verificar que Hallazgos muestra la evidencia importada del mismo activo dentro de la ventana temporal y permite volver al registro exacto de Actividad.",
      why: "La correlación debe preservar UID y procedencia para que una persona pueda revisar la fuente. La proximidad temporal por sí sola no prueba una intrusión ni una causa raíz.",
      instructions: [
        "Abrí Hallazgos en otra pestaña y seleccioná la vista que incluye todos los estados.",
        "Encontrá el evento cuyo mensaje comienza con «Fixture sintética: evento de laboratorio para validar correlación Zeek». No confundas esta fixture explícita con un evento de red real.",
        "Comprobá que muestra una o más conexiones Zeek del dispositivo sintético y una diferencia temporal dentro de ±300 segundos.",
        "Abrí el enlace de la conexión. En Actividad deben conservarse el UID Zeek exacto y el formato zeek_conn_log.",
        "Volvé a esta guía y pulsá «Comprobar ahora». Revisá el UID, el intervalo y el aviso que explica que una coincidencia no demuestra causalidad."
      ],
      expected: "Hallazgos presenta al menos una conexión Zeek importada de forma explícita del mismo activo dentro de cinco minutos; el enlace filtra Actividad por UID y formato exactos; el mensaje no atribuye una causa ni declara un ataque.",
      link: "/findings",
      linkLabel: "Abrir Hallazgos en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-case",
      type: "manual",
      phase: "Forense",
      title: "9. Forense: abrir el caso y registrar la muestra",
      lead: "A continuación se prueba un expediente artificial, con nombres y autorización ficticios. No uses evidencia real.",
      objective: "Comprobar que se puede registrar el alcance de un caso y los metadatos de recepción de un archivo sintético.",
      why: "Un registro útil necesita identificar el propósito, el alcance autorizado, quién declara la recepción y cuál es el origen del hash. El formulario no debe presentar esto como autenticidad ya comprobada.",
      instructions: [
        "Abrí NetSentinel Forense en otra pestaña. En «Nombre de quien realiza la operación», escribí Operador sintético de prueba.",
        "Pulsá «Abrir un caso» y usá los valores de referencia que aparecen debajo de estas instrucciones.",
        "En «Evidencia registrada», pulsá «Registrar un elemento de evidencia». Usá netsentinel-forensic-sample.bin como nombre original, «Copia de archivo» como tipo y el SHA-256 que imprimió el generador en la terminal.",
        "Copiá el SHA-256 exacto que aparece en las referencias debajo (también lo imprime el generador). En el origen del hash indicá «SHA-256 calculado por el generador local al crear la muestra». Como descripción de recepción, usá «Archivo artificial para validar el control de integridad; no es evidencia real».",
        "Guardá y revisá que el caso y la evidencia aparezcan en la página antes de volver al asistente."
      ],
      referenceValues: [
        ["Identificador del caso", "LAB-SINTETICO-001"],
        ["Nombre breve", "Verificación de archivo sintético"],
        ["Autorización", "AUTORIZACION-DE-PRUEBA"],
        ["Objetivo", "Probar coincidencia y discrepancia SHA-256 de una muestra sintética."],
        ["Alcance", "Solo netsentinel-forensic-sample.bin en forensics-working-copies; sin evidencia real."],
        ["Examinador", "Examinador sintético"],
        ["Operador", "Operador sintético de prueba"],
        ["Descripción breve de evidencia", "Muestra sintética de integridad"],
        ["Entregado por", "Generador local de pruebas"],
        ["Recibido por", "Examinador sintético"],
        ["Fecha/hora de recepción", "El formulario la completa automáticamente con la hora local y su offset. Verificá que coincida con la máquina de prueba."],
        ["Zona horaria", "El formulario propone la zona horaria local; comprobá que sea la adecuada para esta prueba."],
        ["Tamaño", "Dejá el campo vacío: no es necesario para esta prueba."],
        ["SHA-256 esperado", "6762a47ef555f45bc4b8a9d5b4cda875cef2630ea601db6cb538db3237bfb37a"]
      ],
      expected: "El caso sintético se guarda con alcance y autorización ficticios y la ficha de evidencia aparece bajo ese mismo caso.",
      link: "/forensics",
      linkLabel: "Abrir NetSentinel Forense en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-hash",
      type: "manual",
      phase: "Forense",
      title: "10. Forense: comprobar coincidencia y discrepancia SHA-256",
      lead: "Esta comprobación demuestra que el contenido cambió —o no— respecto del valor declarado. No demuestra por sí misma quién creó el archivo.",
      objective: "Obtener una coincidencia con la muestra inicial y una discrepancia después de cambiar solo la copia sintética de trabajo.",
      why: "El hash es una huella de contenido. Registrar una referencia y recalcular la copia en momentos distintos permite detectar modificaciones.",
      instructions: [
        "En la ficha de la evidencia, abrí «Comparar con una copia de trabajo» y usá solo el nombre netsentinel-forensic-sample.bin.",
        "Marcá que se trata de una copia de trabajo autorizada. La primera comparación debe coincidir con el SHA-256 que declaró la fuente.",
        "Usá «Copiar comando» debajo. En una segunda terminal, reemplazá PEGAR_AQUI_LA_RUTA_IMPRESA con la ruta exacta de NETSENTINEL_DATA_DIR que imprimió la preparación y ejecutá el comando.",
        "Volvé a Forense y repetí la comparación sobre el mismo nombre. Ahora debe detectar una discrepancia respecto del hash de referencia.",
        "Volvé a esta guía y registra si viste primero coincidencia y luego discrepancia."
      ],
      command: 'export NETSENTINEL_DATA_DIR="PEGAR_AQUI_LA_RUTA_IMPRESA"\npython -c \'from pathlib import Path; import os; p=Path(os.environ["NETSENTINEL_DATA_DIR"])/"forensics-working-copies"/"netsentinel-forensic-sample.bin"; p.write_bytes(b"NetSentinel synthetic evidence v2"); print("Muestra sintética actualizada:", p.name)\'',
      commandDescription: "El comando cambia solamente la copia sintética de trabajo, no el archivo original. Pegá la ruta impresa al preparar el laboratorio; no la reemplaces por una carpeta real.",
      expected: "La copia inicial coincide; tras modificar el archivo de trabajo, el resultado muestra una discrepancia. La referencia declarada no se sobrescribe.",
      link: "/forensics",
      linkLabel: "Volver a NetSentinel Forense ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-safety",
      type: "manual",
      phase: "Forense",
      title: "11. Forense: rechazar archivos y rutas inseguras",
      lead: "Esta prueba negativa verifica que el módulo no lea archivos inexistentes ni permita salir del directorio de copias de trabajo.",
      objective: "Comprobar el manejo de errores y la defensa frente a nombres que intentan subir a un directorio padre.",
      why: "Los errores deben permitir entender qué ocurrió sin filtrar rutas locales, y una ruta con «..» no debe permitir acceder a archivos ajenos al alcance.",
      instructions: [
        "En la evidencia sintética, abrí «Comparar con una copia de trabajo».",
        "Probá missing-sample.bin y confirmá que es una copia de trabajo autorizada. Debe devolverse un error controlado, sin mostrar una ruta completa.",
        "Repetí con el nombre literal ../fuera.bin. No crees ese archivo ni uses una ruta real.",
        "Revisá el mensaje y el historial de auditoría; no debe aparecer una ruta local completa.",
        "Volvé al asistente y registrá el resultado."
      ],
      expected: "Los dos intentos se rechazan; no se lee ningún archivo fuera de la carpeta permitida y el error no revela rutas locales.",
      link: "/forensics",
      linkLabel: "Abrir NetSentinel Forense ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-manifests",
      type: "manual",
      phase: "Forense",
      title: "12. Forense: revisar auditoría y manifiestos",
      lead: "Ahora vamos a sacar el historial del módulo para revisar lo que quedó registrado fuera de la página.",
      objective: "Validar el traspaso sintético, el historial de operaciones, la integridad del registro y las dos exportaciones JSON.",
      why: "El expediente tiene que permitir reconstruir qué operaciones se declararon. Un digest ayuda a detectar cambios, pero sin firma y anclaje independientes no certifica la identidad de los autores.",
      instructions: [
        "Abrí «NetSentinel Forense» en la pestaña nueva. Si no está seleccionado, elegí LAB-SINTETICO-001 en «Casos locales» y comprobá que netsentinel-forensic-sample.bin figure dentro del caso.",
        "En la tarjeta de esa evidencia, desplegá «Registrar transferencia de custodia». La persona que entrega debería ser Examinador sintético; completá la persona que recibe y los campos obligatorios con los valores de referencia de abajo.",
        "Pulsá «Registrar transferencia». Leé el mensaje de resultado y comprobá que la transferencia aparece en la tarjeta y en el historial de operaciones.",
        "Pulsá «Descargar auditoría» y «Exportar expediente». Revisá que ambos archivos JSON correspondan al caso LAB-SINTETICO-001 y contengan la evidencia y la transferencia.",
        "Volvé al asistente y registrá si el nuevo evento y las dos descargas coinciden con lo esperado."
      ],
      referenceValues: [
        ["Caso", "LAB-SINTETICO-001"],
        ["Persona que entrega", "Examinador sintético (normalmente aparece completado)"],
        ["Persona que recibe", "Custodio sintético receptor"],
        ["Motivo de la transferencia", "Traslado sintético para validar el registro de custodia."],
        ["Método de entrega", "Entrega simulada dentro del laboratorio local; no se entrega ningún objeto físico."],
        ["Fecha/hora de la transferencia", "Se completa con la hora local y su offset; verificá que corresponda a la máquina de prueba."],
        ["Estado del elemento", "Muestra digital ficticia; no hubo embalaje físico. (Campo opcional)"],
        ["Precinto", "Dejalo vacío: no hay precinto físico. (Campo opcional)"]
      ],
      expected: "El historial contiene el evento sintético y los dos JSON se descargan con el identificador del caso, los metadatos de evidencia y los eventos relevantes.",
      link: "/forensics",
      linkLabel: "Abrir historial de Forense ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-report",
      type: "manual",
      phase: "Forense",
      title: "13. Forense: generar y verificar el informe",
      lead: "La última operación funcional crea un borrador reproducible. Debe quedar explícito que está sin firma y que solo describe datos sintéticos.",
      objective: "Crear un informe, exportarlo en JSON y Markdown y comprobar que el JSON conserva un digest verificable.",
      why: "El lector tiene que distinguir un borrador versionado de un informe firmado o aprobado. La verificación de integridad no autentica automáticamente al autor.",
      instructions: [
        "Abrí NetSentinel Forense. Confirmá que esté seleccionado el caso LAB-SINTETICO-001; si no, seleccionalo en «Casos locales». El nombre del operador debe ser Operador sintético de prueba.",
        "En «Informe de examen», desplegá «Crear borrador de informe». La fecha de solicitud se completa sola. Rellená los demás campos obligatorios usando los valores de referencia de abajo; dejá Conclusiones vacías para que el campo de fundamento no sea obligatorio.",
        "Pulsá «Guardar nueva versión sin firma». En la tarjeta del informe, verificá que indique «Borrador sin firma» y que muestre un digest SHA-256.",
        "Desde esa tarjeta, descargá «JSON verificable» y «informe legible (.md)». Confirmá que corresponden al caso LAB-SINTETICO-001.",
        "Abrí una segunda ventana o pestaña de Terminal; no detengas el servidor que está ejecutando NetSentinel. Desde la raíz del repositorio/laboratorio, ejecutá .venv/bin/python -m netsentinel.forensics_report \"RUTA_COMPLETA_DEL_JSON\"; reemplazá el marcador por la ruta real del JSON descargado. El verificador debe informar que el borrador es verificable y sin firma.",
        "Volvé al asistente e indicá qué campo, descarga o verificación no coincidió. No uses ni adjuntes evidencia real."
      ],
      referenceValues: [
        ["Caso vinculado", "LAB-SINTETICO-001; seleccioná ese caso antes de abrir el formulario."],
        ["Título", "Informe de examen sintético"],
        ["Organización examinadora", "Laboratorio de pruebas"],
        ["Fecha de solicitud", "Se completa automáticamente con la fecha local de la máquina."],
        ["Solicitante", "Solicitante sintético"],
        ["Organización solicitante", "Unidad de pruebas"],
        ["Propósito", "Comprobar el flujo de generación y verificación del informe."],
        ["Alcance realizado", "Solo caso, metadatos y una muestra artificial."],
        ["Procedimientos", "Se verificaron campos obligatorios y el expediente base."],
        ["Resultados", "El flujo de generación se ejecutó con datos sintéticos."],
        ["Conclusiones", "Dejalo vacío en esta prueba; así no se exige una justificación de conclusiones."],
        ["Datos que sustentan conclusiones", "Dejalo vacío porque no se declaran conclusiones."],
        ["Limitaciones", "No hubo adquisición ni examen de evidencia real."],
        ["Disposición original", "No existe un original real; se usó una muestra artificial."],
        ["Disposición de copias y derivados", "La copia sintética de trabajo permanece en el directorio aislado; no hay derivados reales."],
        ["Autor declarado", "Autor de pruebas"],
        ["Autorizador declarado", "Dejalo vacío: no hay autorización ni firma en este borrador."]
      ],
      expected: "Se genera la versión 1 como borrador sin firma; las exportaciones JSON y Markdown corresponden al caso y el verificador acepta el JSON original.",
      link: "/forensics",
      linkLabel: "Abrir Informe de examen ↗",
      needsManual: true,
      track: true
    },
    {
      id: "summary",
      type: "summary",
      phase: "Cierre",
      title: "Recorrido finalizado",
      lead: "Este resumen reúne los resultados y las notas que registraste. Los pasos fallidos o no comprobados quedan visibles para no confundirlos con una aprobación.",
      objective: "Revisar el estado final, copiar o descargar el informe y dejar claras las incidencias que necesitan seguimiento.",
      why: "Una prueba manual es útil cuando conserva resultados reproducibles y no oculta los pasos pendientes.",
      instructions: [],
      expected: "El cierre muestra los doce pasos evaluables, su estado y las notas asociadas. El informe no contiene una aprobación automática.",
      track: false
    }
  ];

  const phaseNames = ["Preparación", "Red", "Actividad", "Geolocalización", "Hallazgos", "Forense", "Cierre"];
  const trackedSteps = steps.filter((step) => step.track);
  let state = loadState();
  const hasSavedProgress = state.currentStep > 0 || Boolean(state.finishedAt)
    || Object.values(state.records).some((record) => record && (
      Boolean(record.outcome) || Boolean(record.note) || Boolean(record.autoChecked)
    ));

  function freshState() {
    return { format_version: 4, currentStep: 0, records: {}, finishedAt: null, returnToSummary: false };
  }

  function freshRecord() {
    return { outcome: null, note: "", opened: false, autoChecked: false, autoResult: null, checking: false };
  }

  function normalizeAutoResult(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return null;
    const details = Array.isArray(value.details) ? value.details
      .filter((item) => item && typeof item === "object")
      .map((item) => ({
        label: typeof item.label === "string" ? item.label : "Detalle",
        value: typeof item.value === "string" ? item.value : "",
        ok: item.ok === true,
        level: typeof item.level === "string" ? item.level : undefined
      })) : [];
    return {
      ok: value.ok === true,
      summary: typeof value.summary === "string" ? value.summary : "",
      details,
      checkedAt: typeof value.checkedAt === "string" ? value.checkedAt : null
    };
  }

  function normalizeRecord(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return freshRecord();
    const outcomes = ["passed", "failed", "blocked"];
    return {
      outcome: outcomes.includes(value.outcome) ? value.outcome : null,
      note: typeof value.note === "string" ? value.note : "",
      opened: value.opened === true,
      autoChecked: value.autoChecked === true,
      autoResult: normalizeAutoResult(value.autoResult),
      // Si se recargó la página durante una petición, no dejar el botón bloqueado.
      checking: false,
      resultTimestamp: typeof value.resultTimestamp === "string" ? value.resultTimestamp : null
    };
  }

  function loadState() {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
      if (!saved || typeof saved !== "object" || Array.isArray(saved)
          || !saved.records || typeof saved.records !== "object" || Array.isArray(saved.records)) {
        return freshState();
      }
      const records = {};
      trackedSteps.forEach((step) => {
        if (Object.prototype.hasOwnProperty.call(saved.records, step.id)) {
          records[step.id] = normalizeRecord(saved.records[step.id]);
        }
      });
      const parsedStep = Number(saved.currentStep);
      const legacyState = saved.format_version !== 4;
      const legacyIndex = Number.isFinite(parsedStep)
        ? Math.max(0, Math.min(LEGACY_STEP_IDS.length - 1, Math.floor(parsedStep))) : 0;
      const legacyStepId = LEGACY_STEP_IDS[legacyIndex];
      const migratedIndex = steps.findIndex((step) => step.id === legacyStepId);
      return {
        format_version: 4,
        currentStep: legacyState
          ? Math.max(0, migratedIndex)
          : (Number.isFinite(parsedStep)
            ? Math.max(0, Math.min(steps.length - 1, Math.floor(parsedStep))) : 0),
        records,
        finishedAt: typeof saved.finishedAt === "string" && Number.isFinite(Date.parse(saved.finishedAt)) ? saved.finishedAt : null,
        returnToSummary: saved.returnToSummary === true
      };
    } catch (_) {
      return freshState();
    }
  }

  function saveState() {
    try {
      state.format_version = 4;
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      const indicator = $("wizardSaveStatus");
      if (indicator) {
        indicator.textContent = "Guardado en este navegador";
        indicator.classList.remove("is-error");
      }
      return true;
    } catch (_) {
      const indicator = $("wizardSaveStatus");
      if (indicator) {
        indicator.textContent = "No se pudo guardar. Descargá el informe antes de cerrar.";
        indicator.classList.add("is-error");
      }
      showMessage("El navegador no pudo guardar el progreso. Podés seguir durante esta visita; al final descargá el informe.", "warning");
      return false;
    }
  }

  function recordFor(step) {
    if (!state.records[step.id] || typeof state.records[step.id] !== "object" || Array.isArray(state.records[step.id])) {
      state.records[step.id] = freshRecord();
    }
    return state.records[step.id];
  }

  function showMessage(message, kind) {
    const target = $("wizardMessage");
    target.textContent = message || "";
    target.className = "wizard-message" + (kind ? " is-" + kind : "");
  }

  function makeNode(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function outcomeText(outcome) {
    return STATUS_TEXT[outcome] || STATUS_TEXT.pending;
  }

  function outcomeClass(outcome) {
    if (outcome === "passed") return "is-success";
    if (outcome === "failed") return "is-error";
    if (outcome === "blocked") return "is-warning";
    return "is-pending";
  }

  function statusSymbol(outcome) {
    if (outcome === "passed") return "✓";
    if (outcome === "failed") return "!";
    if (outcome === "blocked") return "—";
    return "·";
  }

  function updateProgress() {
    const outcomes = trackedSteps.map((step) => recordFor(step).outcome);
    const completed = outcomes.filter(Boolean).length;
    const passed = outcomes.filter((outcome) => outcome === "passed").length;
    const failed = outcomes.filter((outcome) => outcome === "failed").length;
    const blocked = outcomes.filter((outcome) => outcome === "blocked").length;
    const pending = trackedSteps.length - completed;
    const percentage = Math.round((completed / trackedSteps.length) * 100);
    const detail = completed + " de " + trackedSteps.length + " con resultado · "
      + passed + " correctos · " + failed + " fallidos · " + blocked
      + " sin comprobar · " + pending + " pendientes.";
    $("wizardProgressCount").textContent = percentage + "%";
    $("wizardProgressFill").style.width = percentage + "%";
    $("wizardProgressBar").setAttribute("aria-valuenow", String(percentage));
    $("wizardProgressBar").setAttribute("aria-valuetext", detail);
    $("wizardProgressText").textContent = detail;
    renderMilestones();
  }

  function renderMilestones() {
    const container = $("wizardMilestones");
    container.replaceChildren();
    phaseNames.forEach((phase) => {
      const group = trackedSteps.filter((step) => step.phase === phase);
      const done = group.filter((step) => Boolean(recordFor(step).outcome)).length;
      const activeStep = steps[state.currentStep];
      const active = activeStep && activeStep.phase === phase;
      const li = makeNode("li", "wizard-milestone" + (active ? " is-current" : "") + (group.length && done === group.length ? " is-complete" : ""));
      const nextInGroup = group.find((step) => recordFor(step).outcome !== "passed");
      const symbolText = !group.length
        ? (active ? "✓" : "—")
        : done === group.length ? "✓"
          : String(Math.max(1, group.findIndex((step) => !recordFor(step).outcome) + 1)).padStart(2, "0");
      const symbol = makeNode("span", "wizard-milestone-symbol", symbolText);
      const textWrap = makeNode("span", "wizard-milestone-copy");
      textWrap.append(makeNode("strong", "", phase));
      textWrap.append(makeNode("small", "", group.length
        ? done + " de " + group.length + " pruebas"
        : "Resumen e informe"));

      if (!group.length) {
        li.append(symbol, textWrap);
        container.append(li);
        return;
      }

      const firstIndex = trackedSteps.findIndex((step) => step.id === group[0].id);
      const prerequisitesMet = trackedSteps.slice(0, firstIndex)
        .every((step) => Boolean(recordFor(step).outcome));
      const button = makeNode("button", "wizard-milestone-button");
      button.type = "button";
      button.disabled = !prerequisitesMet && !active;
      button.setAttribute("aria-label", phase + ": " + (done === group.length
        ? "revisar esta fase"
        : "ir al primer paso pendiente o con incidencias"));
      if (active) button.setAttribute("aria-current", "step");
      button.title = button.disabled
        ? "Completá o registrá un resultado en los pasos anteriores para habilitar esta fase."
        : "Abrir el primer paso pendiente o con incidencias de esta fase.";
      button.append(symbol, textWrap);
      button.addEventListener("click", () => {
        const currentInGroup = group.find((step) => step.id === activeStep.id);
        const target = currentInGroup || nextInGroup || group[0];
        jumpToStep(target.id);
      });
      li.append(button);
      container.append(li);
    });
  }

  function showPanel(id, visible) {
    $(id).hidden = !visible;
  }

  function renderInstructions(step) {
    const list = $("wizardInstructions");
    list.replaceChildren();
    (step.instructions || []).forEach((instruction) => {
      const li = document.createElement("li");
      li.textContent = instruction;
      list.append(li);
    });
    $("wizardInstructionsHeading").textContent = step.type === "intro"
      ? "Cómo funciona este recorrido"
      : step.type === "summary" ? "Qué queda registrado" : "Qué tenés que hacer ahora";
    showPanel("wizardInstructionsHeading", true);
    list.hidden = !(step.instructions || []).length;
  }

  function renderReferenceValues(step) {
    const panel = $("wizardReferencePanel");
    const list = $("wizardReferenceValues");
    list.replaceChildren();
    const values = step.referenceValues || [];
    values.forEach(([label, value]) => {
      list.append(makeNode("dt", "", label), makeNode("dd", "", value));
    });
    $("wizardReferenceStatus").textContent = "Valores ficticios para este laboratorio. No los reutilices en expedientes ni datos reales.";
    panel.hidden = values.length === 0;
    $("wizardCopyReferenceValues").hidden = values.length === 0;
  }

  function renderCommand(step) {
    const panel = $("wizardCommandPanel");
    panel.hidden = !step.command;
    if (step.command) {
      $("wizardCommandText").textContent = step.command;
      $("wizardCommandDescription").textContent = step.commandDescription || "";
      $("wizardCommandStatus").textContent = "";
    }
  }

  function renderAutomaticResult(step, record) {
    const panel = $("wizardAutomaticPanel");
    const result = record.autoResult;
    panel.hidden = !step.checkKey || !record.autoChecked || !result;
    if (!step.checkKey || !record.autoChecked || !result) return;
    const badge = $("wizardAutomaticBadge");
    const needsAction = result.status === "needs_action";
    badge.textContent = result.ok ? "Comprobación correcta" : needsAction ? "Falta una acción previa" : "Revisar";
    badge.className = "wizard-result-badge " + (result.ok ? "is-success" : needsAction ? "is-warning" : "is-error");
    $("wizardAutomaticSummary").textContent = result.summary || "";
    const list = $("wizardAutomaticDetails");
    list.replaceChildren();
    (result.details || []).forEach((item) => {
      const warning = item.level === "warning" || needsAction;
      const li = makeNode("li", "wizard-check-result " + (item.ok ? "is-success" : warning ? "is-warning" : "is-error"));
      li.append(makeNode("span", "wizard-check-symbol", item.ok ? "✓" : warning ? "!" : "×"));
      const wrap = makeNode("span", "wizard-check-copy");
      wrap.append(makeNode("strong", "", item.label));
      wrap.append(makeNode("small", "", item.value));
      li.append(wrap);
      list.append(li);
    });
    if (!result.ok && step.id === "lab") {
      $("wizardRecoveryDetails").open = true;
    }
  }

  function manualOutcomeReady(step, record) {
    if (!step.needsManual) return false;
    if (step.checkKey) return Boolean(record.autoChecked);
    return Boolean(record.opened);
  }

  function renderManualResult(step, record) {
    const visible = manualOutcomeReady(step, record);
    showPanel("wizardManualResultPanel", visible);
    showPanel("wizardNotesPanel", visible);
    if (!visible) return;

    $("wizardNotes").value = record.note || "";
    $("wizardManualOutcomeStatus").textContent = record.outcome
      ? "Resultado guardado: " + outcomeText(record.outcome) + ". Podés cambiarlo si al revisar encontrás otra cosa."
      : "Elegí el resultado que viste. Si no coincide, no lo marques como correcto.";

    document.querySelectorAll("[data-wizard-outcome]").forEach((button) => {
      const outcome = button.dataset.wizardOutcome;
      button.classList.toggle("is-selected", record.outcome === outcome);
      button.setAttribute("aria-pressed", record.outcome === outcome ? "true" : "false");
      button.disabled = outcome === "passed" && (
        (step.needsManual && !record.opened) ||
        (step.checkKey && record.autoResult && !record.autoResult.ok)
      );
    });
    if (step.checkKey && record.autoResult && !record.autoResult.ok) {
      $("wizardManualOutcomeStatus").textContent = record.autoResult.status === "needs_action"
        ? "Todavía falta una acción para evaluar este paso. Seguí la indicación del resultado y pulsá «Comprobar de nuevo» después de completar la acción. No lo marques como correcto todavía."
        : "La comprobación automática detectó una incidencia. No se puede marcar este paso como correcto; registrá el fallo o indicá que no pudiste comprobarlo.";
    }
  }

  function canAdvance(step, record) {
    if (step.type === "intro") return true;
    if (step.type === "summary") return false;
    // Si falla el control previo del laboratorio, detenemos el recorrido aquí.
    // Así no se genera una cascada de errores por ausencia de la fixture o del servicio.
    if (step.type === "auto" && record.autoChecked && (!record.autoResult || !record.autoResult.ok)) {
      return false;
    }
    return Boolean(record.outcome);
  }

  function renderSummary() {
    const counts = { passed: 0, failed: 0, blocked: 0 };
    trackedSteps.forEach((step) => {
      const outcome = recordFor(step).outcome;
      if (outcome && Object.prototype.hasOwnProperty.call(counts, outcome)) counts[outcome] += 1;
    });
    const complete = counts.passed + counts.failed + counts.blocked === trackedSteps.length;
    const badge = $("wizardSummaryBadge");
    let summary;
    if (!complete) {
      summary = "Faltan " + (trackedSteps.length - counts.passed - counts.failed - counts.blocked) + " resultados por registrar. Volvé al paso pendiente usando «Anterior».";
      badge.textContent = "Incompleto";
      badge.className = "wizard-result-badge is-warning";
    } else if (counts.failed) {
      summary = "El recorrido terminó con " + counts.failed + " fallo(s) y " + counts.blocked + " paso(s) sin comprobar. Revisá las notas y corregí los fallos antes de considerar la integración aceptada.";
      badge.textContent = "Con incidencias";
      badge.className = "wizard-result-badge is-error";
    } else if (counts.blocked) {
      summary = "El recorrido terminó, pero " + counts.blocked + " paso(s) quedaron sin comprobar. No los contamos como correctos.";
      badge.textContent = "Parcial";
      badge.className = "wizard-result-badge is-warning";
    } else {
      summary = "Todos los pasos evaluables quedaron marcados como correctos. Es el resultado registrado en esta sesión de prueba, no una certificación ni una aprobación automática.";
      badge.textContent = "Todo correcto según el recorrido";
      badge.className = "wizard-result-badge is-success";
    }
    const finishedAt = state.finishedAt ? new Date(state.finishedAt) : new Date();
    const finishedText = new Intl.DateTimeFormat("es-AR", {
      dateStyle: "long",
      timeStyle: "short"
    }).format(finishedAt);
    $("wizardCompletionMessage").textContent = "PRUEBA GUIADA FINALIZADA · " + finishedText + ". " + summary;
    const firstIssue = trackedSteps.find((step) => recordFor(step).outcome !== "passed");
    const reviewNextIssue = $("wizardReviewNextIssue");
    reviewNextIssue.hidden = !firstIssue;
    reviewNextIssue.textContent = firstIssue && !recordFor(firstIssue).outcome
      ? "Ir al primer paso pendiente"
      : "Revisar el primer paso con incidencias";
    const rows = $("wizardSummaryRows");
    rows.replaceChildren();
    trackedSteps.forEach((step) => {
      const record = recordFor(step);
      const row = makeNode("article", "wizard-summary-row");
      const icon = makeNode("span", "wizard-summary-symbol " + outcomeClass(record.outcome), statusSymbol(record.outcome));
      const copy = makeNode("div", "wizard-summary-copy");
      copy.append(makeNode("strong", "", step.title));
      copy.append(makeNode("span", "wizard-summary-outcome " + outcomeClass(record.outcome), outcomeText(record.outcome)));
      if (record.autoResult && record.autoResult.summary) {
        copy.append(makeNode("small", "", record.autoResult.summary));
      }
      if (record.note) copy.append(makeNode("p", "wizard-summary-note", record.note));
      const reviewButton = makeNode("button", "wizard-summary-review", "Revisar paso");
      reviewButton.type = "button";
      reviewButton.dataset.wizardReviewStep = step.id;
      reviewButton.setAttribute("aria-label", "Revisar paso: " + step.title);
      row.append(icon, copy, reviewButton);
      rows.append(row);
    });
    showPanel("wizardSummaryPanel", true);
    $("wizardCopyReport").hidden = false;
    $("wizardDownloadReport").hidden = false;
    $("wizardNext").hidden = true;
    $("wizardStart").hidden = true;
    $("wizardRunCheck").hidden = true;
    $("wizardFooterHint").textContent = "El informe se genera en este navegador y no se envía a ningún servicio externo.";
  }

  function reopenedLinkLabel(label) {
    const suffix = /\s*↗$/.test(label) ? " ↗" : "";
    const plain = label.replace(/\s*↗$/, "").trim();
    if (plain.startsWith("Abrir ")) return "Volver a abrir " + plain.slice("Abrir ".length) + suffix;
    if (plain.startsWith("Volver a ")) return "Volver a abrir " + plain.slice("Volver a ".length) + suffix;
    return "Volver a abrir " + plain + suffix;
  }

  function renderStep() {
    const step = steps[state.currentStep];
    const record = step.track ? recordFor(step) : { outcome: null, note: "", opened: false, autoChecked: false, autoResult: null };
    const trackedIndex = trackedSteps.findIndex((item) => item.id === step.id);
    $("wizardStepNumber").textContent = step.type === "intro" ? "00" : step.type === "summary" ? "✓" : String(trackedIndex + 1).padStart(2, "0");
    $("wizardStepPhase").textContent = step.phase.toUpperCase();
    $("wizardStepCounter").textContent = step.type === "intro"
      ? "Antes de empezar"
      : step.type === "summary" ? "Cierre del recorrido" : "Paso " + (trackedIndex + 1) + " de " + trackedSteps.length;
    $("wizardStepTitle").textContent = step.title;
    $("wizardStepLead").textContent = step.lead;
    $("wizardObjective").textContent = step.objective;
    $("wizardWhy").textContent = step.why;
    $("wizardExpected").textContent = step.expected;
    renderInstructions(step);
    renderReferenceValues(step);
    renderCommand(step);

    showPanel("wizardAutomaticPanel", false);
    showPanel("wizardActionPanel", Boolean(step.link));
    showPanel("wizardManualResultPanel", false);
    showPanel("wizardNotesPanel", false);
    showPanel("wizardSummaryPanel", false);
    if (step.link) {
      const baseLinkLabel = step.linkLabel || "Abrir módulo en otra pestaña ↗";
      $("wizardActionLink").href = step.link;
      $("wizardActionLink").textContent = record.opened ? reopenedLinkLabel(baseLinkLabel) : baseLinkLabel;
      $("wizardActionTitle").textContent = record.opened
        ? "Módulo abierto en otra pestaña"
        : step.actionTitle || "Abrí el módulo que vamos a probar";
      const actionDescription = record.opened
        ? step.checkAfterAction
          ? "El módulo ya se abrió. Completá la acción y volvé haciendo clic en la pestaña de esta guía; no hace falta cerrar la otra. Después pulsá «Comprobar ahora»."
          : step.checkKey && !record.autoChecked
            ? "El módulo ya se abrió. Volvé haciendo clic en esta pestaña, revisá el resultado y registrá tu observación; no hace falta cerrar la otra pestaña."
            : "El módulo ya se abrió. Podés volver a consultarlo; cuando termines, regresá aquí y registrá lo que viste."
        : step.checkKey
          ? "Podés comprobar desde esta guía en cualquier momento. Para evaluar también la interfaz, abrí el módulo en otra pestaña y después volvé haciendo clic en esta pestaña; no hace falta cerrar ninguna."
          : "Se abrirá en otra pestaña. Seguí los pasos indicados, después volvé acá y registrá el resultado.";
      $("wizardActionDescription").textContent = step.actionDescription || actionDescription;
    }

    renderAutomaticResult(step, record);
    renderManualResult(step, record);

    $("wizardPrevious").disabled = state.currentStep === 0;
    $("wizardStart").hidden = step.type !== "intro";
    $("wizardRunCheck").hidden = !step.checkKey;
    $("wizardRunCheck").disabled = Boolean(record.checking);
    $("wizardRunCheck").textContent = record.checking ? "Comprobando…" : record.autoChecked ? "Comprobar de nuevo" : "Comprobar ahora";
    $("wizardNext").hidden = step.type === "intro" || step.type === "summary";
    $("wizardNext").disabled = !canAdvance(step, record);
    $("wizardNext").textContent = state.currentStep === steps.length - 2 ? "Ver resumen final →" : "Siguiente paso →";
    $("wizardCopyReport").hidden = step.type !== "summary";
    $("wizardDownloadReport").hidden = step.type !== "summary";
    $("wizardReturnToSummary").hidden = step.type === "summary" || !state.returnToSummary;
    $("wizardFooterHint").textContent = step.type === "intro"
      ? "No hace falta marcar casillas. Empezá y seguí una indicación por vez."
      : step.type === "summary"
        ? "El informe registra lo comprobado, lo que falló y lo que quedó pendiente."
        : step.type === "auto"
          ? "Esta comprobación es de solo lectura. No toca el inventario ni inicia un escaneo."
          : manualOutcomeReady(step, record)
            ? "Elegí un resultado para habilitar el siguiente paso."
            : step.checkKey
              ? step.checkAfterAction
                ? "1. Abrí el módulo y completá la acción.  2. Volvé aquí.  3. Pulsá Comprobar ahora y registrá el resultado."
                : "1. Pulsá Comprobar ahora.  2. Abrí el módulo en otra pestaña.  3. Volvé y registrá el resultado."
              : "1. Abrí el módulo en otra pestaña.  2. Volvé aquí y registrá el resultado.";
    $("wizardMessage").textContent = "";
    if (step.type === "summary") renderSummary();
    updateProgress();
  }

  async function getJson(path) {
    const response = await fetch(path, {
      method: "GET",
      cache: "no-store",
      credentials: "same-origin",
      headers: { Accept: "application/json" }
    });
    let data = null;
    try { data = await response.json(); } catch (_) { /* La llamada puede responder texto, el estado HTTP sigue sirviendo. */ }
    return { ok: response.ok, status: response.status, data };
  }

  async function checkLab() {
    const [health, devicesResponse, scansResponse] = await Promise.all([
      getJson("/api/health"),
      getJson("/api/devices?q=" + encodeURIComponent(DEVICE_IP)),
      getJson("/api/scans?limit=100")
    ]);
    const devices = Array.isArray(devicesResponse.data) ? devicesResponse.data : [];
    const scans = Array.isArray(scansResponse.data) ? scansResponse.data : [];
    const device = devices.find((item) => item && item.ip_address === DEVICE_IP);
    const scan = scans.find((item) => item && item.source === "synthetic-test-fixture");
    const deviceName = device && (device.display_name || "").toLowerCase().includes("sintético")
      ? device.display_name
      : "Activo " + DEVICE_IP + " (la captura sintética confirma su contexto)";
    const details = [
      { label: "API de salud", value: health.ok ? "HTTP " + health.status + " · servicio responde" : "No responde (HTTP " + health.status + ")", ok: health.ok },
      { label: "Activo de laboratorio", value: device ? deviceName + " · " + DEVICE_IP + " · ID " + device.id : devicesResponse.ok ? "No se encontró el activo de prueba " + DEVICE_IP : "No se pudo consultar el inventario (HTTP " + devicesResponse.status + ")", ok: Boolean(device) },
      { label: "Lectura de topología", value: scan ? "Lectura #" + scan.id + " · origen synthetic-test-fixture · " + (scan.devices_found || "activos registrados") : scansResponse.ok ? "No se encontró la lectura synthetic-test-fixture" : "No se pudo consultar el historial (HTTP " + scansResponse.status + ")", ok: Boolean(scan) }
    ];
    const ok = details.every((item) => item.ok);
    const unmet = details.filter((item) => !item.ok).map((item) => item.label + ": " + item.value);
    return {
      ok,
      details,
      summary: ok
        ? "El servicio, el dispositivo ficticio y la lectura sintética están disponibles. No se ejecutó un escaneo."
        : "No se puede continuar todavía. " + unmet.join(" · ") + ". Revisá la ayuda de preparación y volvé a comprobar."
    };
  }

  async function checkTopology() {
    const scansResponse = await getJson("/api/scans?limit=100");
    const scans = Array.isArray(scansResponse.data) ? scansResponse.data : [];
    const scan = scans.find((item) => item && item.source === "synthetic-test-fixture");
    if (!scansResponse.ok || !scan) {
      return {
        ok: false,
        summary: "No está disponible la lectura sintética. No se intentó sustituirla por datos actuales.",
        details: [{ label: "Lectura sintética", value: scansResponse.ok ? "No se encontró en el historial" : "La API devolvió HTTP " + scansResponse.status, ok: false }]
      };
    }
    const graphResponse = await getJson("/api/scans/" + encodeURIComponent(scan.id) + "/topology");
    const graph = graphResponse.data || {};
    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    const hasDevice = JSON.stringify(nodes).includes(DEVICE_IP);
    // En el laboratorio manual la lectura tiene tres activos; la fixture de navegador
    // puede cargar un único activo observado más la subred conocida.
    const hasMinimumGraph = nodes.length >= 2;
    const ok = graphResponse.ok && graph.evidence_available !== false && hasMinimumGraph && hasDevice;
    return {
      ok,
      summary: ok
        ? "La API devolvió el grafo guardado en modo de lectura. Ahora compará estos datos con la vista de Mapa de red."
        : "La respuesta no contiene toda la evidencia sintética esperada. Revisá la lectura seleccionada antes de marcar el paso.",
      details: [
        { label: "Lectura seleccionada", value: "ID " + scan.id + " · synthetic-test-fixture", ok: true },
        { label: "Grafo", value: graphResponse.ok ? nodes.length + " nodos · " + edges.length + " enlaces" : "HTTP " + graphResponse.status, ok: graphResponse.ok && hasMinimumGraph },
        { label: "Dispositivo de prueba", value: hasDevice ? DEVICE_IP + " presente en el grafo" : DEVICE_IP + " no aparece en los nodos", ok: hasDevice },
        { label: "Evidencia", value: graph.evidence_available === false ? "La API indica que no hay evidencia disponible" : "Consulta de solo lectura; no se inició un escaneo", ok: graph.evidence_available !== false }
      ]
    };
  }

  async function readSyntheticActivity() {
    const devicesResponse = await getJson("/api/devices?q=" + encodeURIComponent(DEVICE_IP));
    const devices = Array.isArray(devicesResponse.data) ? devicesResponse.data : [];
    const device = devices.find((item) => item && item.ip_address === DEVICE_IP);
    if (!devicesResponse.ok || !device) {
      return {
        ok: false,
        device: null,
        events: [],
        detail: devicesResponse.ok ? "No se encontró el activo sintético " + DEVICE_IP : "La API de inventario respondió HTTP " + devicesResponse.status
      };
    }
    const activityResponse = await getJson("/api/activity?device_id=" + encodeURIComponent(device.id) + "&limit=500");
    const payload = activityResponse.data || {};
    if (!activityResponse.ok) {
      return { ok: false, device, events: [], detail: "La API de actividad respondió HTTP " + activityResponse.status };
    }
    return {
      ok: true,
      device,
      events: Array.isArray(payload.events) ? payload.events : [],
      totalEvents: Number(payload.total_events || 0),
      detail: "Activo sintético ID " + device.id + " · " + Number(payload.total_events || 0) + " evento(s) registrados"
    };
  }

  function syntheticCsvEvents(events) {
    const csvDomains = new Set([
      "dns-probe.invalid", "web-probe.invalid", "tls-probe.invalid", "policy-probe.invalid"
    ]);
    return events.filter((event) =>
      csvDomains.has(String(event.domain || "").toLowerCase()) ||
      event.app_name === "Aplicación simulada" ||
      event.search_terms === "consulta ficticia sin datos personales"
    );
  }

  async function checkCsvEvents() {
    const snapshot = await readSyntheticActivity();
    if (!snapshot.ok) {
      return {
        ok: false,
        summary: snapshot.detail,
        details: [{ label: "Actividad local", value: snapshot.detail, ok: false }]
      };
    }
    const csvEvents = syntheticCsvEvents(snapshot.events);
    const ok = csvEvents.length === 6;
    const needsAction = csvEvents.length === 0;
    return {
      ok,
      status: ok ? "passed" : needsAction ? "needs_action" : "failed",
      summary: ok
        ? "Se encontraron los seis eventos identificables del CSV de prueba en la base local."
        : needsAction
          ? "Todavía no hay eventos del CSV guardados. Esto no demuestra un fallo del importador: abrí Actividad, importá activity.csv y volvé a comprobar. Si todavía no encontrás el archivo, usá ⌘⇧G en el selector de macOS y pegá la ruta SCENARIO_DIR que imprimió la terminal."
          : "Se esperaban seis eventos sintéticos de activity.csv, pero solo se encontró una parte. Revisá el dispositivo seleccionado, la confirmación de importación y la retención.",
      details: [
        { label: "Dispositivo consultado", value: snapshot.device.display_name + " · " + DEVICE_IP + " · ID " + snapshot.device.id, ok: true },
        { label: "Eventos sintéticos del CSV", value: csvEvents.length + " de 6 encontrados", ok, level: needsAction ? "warning" : undefined },
        { label: "Total de eventos del dispositivo", value: String(snapshot.totalEvents), ok: snapshot.totalEvents >= 6, level: snapshot.totalEvents < 6 ? "warning" : undefined }
      ]
    };
  }

  async function checkCsvRejections() {
    const snapshot = await readSyntheticActivity();
    if (!snapshot.ok) {
      return {
        ok: false,
        summary: snapshot.detail,
        details: [{ label: "Actividad local", value: snapshot.detail, ok: false }]
      };
    }
    const validCount = syntheticCsvEvents(snapshot.events).length;
    const sensitiveMarkerPresent = JSON.stringify(snapshot.events).includes("SYNTHETIC_BODY_MUST_BE_REJECTED");
    const ok = validCount === 6 && !sensitiveMarkerPresent;
    const needsAction = validCount === 0 && !sensitiveMarkerPresent;
    return {
      ok,
      status: ok ? "passed" : needsAction ? "needs_action" : "failed",
      summary: ok
        ? "Los seis eventos válidos siguen presentes y no se encontró el marcador del archivo sensible entre los eventos guardados. Antes de marcarlo correcto, confirmá que viste los mensajes de rechazo de ambos CSV; esta consulta solo verifica que el contenido sensible no se haya guardado."
        : needsAction
          ? "Todavía no hay CSV válido importado, así que no se puede concluir que el rechazo sea correcto. Importá primero activity.csv en el paso anterior y después probá los dos archivos inválidos."
          : "Hay un resultado inesperado: faltan eventos válidos o aparece un marcador que no debería importarse. Revisá la vista previa y el rechazo de los dos archivos inválidos.",
      details: [
        { label: "Eventos válidos del CSV", value: validCount + " de 6 encontrados", ok: validCount === 6, level: needsAction ? "warning" : undefined },
        { label: "Marcador de contenido sensible", value: sensitiveMarkerPresent ? "Detectado inesperadamente en los eventos" : "No aparece en los eventos guardados", ok: !sensitiveMarkerPresent },
        { label: "Total de eventos del dispositivo", value: String(snapshot.totalEvents), ok: snapshot.totalEvents >= 6, level: snapshot.totalEvents < 6 ? "warning" : undefined }
      ]
    };
  }

  async function checkZeekEvents() {
    const snapshot = await readSyntheticActivity();
    if (!snapshot.ok) {
      return {
        ok: false,
        summary: snapshot.detail,
        details: [{ label: "Actividad local", value: snapshot.detail, ok: false }]
      };
    }
    const zeekEvents = snapshot.events.filter((event) =>
      ["zeek:CManualScenario101", "zeek:CManualScenario102"].includes(String(event.source_event_id || ""))
    );
    const ok = zeekEvents.length === 2;
    const needsAction = zeekEvents.length === 0;
    return {
      ok,
      status: ok ? "passed" : needsAction ? "needs_action" : "failed",
      summary: ok
        ? "La consulta local encontró los dos UID del conn.log sintético. Compará este recuento con la vista previa y la segunda importación."
        : needsAction
          ? "Todavía no se encontró ningún registro Zeek de la prueba. Esto no demuestra que el importador falle: en Actividad → Importar, elegí zeek-conn.tsv, previsualizalo e importalo; después volvé y comprobá otra vez."
          : "Se encontraron algunos registros Zeek, pero no están los dos UID esperados. Revisá el archivo, el dispositivo y el resultado de la importación.",
      details: [
        { label: "Dispositivo consultado", value: snapshot.device.display_name + " · " + DEVICE_IP + " · ID " + snapshot.device.id, ok: true },
        { label: "UID Zeek esperados", value: zeekEvents.length + " de 2 encontrados", ok, level: needsAction ? "warning" : undefined },
        { label: "Identificadores observados", value: zeekEvents.map((event) => event.source_event_id).join(", ") || "Ninguno encontrado", ok, level: needsAction ? "warning" : undefined },
        { label: "Total de eventos del dispositivo", value: String(snapshot.totalEvents), ok: snapshot.totalEvents >= 8, level: snapshot.totalEvents < 8 ? "warning" : undefined }
      ]
    };
  }

  async function checkFindingsCorrelation() {
    const response = await getJson("/api/findings?state=all&limit=200");
    const report = response.data && typeof response.data === "object" ? response.data : {};
    const findings = Array.isArray(report.findings) ? report.findings : [];
    const fixtureMessage = "Fixture sintética: evento de laboratorio para validar correlación Zeek; no representa una observación real.";
    const finding = findings.find((item) =>
      item
      && item.source
      && item.source.system === "inventory"
      && item.evidence
      && item.evidence.message === fixtureMessage
    );
    const related = finding && finding.related_activity && typeof finding.related_activity === "object"
      ? finding.related_activity : {};
    const records = Array.isArray(related.records) ? related.records : [];
    const expectedIds = new Set(["zeek:CManualScenario101", "zeek:CManualScenario102"]);
    const deviceId = finding && finding.asset ? Number(finding.asset.device_id) : NaN;
    const match = records.find((item) =>
      item
      && expectedIds.has(String(item.source_event_id || ""))
      && Number(item.device_id) === deviceId
      && Number.isFinite(Number(item.time_delta_seconds))
      && Math.abs(Number(item.time_delta_seconds)) <= 300
    );
    const notice = String(related.notice || related.message || "").trim();
    const nonCausalNotice = /no demuestra|no prueba/i.test(notice);
    const details = [
      {
        label: "API Hallazgos",
        value: response.ok ? "HTTP " + response.status + " · consulta completada" : "HTTP " + response.status + " · no se pudo consultar",
        ok: response.ok
      },
      {
        label: "Evento sintético",
        value: finding ? "Evento de fixture encontrado · activo ID " + deviceId : "No se encontró el evento de prueba; prepará la base con --include-findings-correlation",
        ok: Boolean(finding)
      },
      {
        label: "Conexión correlacionada",
        value: match
          ? String(match.source_event_id) + " · diferencia temporal " + Math.abs(Number(match.time_delta_seconds)) + " s · activo ID " + match.device_id
          : "No se encontró un UID de la fixture del mismo activo dentro de ±300 segundos",
        ok: Boolean(match) && related.status === "matched"
      },
      {
        label: "Límite de interpretación",
        value: notice || "La respuesta no incluye la nota de interpretación",
        ok: nonCausalNotice
      }
    ];
    const ok = response.ok && Boolean(finding) && related.status === "matched"
      && Boolean(match) && nonCausalNotice;
    const needsAction = response.ok && Boolean(finding) && !match;
    if (needsAction) {
      details[2].level = "warning";
      details[2].value = "La fixture Zeek todavía no aparece correlacionada. Confirmá que zeek-conn.tsv se haya importado para el dispositivo sintético y dentro de la ventana de ±300 segundos.";
    }
    return {
      ok,
      status: ok ? "passed" : needsAction || (response.ok && !finding) ? "needs_action" : "failed",
      summary: ok
        ? "Hallazgos conserva la procedencia Zeek, la identidad del activo y el intervalo temporal. La coincidencia es contexto investigativo, no una conclusión de amenaza."
        : needsAction
          ? "El hallazgo sintético existe, pero no se encontró la conexión Zeek que debe acompañarlo. Importá zeek-conn.tsv en el paso anterior y volvé a comprobar; esto todavía no demuestra un defecto de correlación."
          : response.ok && !finding
            ? "No se encontró la fixture de Hallazgos en la base de prueba. Revisá que la preparación se ejecutara con --include-findings-correlation antes de investigar la correlación."
            : "No se pudo confirmar la correlación sintética completa. Revisá el estado de la API, la importación Zeek, el activo elegido y la ventana temporal.",
      details
    };
  }

  async function checkMap() {
    const [mapResponse, worldResponse] = await Promise.all([
      getJson("/api/geolocation/map?limit=250"),
      fetch("/static/world_110m.geojson", { method: "GET", cache: "no-store", credentials: "same-origin" })
        .then(async (response) => ({ ok: response.ok, status: response.status, data: null }))
        .catch(() => ({ ok: false, status: 0, data: null }))
    ]);
    const map = mapResponse.data || {};
    const summary = map.summary || {};
    const databases = map.databases || {};
    const cityStatus = databases.city_status || "sin estado";
    const eventCount = Number(summary.events_with_destination_ip || 0);
    const infrastructureOk = mapResponse.ok && worldResponse.ok;
    const needsAction = infrastructureOk && eventCount === 0;
    const ok = infrastructureOk && eventCount > 0;
    const details = [
      { label: "API del mapa", value: mapResponse.ok ? "HTTP " + mapResponse.status + " · servicio disponible" : "No disponible (HTTP " + mapResponse.status + ")", ok: mapResponse.ok },
      { label: "Cartografía incluida", value: worldResponse.ok ? "Recurso local cargado (HTTP " + worldResponse.status + ")" : "No se pudo cargar el archivo cartográfico", ok: worldResponse.ok },
      { label: "Eventos con IP destino", value: eventCount > 0 ? eventCount + " evento(s) disponibles para revisar" : "Todavía no hay eventos para mostrar; importá activity.csv en el paso CSV", ok: eventCount > 0, level: needsAction ? "warning" : undefined },
      { label: "Base GeoLite2-City", value: cityStatus === "available" ? "Disponible: la interfaz puede ubicar las IP cubiertas" : "No disponible: la tabla debe conservar los destinos sin inventar ubicaciones", ok: cityStatus === "available", level: cityStatus === "available" ? undefined : "warning" }
    ];
    return {
      ok,
      status: ok ? "passed" : needsAction ? "needs_action" : "failed",
      details,
      summary: ok
        ? "El servicio y el mapa base responden y hay destinos guardados para revisar. La geolocalización sigue limitada a las IP cubiertas por GeoIP; sin GeoLite2-City, los destinos deben seguir visibles en la tabla sin coordenadas inventadas."
        : needsAction
          ? "La API y la cartografía responden, pero no hay eventos con IP destino. La pantalla vacía es esperable antes de importar activity.csv, pero no alcanza para evaluar la tabla ni los marcadores. Volvé al paso de importación CSV, completalo y después repetí esta comprobación."
          : "La API o el recurso cartográfico falló. Revisá el detalle y marcá el paso como fallido si la interfaz tampoco funciona."
    };
  }

  async function runCheck() {
    const step = steps[state.currentStep];
    if (!step.checkKey) return;
    const record = recordFor(step);
        record.checking = true;
    showMessage("Ejecutando una comprobación de lectura…");
    $("wizardRunCheck").disabled = true;
    $("wizardRunCheck").textContent = "Comprobando…";
    saveState();
    try {
      let result;
      if (step.checkKey === "lab") result = await checkLab();
      else if (step.checkKey === "topology") result = await checkTopology();
      else if (step.checkKey === "map") result = await checkMap();
      else if (step.checkKey === "csv-events") result = await checkCsvEvents();
      else if (step.checkKey === "csv-rejections") result = await checkCsvRejections();
      else if (step.checkKey === "zeek-events") result = await checkZeekEvents();
      else if (step.checkKey === "findings-correlation") result = await checkFindingsCorrelation();
      else throw new Error("No hay una comprobación asociada a este paso.");
      record.autoChecked = true;
      record.autoResult = {
        ok: Boolean(result.ok),
        status: result.status || (result.ok ? "passed" : "failed"),
        summary: result.summary,
        details: result.details || [],
        checkedAt: new Date().toISOString()
      };
      record.checking = false;
      if (step.type === "auto") {
        record.outcome = result.ok ? "passed" : "failed";
        record.resultTimestamp = new Date().toISOString();
      } else if (!result.ok && record.outcome === "passed") {
        // Una nueva comprobación no puede conservar un aprobado que acaba de contradecir.
        record.outcome = null;
        record.resultTimestamp = null;
      }
      saveState();
      renderStep();
      if (result.ok) showMessage("Comprobación finalizada. Revisá los datos observados y seguí la indicación del paso.", "success");
      else if (result.status === "needs_action") {
        showMessage(result.summary, "warning");
      } else {
        showMessage("La comprobación encontró una condición que revisar. Abrí la ayuda de preparación si faltan datos sintéticos.", "error");
        if (step.id === "lab") $("wizardRecoveryDetails").open = true;
      }
    } catch (error) {
      record.checking = false;
      record.autoChecked = true;
      record.autoResult = {
        ok: false,
        summary: error && error.message ? error.message : "No se pudo completar la comprobación.",
        details: [{ label: "Comprobación", value: error && error.message ? error.message : "Error inesperado", ok: false }],
        checkedAt: new Date().toISOString()
      };
      if (step.type === "auto") {
        record.outcome = "failed";
        record.resultTimestamp = new Date().toISOString();
      }
      saveState();
      renderStep();
      showMessage("No se pudo completar la comprobación. Revisá el mensaje y no marques el paso como correcto.", "error");
      if (step.id === "lab") $("wizardRecoveryDetails").open = true;
    }
  }

  function makeReportText() {
    const date = state.finishedAt ? new Date(state.finishedAt) : new Date();
    const counts = { passed: 0, failed: 0, blocked: 0 };
    trackedSteps.forEach((step) => {
      const outcome = recordFor(step).outcome;
      if (outcome && Object.prototype.hasOwnProperty.call(counts, outcome)) counts[outcome] += 1;
    });
    const evaluated = counts.passed + counts.failed + counts.blocked;
    const pending = trackedSteps.length - evaluated;
    const lines = [
      "NetSentinel — Informe del asistente de aceptación",
      "Fecha de cierre: " + new Intl.DateTimeFormat("es-AR", { dateStyle: "long", timeStyle: "short" }).format(date),
      "Modo: laboratorio local con datos sintéticos.",
      "Resumen: " + evaluated + " de " + trackedSteps.length + " pasos con resultado registrado.",
      "Correctos: " + counts.passed + " · Fallidos: " + counts.failed
        + " · No comprobados: " + counts.blocked + " · Pendientes: " + pending + ".",
      "Nota: los resultados manuales son autodeclarados. Este informe no equivale a certificación ni aprobación automática.",
      ""
    ];
    trackedSteps.forEach((step, index) => {
      const record = recordFor(step);
      lines.push((index + 1) + ". " + step.title);
      lines.push("   Resultado: " + outcomeText(record.outcome));
      if (record.autoResult && record.autoResult.summary) lines.push("   Comprobación automática: " + record.autoResult.summary);
      if (record.autoResult && record.autoResult.details) {
        record.autoResult.details.forEach((item) => lines.push("   - " + item.label + ": " + item.value));
      }
      if (record.note) lines.push("   Nota: " + record.note.replace(/\s+/g, " ").trim());
      lines.push("");
    });
    return lines.join("\n");
  }

  async function copyText(value) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(value);
      return;
    }
    const field = document.createElement("textarea");
    field.value = value;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.append(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("El navegador no permitió copiar. Podés descargar el informe .txt.");
  }

  function focusCurrentStepTitle() {
    const title = $("wizardStepTitle");
    if (!title) return;
    try {
      title.focus({ preventScroll: true });
    } catch (_) {
      title.focus();
    }
  }

  function jumpToStep(stepId) {
    const targetIndex = steps.findIndex((step) => step.id === stepId && step.track);
    if (targetIndex < 1 || targetIndex >= steps.length - 1) return;
    const returningFromCompletedSummary = steps[state.currentStep].type === "summary"
      || Boolean(state.finishedAt) || state.returnToSummary;
    state.returnToSummary = returningFromCompletedSummary;
    state.currentStep = targetIndex;
    // Si se vuelve a revisar una prueba, la fecha de cierre debe renovarse al terminar otra vez.
    state.finishedAt = null;
    saveState();
    renderStep();
    focusCurrentStepTitle();
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
    });
    showMessage("Volviste a «" + steps[targetIndex].title + "». Las respuestas y notas anteriores se conservaron; podés ajustarlas según lo que observes.", "success");
  }

  function advance() {
    const step = steps[state.currentStep];
    const record = step.track ? recordFor(step) : null;
    if (!canAdvance(step, record || {})) {
      showMessage("Registrá el resultado de este paso antes de continuar.", "warning");
      return;
    }
    state.currentStep = Math.min(steps.length - 1, state.currentStep + 1);
    if (steps[state.currentStep].type === "summary") {
      if (!state.finishedAt) state.finishedAt = new Date().toISOString();
      state.returnToSummary = false;
    }
    saveState();
    renderStep();
    focusCurrentStepTitle();
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function goBack() {
    if (steps[state.currentStep].type === "summary") {
      state.returnToSummary = true;
      state.finishedAt = null;
    }
    state.currentStep = Math.max(0, state.currentStep - 1);
    saveState();
    renderStep();
    focusCurrentStepTitle();
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function setOutcome(outcome) {
    const step = steps[state.currentStep];
    if (!step.track || !step.needsManual) return;
    const record = recordFor(step);
    if (!manualOutcomeReady(step, record)) {
      showMessage("Primero completá la comprobación automática, si la hay, y abrí el módulo en otra pestaña.", "warning");
      return;
    }
    if (outcome === "passed" && step.needsManual && !record.opened) {
      showMessage("Para marcarlo como correcto, abrí el módulo y revisá su interfaz. No hace falta cerrar la otra pestaña: volvé haciendo clic en esta guía.", "warning");
      return;
    }
    if (outcome === "passed" && step.checkKey && record.autoResult && !record.autoResult.ok) {
      showMessage("La comprobación automática encontró una incidencia: este paso no puede quedar registrado como correcto.", "error");
      return;
    }
    record.outcome = outcome;
    record.resultTimestamp = new Date().toISOString();
    record.note = $("wizardNotes").value || record.note || "";
    saveState();
    renderStep();
    showMessage(
      outcome === "passed" ? "Resultado guardado como correcto. Ya podés continuar." :
      outcome === "failed" ? "Fallo guardado. Podés continuar; la incidencia aparecerá en el informe final." :
      "El paso quedó registrado como no comprobado. No se contará como correcto.",
      outcome === "passed" ? "success" : outcome === "failed" ? "error" : "warning"
    );
  }

  $("wizardStart").addEventListener("click", advance);
  $("wizardNext").addEventListener("click", advance);
  $("wizardPrevious").addEventListener("click", goBack);
  $("wizardRunCheck").addEventListener("click", runCheck);

  $("wizardReviewNextIssue").addEventListener("click", () => {
    const firstIssue = trackedSteps.find((step) => recordFor(step).outcome !== "passed");
    if (firstIssue) jumpToStep(firstIssue.id);
  });

  $("wizardReturnToSummary").addEventListener("click", () => {
    const missing = trackedSteps.find((step) => !recordFor(step).outcome);
    if (missing) {
      showMessage("Todavía falta registrar «" + missing.title + "». Completá ese paso antes de volver al resumen.", "warning");
      return;
    }
    state.currentStep = steps.length - 1;
    state.finishedAt = new Date().toISOString();
    state.returnToSummary = false;
    saveState();
    renderStep();
    focusCurrentStepTitle();
    window.scrollTo({
      top: 0,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
    });
    showMessage("Resumen actualizado con los resultados y notas conservados.", "success");
  });

  $("wizardSummaryRows").addEventListener("click", (event) => {
    const button = event.target.closest("[data-wizard-review-step]");
    if (button) jumpToStep(button.dataset.wizardReviewStep);
  });

  $("wizardActionLink").addEventListener("click", () => {
    const step = steps[state.currentStep];
    if (!step.link || !step.track) return;
    const record = recordFor(step);
    record.opened = true;
    saveState();
    renderStep();
    $("wizardFooterHint").textContent = step.checkKey && !record.autoChecked
      ? step.checkAfterAction
        ? "Volvé a esta pestaña y pulsá «Comprobar ahora» para revisar los datos guardados."
        : "Volvé a esta pestaña, revisá los resultados automáticos y registrá el resultado."
      : "Volvé a esta pestaña cuando termines de revisar el módulo.";
    let returnMessage;
    if (step.checkAfterAction) {
      returnMessage = "La guía sigue abierta aquí. Completá la acción en la otra pestaña y volvé haciendo clic en esta pestaña; no hace falta cerrar la otra. Después pulsá «Comprobar ahora».";
    } else if (step.checkKey && !record.autoChecked) {
      returnMessage = "La guía sigue abierta aquí. Al volver, pulsá «Comprobar ahora» y revisá el resultado antes de registrar tu observación.";
    } else if (step.checkKey && record.autoResult && !record.autoResult.ok) {
      returnMessage = "La comprobación automática detectó una incidencia. Registrá el fallo o «No pude comprobarlo»; no se puede marcar como correcto.";
    } else {
      returnMessage = "La guía sigue abierta aquí. Cuando termines en la otra pestaña, volvé y registrá el resultado que observaste.";
    }
    showMessage(returnMessage, "success");
  });

  document.querySelectorAll("[data-wizard-outcome]").forEach((button) => {
    button.addEventListener("click", () => setOutcome(button.dataset.wizardOutcome));
  });

  $("wizardNotes").addEventListener("input", () => {
    const step = steps[state.currentStep];
    if (!step.track) return;
    recordFor(step).note = $("wizardNotes").value;
    saveState();
  });

  $("wizardRestart").addEventListener("click", () => {
    if (!window.confirm("¿Reiniciar el recorrido? Se borrarán las respuestas y notas guardadas en este navegador, pero no se eliminarán la base de datos ni los archivos del laboratorio.")) return;
    state = freshState();
    saveState();
    $("wizardRecoveryDetails").open = false;
    renderStep();
    focusCurrentStepTitle();
    showMessage("Recorrido reiniciado. La base y los datos sintéticos siguen intactos.", "success");
    window.scrollTo({ top: 0, behavior: "auto" });
  });

  $("wizardCopyRecovery").addEventListener("click", async () => {
    try {
      await copyText($("wizardRecoveryCommand").textContent);
      $("wizardRecoveryStatus").textContent = "Comandos copiados. Revisá que estés en la raíz del laboratorio y que hayas detenido el servidor anterior.";
    } catch (error) {
      $("wizardRecoveryStatus").textContent = error && error.message ? error.message : "No se pudieron copiar los comandos.";
    }
  });

  $("wizardCopyReferenceValues").addEventListener("click", async () => {
    const step = steps[state.currentStep];
    const values = step.referenceValues || [];
    if (!values.length) return;
    try {
      await copyText(values.map(([label, value]) => label + ": " + value).join(String.fromCharCode(10)));
      $("wizardReferenceStatus").textContent = "Valores copiados. Pegalos solo en el formulario ficticio de este paso.";
      showMessage("Valores de referencia copiados al portapapeles.", "success");
    } catch (error) {
      $("wizardReferenceStatus").textContent = error && error.message ? error.message : "No se pudieron copiar los valores.";
    }
  });

  $("wizardCopyCommand").addEventListener("click", async () => {
    try {
      await copyText($("wizardCommandText").textContent);
      $("wizardCommandStatus").textContent = "Comando copiado. Reemplazá el marcador por la ruta exacta impresa en la terminal.";
    } catch (error) {
      $("wizardCommandStatus").textContent = error && error.message ? error.message : "No se pudo copiar el comando.";
    }
  });

  $("wizardCopyReport").addEventListener("click", async () => {
    try {
      await copyText(makeReportText());
      $("wizardFooterHint").textContent = "Informe copiado al portapapeles.";
      showMessage("Informe copiado. Revisá y guardá una copia en el lugar donde documentes la aceptación.", "success");
    } catch (error) {
      showMessage(error && error.message ? error.message : "No se pudo copiar el informe.", "error");
    }
  });

  $("wizardDownloadReport").addEventListener("click", () => {
    const content = makeReportText();
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "netsentinel-acceptance-report.txt";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    // No revocar la URL de inmediato: algunos navegadores todavía están iniciando la descarga.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    showMessage("Informe .txt descargado en tu computadora.", "success");
  });

  const resumeNotice = $("wizardResumeNotice");
  if (hasSavedProgress) {
    resumeNotice.hidden = false;
    resumeNotice.textContent = "Se recuperó un recorrido anterior de este navegador. Retomás en el paso guardado; podés volver a fases anteriores sin perder notas.";
  }
  renderStep();
})();
