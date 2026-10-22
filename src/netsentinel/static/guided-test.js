/* Asistente de aceptación de NetSentinel: una prueba por pantalla, resultados persistentes y consultas automáticas de solo lectura. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "netsentinel.acceptance-wizard.v2";
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
        "Cuando haya que mirar otro módulo, se abrirá en una pestaña nueva. Esta guía quedará abierta en la pestaña actual.",
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
        "Abrí Actividad en otra pestaña y entrá en la sección «Importar».",
        "En «Asociar al dispositivo», elegí «Dispositivo sintético de prueba» (192.168.56.20).",
        "En «Archivo CSV», seleccioná activity.csv dentro de la carpeta SCENARIO_DIR que imprimió la terminal al preparar el laboratorio.",
        "Pulsá «Previsualizar CSV». Leé el resumen y las filas: tienen que aparecer seis filas válidas. No pulses todavía «Importar metadatos».",
        "Volvé a esta guía y anotá cualquier diferencia si la vista previa no muestra las seis filas."
      ],
      expected: "La vista previa presenta seis filas válidas y explica qué se importaría sin guardar todavía los eventos.",
      link: "/activity",
      linkLabel: "Abrir Actividad en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "csv-import",
      type: "manual",
      phase: "Actividad",
      title: "4. CSV: importar una vez y comprobar duplicados",
      lead: "Ahora que revisaste la vista previa, comprobaremos qué ocurre al confirmar la importación y al repetirla.",
      objective: "Validar que los eventos se guarden una vez y que una nueva importación del mismo archivo no cree duplicados.",
      why: "Sin idempotencia, volver a importar un archivo puede inflar contadores y distorsionar el historial de actividad.",
      instructions: [
        "En la pestaña de Actividad que ya abriste, confirmá «Importar metadatos». Leé el resumen de importados y duplicados.",
        "Sin cambiar el dispositivo, volvé a seleccionar activity.csv y pulsá «Previsualizar CSV» otra vez.",
        "Revisá el resumen de registros ya vistos o duplicados. Si el resumen no lo explica, revisá la lista de eventos para comprobar que no haya una segunda copia.",
        "Volvé al asistente y registrá el resultado observado."
      ],
      expected: "La primera importación guarda los seis eventos válidos; la repetición identifica los registros duplicados y no vuelve a contarlos como eventos nuevos.",
      link: "/activity",
      linkLabel: "Volver a Actividad en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "csv-rejections",
      type: "manual",
      phase: "Actividad",
      title: "5. CSV: rechazar archivos inválidos",
      lead: "Esta prueba negativa verifica que los datos problemáticos se rechacen por completo y dejen un mensaje comprensible.",
      objective: "Comprobar el rechazo de cabeceras sensibles y cabeceras duplicadas sin escrituras parciales.",
      why: "Aceptar un archivo inválido o solo una parte puede guardar datos sensibles o cambiar silenciosamente el significado de las columnas.",
      instructions: [
        "En «Importar», elegí el mismo dispositivo sintético.",
        "Previsualizá activity-invalid-sensitive.csv. El archivo debe rechazarse por la cabecera sensible.",
        "Previsualizá activity-invalid-duplicate-header.csv. El archivo debe rechazarse por ambigüedad.",
        "Abrí «Eventos» y comprobá que ninguno de los lotes rechazados quedó importado. No hace falta borrar nada.",
        "Volvé al asistente e indicá si los dos archivos se rechazaron sin escrituras parciales."
      ],
      expected: "Ambos CSV se rechazan con un mensaje entendible y no aparece ningún evento procedente de esos archivos inválidos.",
      link: "/activity",
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
        "Abrí «Mapa mundial» en otra pestaña. Revisá mapa base, tabla de destinos y filtro.",
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
      lead: "Este escenario usa un archivo exportado y sintético. No arranca Zeek, no captura paquetes y no consulta un sensor.",
      objective: "Verificar la lectura de TSV nativo de Zeek, la atribución por IP y fecha, el tratamiento de contadores ausentes y la deduplicación por UID.",
      why: "Los contadores ausentes no equivalen a cero, y una conexión solo debe atribuirse cuando el dispositivo y el intervalo temporal coinciden con los datos guardados.",
      instructions: [
        "En Actividad, abrí «Importar conexiones de Zeek (conn.log)».",
        "Elegí «Dispositivo sintético de prueba» (192.168.56.20) y seleccioná zeek-conn.tsv dentro de SCENARIO_DIR.",
        "Pulsá «Previsualizar registros». Revisá los UID, la hora, la IP de origen/destino y los contadores. Los campos marcados como ausentes deben permanecer desconocidos.",
        "Si la vista previa corresponde a la IP y al intervalo del activo, pulsá «Importar conexiones». Después previsualizá el mismo archivo otra vez y revisá los UID duplicados.",
        "Volvé a esta guía y anotá cualquier atribución o contador inesperado."
      ],
      expected: "La vista previa explica filas aceptadas y omitidas; los contadores ausentes siguen como desconocidos y los UID repetidos no generan duplicados.",
      link: "/activity",
      linkLabel: "Abrir Actividad y Zeek en otra pestaña ↗",
      needsManual: true,
      track: true
    },
    {
      id: "forensics-case",
      type: "manual",
      phase: "Forense",
      title: "8. Forense: abrir el caso y registrar la muestra",
      lead: "A continuación se prueba un expediente artificial, con nombres y autorización ficticios. No uses evidencia real.",
      objective: "Comprobar que se puede registrar el alcance de un caso y los metadatos de recepción de un archivo sintético.",
      why: "Un registro útil necesita identificar el propósito, el alcance autorizado, quién declara la recepción y cuál es el origen del hash. El formulario no debe presentar esto como autenticidad ya comprobada.",
      instructions: [
        "Abrí NetSentinel Forense en otra pestaña. En «Nombre de quien realiza la operación», escribí Operador sintético de prueba.",
        "Pulsá «Abrir un caso» y usá los valores de referencia que aparecen debajo de estas instrucciones.",
        "En «Evidencia registrada», pulsá «Registrar un elemento de evidencia». Usá netsentinel-forensic-sample.bin como nombre original, «Copia de archivo» como tipo y el SHA-256 que imprimió el generador en la terminal.",
        "En el origen del hash indicá «SHA-256 calculado por el generador local al crear la muestra». Como descripción de recepción, usá «Archivo artificial para validar el control de integridad; no es evidencia real».",
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
        ["Recibido por", "Examinador sintético"]
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
      title: "9. Forense: comprobar coincidencia y discrepancia SHA-256",
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
      title: "10. Forense: rechazar archivos y rutas inseguras",
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
      title: "11. Forense: revisar auditoría y manifiestos",
      lead: "Ahora vamos a sacar el historial del módulo para revisar lo que quedó registrado fuera de la página.",
      objective: "Validar el traspaso sintético, el historial de operaciones, la integridad del registro y las dos exportaciones JSON.",
      why: "El expediente tiene que permitir reconstruir qué operaciones se declararon. Un digest ayuda a detectar cambios, pero sin firma y anclaje independientes no certifica la identidad de los autores.",
      instructions: [
        "En la evidencia sintética, registrá un traspaso de Examinador sintético a Custodio sintético receptor, con motivo y método explícitos.",
        "Confirmá que el nuevo evento aparece en el historial de operaciones y que el estado de integridad se muestra.",
        "Pulsa «Descargar auditoría» y «Exportar expediente». Abre ambos JSON y verifica que hagan referencia al caso LAB-SINTETICO-001 e incluyan los eventos y la evidencia que registraste.",
        "Volvé al asistente y registrá si ambas exportaciones se generaron y correspondían al caso correcto."
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
      title: "12. Forense: generar y verificar el informe",
      lead: "La última operación funcional crea un borrador reproducible. Debe quedar explícito que está sin firma y que solo describe datos sintéticos.",
      objective: "Crear un informe, exportarlo en JSON y Markdown y comprobar que el JSON conserva un digest verificable.",
      why: "El lector tiene que distinguir un borrador versionado de un informe firmado o aprobado. La verificación de integridad no autentica automáticamente al autor.",
      instructions: [
        "En «Informe de examen», pulsá «Crear borrador de informe» y completá los campos obligatorios con los valores de referencia de abajo.",
        "Guardá la versión 1 y verificá que la tarjeta indique «Borrador sin firma».",
        "Descargá JSON y Markdown. Confirmá que el JSON se refiera al caso sintético y contenga el digest del informe.",
        "Conservá intacto el JSON exportado y ejecutá python -m netsentinel.forensics_report RUTA_DEL_JSON con la ruta real del archivo descargado.",
        "Volvé al asistente. Si algo falló, registrá qué campo, descarga o verificación no coincidió."
      ],
      referenceValues: [
        ["Título", "Informe de examen sintético"],
        ["Organización examinadora", "Laboratorio de pruebas"],
        ["Solicitante", "Solicitante sintético"],
        ["Organización solicitante", "Unidad de pruebas"],
        ["Propósito", "Comprobar el flujo de generación y verificación del informe."],
        ["Alcance realizado", "Solo caso, metadatos y una muestra artificial."],
        ["Procedimientos", "Se verificaron campos obligatorios y el expediente base."],
        ["Resultados", "El flujo de generación se ejecutó con datos sintéticos."],
        ["Conclusiones", "No se formula una conclusión sobre evidencia real."],
        ["Fundamento", "La conclusión se limita a la respuesta observada en esta prueba automatizada."],
        ["Limitaciones", "No hubo adquisición ni examen de evidencia real."],
        ["Disposición original", "El original no existe; se usó una muestra artificial."],
        ["Autor declarado", "Autor de pruebas"]
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

  const phaseNames = ["Preparación", "Red", "Actividad", "Geolocalización", "Forense"];
  const trackedSteps = steps.filter((step) => step.track);
  let state = loadState();

  function freshState() {
    return { currentStep: 0, records: {}, finishedAt: null };
  }

  function loadState() {
    try {
      const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "null");
      if (!saved || typeof saved !== "object" || !saved.records || typeof saved.records !== "object") {
        return freshState();
      }
      return {
        currentStep: Math.max(0, Math.min(steps.length - 1, Number(saved.currentStep) || 0)),
        records: saved.records,
        finishedAt: typeof saved.finishedAt === "string" ? saved.finishedAt : null
      };
    } catch (_) {
      return freshState();
    }
  }

  function saveState() {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (_) {
      showMessage("El navegador no pudo guardar el progreso. Podés seguir durante esta visita; al final descargá el informe.", "warning");
      return false;
    }
  }

  function recordFor(step) {
    if (!state.records[step.id]) {
      state.records[step.id] = { outcome: null, note: "", opened: false, autoChecked: false, autoResult: null };
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
    const completed = trackedSteps.filter((step) => Boolean(recordFor(step).outcome)).length;
    const percentage = Math.round((completed / trackedSteps.length) * 100);
    $("wizardProgressCount").textContent = percentage + "%";
    $("wizardProgressFill").style.width = percentage + "%";
    $("wizardProgressBar").setAttribute("aria-valuenow", String(percentage));
    $("wizardProgressText").textContent = completed === trackedSteps.length
      ? "Todos los pasos evaluables tienen un resultado registrado."
      : completed + " de " + trackedSteps.length + " pasos evaluados. El asistente no adivina resultados manuales.";
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
      const symbol = makeNode("span", "wizard-milestone-symbol", done === group.length && group.length ? "✓" : String(group.findIndex((step) => !recordFor(step).outcome) + 1).padStart(2, "0"));
      const textWrap = makeNode("span", "wizard-milestone-copy");
      textWrap.append(makeNode("strong", "", phase));
      textWrap.append(makeNode("small", "", group.length ? done + " de " + group.length + " pruebas" : "Cierre e informe"));
      li.append(symbol, textWrap);
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
    panel.hidden = values.length === 0;
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
    badge.textContent = result.ok ? "Comprobación correcta" : "Revisar";
    badge.className = "wizard-result-badge " + (result.ok ? "is-success" : "is-error");
    $("wizardAutomaticSummary").textContent = result.summary || "";
    const list = $("wizardAutomaticDetails");
    list.replaceChildren();
    (result.details || []).forEach((item) => {
      const li = makeNode("li", "wizard-check-result " + (item.ok ? "is-success" : item.level === "warning" ? "is-warning" : "is-error"));
      li.append(makeNode("span", "wizard-check-symbol", item.ok ? "✓" : item.level === "warning" ? "!" : "×"));
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
    if (!step.needsManual || !record.opened) return false;
    if (step.checkKey && !record.autoChecked) return false;
    return true;
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
      button.disabled = outcome === "passed" && step.checkKey && record.autoResult && !record.autoResult.ok;
    });
    if (step.checkKey && record.autoResult && !record.autoResult.ok) {
      $("wizardManualOutcomeStatus").textContent = "La comprobación automática detectó una incidencia. No se puede marcar este paso como correcto; registrá el fallo o indicá que no pudiste comprobarlo.";
    }
  }

  function canAdvance(step, record) {
    if (step.type === "intro") return true;
    if (step.type === "summary") return false;
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
    $("wizardCompletionMessage").textContent = summary;
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
      row.append(icon, copy);
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
      $("wizardActionLink").href = step.link;
      $("wizardActionLink").textContent = step.linkLabel || "Abrir módulo en otra pestaña ↗";
      $("wizardActionTitle").textContent = step.actionTitle || "Abrí el módulo que vamos a probar";
      $("wizardActionDescription").textContent = step.checkKey
        ? "Ejecutá la comprobación de lectura y abrí el módulo. La guía seguirá abierta en esta pestaña."
        : "Se abrirá en otra pestaña. Seguí los pasos indicados, después volvé acá y registrá el resultado.";
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
    $("wizardFooterHint").textContent = step.type === "intro"
      ? "No hace falta marcar casillas. Empezá y seguí una indicación por vez."
      : step.type === "summary"
        ? "El informe registra lo comprobado, lo que falló y lo que quedó pendiente."
        : step.type === "auto"
          ? "Esta comprobación es de solo lectura. No toca el inventario ni inicia un escaneo."
          : manualOutcomeReady(step, record)
            ? "Elegí un resultado para habilitar el siguiente paso."
            : step.checkKey
              ? "1. Comprobá la API.  2. Abrí el módulo en otra pestaña.  3. Volvé y registrá el resultado."
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
    return {
      ok,
      details,
      summary: ok
        ? "El servicio, el dispositivo ficticio y la lectura sintética están disponibles. No se ejecutó un escaneo."
        : "El servidor respondió parcialmente, pero falta una condición necesaria para una prueba aislada. Revisá las filas y la ayuda de preparación antes de continuar."
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
    const ok = graphResponse.ok && graph.evidence_available !== false && nodes.length >= 3 && hasDevice;
    return {
      ok,
      summary: ok
        ? "La API devolvió el grafo guardado en modo de lectura. Ahora compará estos datos con la vista de Mapa de red."
        : "La respuesta no contiene toda la evidencia sintética esperada. Revisá la lectura seleccionada antes de marcar el paso.",
      details: [
        { label: "Lectura seleccionada", value: "ID " + scan.id + " · synthetic-test-fixture", ok: true },
        { label: "Grafo", value: graphResponse.ok ? nodes.length + " nodos · " + edges.length + " enlaces" : "HTTP " + graphResponse.status, ok: graphResponse.ok && nodes.length >= 3 },
        { label: "Dispositivo de prueba", value: hasDevice ? DEVICE_IP + " presente en el grafo" : DEVICE_IP + " no aparece en los nodos", ok: hasDevice },
        { label: "Evidencia", value: graph.evidence_available === false ? "La API indica que no hay evidencia disponible" : "Consulta de solo lectura; no se inició un escaneo", ok: graph.evidence_available !== false }
      ]
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
    const ok = mapResponse.ok && worldResponse.ok;
    const details = [
      { label: "API del mapa", value: mapResponse.ok ? "HTTP " + mapResponse.status + " · " + eventCount + " evento(s) con IP destino" : "No disponible (HTTP " + mapResponse.status + ")", ok: mapResponse.ok },
      { label: "Cartografía incluida", value: worldResponse.ok ? "Recurso local cargado (HTTP " + worldResponse.status + ")" : "No se pudo cargar el archivo cartográfico", ok: worldResponse.ok },
      { label: "Base GeoLite2-City", value: cityStatus === "available" ? "Disponible: la interfaz puede ubicar las IP cubiertas" : "No disponible: es válido mostrar la tabla sin inventar marcadores", ok: true, level: cityStatus === "available" ? "success" : "warning" }
    ];
    return {
      ok,
      details,
      summary: ok
        ? "El servicio y el mapa base responden. El estado de GeoIP indica si hay cobertura geográfica real, no si el mapa debe inventar coordenadas."
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
      else throw new Error("No hay una comprobación asociada a este paso.");
      record.autoChecked = true;
      record.autoResult = {
        ok: Boolean(result.ok),
        summary: result.summary,
        details: result.details || [],
        checkedAt: new Date().toISOString()
      };
      record.checking = false;
      if (step.type === "auto") {
        record.outcome = result.ok ? "passed" : "failed";
        record.resultTimestamp = new Date().toISOString();
      }
      saveState();
      renderStep();
      if (result.ok) showMessage("Comprobación finalizada. Revisá los datos observados y seguí la indicación del paso.", "success");
      else {
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
    const lines = [
      "NetSentinel — Informe del asistente de aceptación",
      "Fecha de cierre: " + new Intl.DateTimeFormat("es-AR", { dateStyle: "long", timeStyle: "short" }).format(date),
      "Modo: laboratorio local con datos sintéticos.",
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

  function advance() {
    const step = steps[state.currentStep];
    const record = step.track ? recordFor(step) : null;
    if (!canAdvance(step, record || {})) {
      showMessage("Registrá el resultado de este paso antes de continuar.", "warning");
      return;
    }
    state.currentStep = Math.min(steps.length - 1, state.currentStep + 1);
    if (steps[state.currentStep].type === "summary" && !state.finishedAt) state.finishedAt = new Date().toISOString();
    saveState();
    renderStep();
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  function goBack() {
    state.currentStep = Math.max(0, state.currentStep - 1);
    saveState();
    renderStep();
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

  $("wizardActionLink").addEventListener("click", () => {
    const step = steps[state.currentStep];
    if (!step.link || !step.track) return;
    const record = recordFor(step);
    record.opened = true;
    saveState();
    renderManualResult(step, record);
    $("wizardFooterHint").textContent = step.checkKey && !record.autoChecked
      ? "Volvé a esta pestaña, pulsá «Comprobar ahora» y después registrá el resultado."
      : "Volvé a esta pestaña cuando termines de revisar el módulo.";
    showMessage("La guía queda abierta aquí. Cuando termines en la otra pestaña, volvé y elegí el resultado observado.", "success");
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
    URL.revokeObjectURL(url);
    showMessage("Informe .txt descargado en tu computadora.", "success");
  });

  renderStep();
})();
