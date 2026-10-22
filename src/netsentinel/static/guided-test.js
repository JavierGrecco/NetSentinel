/* Recorrido de pruebas local: el progreso es una ayuda visual, no un informe de aprobación automática. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const STORAGE_KEY = "netsentinel.guided-test.progress.v1";
  const checks = Array.from(document.querySelectorAll("[data-guided-step]"));
  const total = checks.length;

  function readProgress() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function writeProgress(completedAt) {
    const progress = {};
    checks.forEach((input) => { progress[input.dataset.guidedStep] = input.checked; });
    if (completedAt) progress._completedAt = completedAt;
    try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(progress)); } catch (_) { /* El progreso seguirá disponible durante esta visita. */ }
  }

  function updateProgress(save) {
    const completed = checks.filter((input) => input.checked).length;
    const percentage = total ? Math.round((completed / total) * 100) : 0;
    const isComplete = total > 0 && completed === total;
    const savedProgress = readProgress();
    const completedAt = isComplete
      ? (savedProgress._completedAt || new Date().toISOString())
      : null;

    $("guidedProgressCount").textContent = completed + " de " + total + " pasos";
    $("guidedProgressFill").style.width = percentage + "%";
    $("guidedProgressBar").setAttribute("aria-valuemax", String(total));
    $("guidedProgressBar").setAttribute("aria-valuenow", String(completed));
    $("guidedProgressText").textContent = isComplete
      ? "PRUEBA GUIADA FINALIZADA. Marcaste todos los pasos; el resultado es una declaración manual, no una aprobación automática."
      : "Completaste " + percentage + "%. Marcá cada paso solo después de comprobarlo en la aplicación.";

    $("guidedCompletionPanel").hidden = !isComplete;
    if (isComplete) {
      const completionDate = new Intl.DateTimeFormat("es-AR", {
        dateStyle: "long",
        timeStyle: "short"
      }).format(new Date(completedAt));
      $("guidedCompletionTimestamp").textContent = "Cierre registrado en este navegador: " + completionDate + ".";
      $("guidedFinalStatus").textContent = "✅ PRUEBA GUIADA FINALIZADA: " + completed + " de " + total + " pasos marcados. Revisá y compartí el resumen de resultados.";
    } else {
      $("guidedFinalStatus").textContent = "Recorrido pendiente: faltan " + (total - completed) + " pasos. No marques una prueba que no pudiste verificar.";
    }

    if (save || (isComplete && !savedProgress._completedAt)) writeProgress(completedAt);
  }

  function announce(target, message, kind) {
    target.textContent = message;
    target.classList.remove("is-success", "is-error");
    if (kind) target.classList.add(kind);
  }

  async function copyText(text) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      await navigator.clipboard.writeText(text);
      return;
    }
    const field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.append(field);
    field.select();
    const copied = document.execCommand("copy");
    field.remove();
    if (!copied) throw new Error("El navegador no permitió copiar automáticamente. Seleccioná el bloque y copialo manualmente.");
  }

  async function checkApi(url, target, label, summarize) {
    target.textContent = "Consultando " + label + "…";
    target.classList.remove("is-success", "is-error");
    try {
      const response = await fetch(url, { cache: "no-store", credentials: "same-origin" });
      if (!response.ok) throw new Error("Respuesta HTTP " + response.status);
      const payload = await response.json();
      const detail = summarize(payload);
      announce(target, label + ": disponible. " + detail, "is-success");
    } catch (error) {
      announce(target, label + ": no se pudo comprobar. " + (error && error.message ? error.message : "Error de conexión local."), "is-error");
    }
  }

  checks.forEach((input) => {
    input.checked = Boolean(readProgress()[input.dataset.guidedStep]);
    input.addEventListener("change", () => updateProgress(true));
  });

  $("resetGuidedProgress").addEventListener("click", () => {
    checks.forEach((input) => { input.checked = false; });
    updateProgress(true);
  });

  $("copySetupCommand").addEventListener("click", async () => {
    try {
      await copyText($("setupCommand").textContent);
      announce($("copyCommandStatus"), "Comandos copiados. Pegalos en una terminal situada en la raíz del repositorio, después de detener una instancia que esté usando el puerto local.", "is-success");
    } catch (error) {
      announce($("copyCommandStatus"), error && error.message ? error.message : "No se pudieron copiar los comandos.", "is-error");
    }
  });

  $("copyEvidenceChangeCommand").addEventListener("click", async () => {
    try {
      await copyText($("evidenceChangeCommand").textContent);
      announce($("evidenceChangeStatus"), "Comando copiado. Ejecutalo en una segunda terminal que comparta NETSENTINEL_DATA_DIR con la app en marcha.", "is-success");
    } catch (error) {
      announce($("evidenceChangeStatus"), error && error.message ? error.message : "No se pudo copiar el comando.", "is-error");
    }
  });

  $("checkMapApi").addEventListener("click", () => {
    checkApi("/api/geolocation/map?limit=1", $("mapApiStatus"), "API del mapa", (payload) => {
      const summary = payload && payload.summary ? payload.summary : {};
      const databases = payload && payload.databases ? payload.databases : {};
      const events = Number(summary.events_with_destination_ip || 0);
      const city = databases.city_status || "sin estado";
      return events + " evento(s) con IP destino; base GeoLite2-City: " + city + ".";
    });
  });

  $("checkTopologyApi").addEventListener("click", async () => {
    const target = $("topologyApiStatus");
    target.textContent = "Buscando la lectura sintética guardada…";
    target.classList.remove("is-success", "is-error");
    try {
      const scansResponse = await fetch("/api/scans?limit=100", { cache: "no-store", credentials: "same-origin" });
      if (!scansResponse.ok) throw new Error("No se pudo consultar el historial (HTTP " + scansResponse.status + ").");
      const scans = await scansResponse.json();
      if (!Array.isArray(scans)) throw new Error("El historial no devolvió una lista de lecturas.");
      const scan = scans.find((item) => item && item.source === "synthetic-test-fixture");
      if (!scan) throw new Error("No se encontró la lectura sintética. Prepará una base nueva con --include-topology.");
      const graphResponse = await fetch("/api/scans/" + encodeURIComponent(scan.id) + "/topology", { cache: "no-store", credentials: "same-origin" });
      if (!graphResponse.ok) throw new Error("La topología respondió HTTP " + graphResponse.status + ".");
      const graph = await graphResponse.json();
      const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
      const edges = Array.isArray(graph.edges) ? graph.edges : [];
      if (graph.evidence_available === false) throw new Error("La lectura no tiene evidencia disponible; revisá el fixture y las migraciones.");
      if (nodes.length < 3 || !JSON.stringify(nodes).includes("192.168.56.20")) {
        throw new Error("La API respondió, pero no encontró los dispositivos sintéticos esperados.");
      }
      announce(target, "Topología disponible: lectura sintética #" + scan.id + "; " + nodes.length + " nodos y " + edges.length + " enlaces. La consulta fue de solo lectura.", "is-success");
    } catch (error) {
      announce(target, error && error.message ? error.message : "No se pudo verificar la topología.", "is-error");
    }
  });

  $("checkForensicsApi").addEventListener("click", () => {
    checkApi("/api/forensics/cases?limit=1", $("forensicsApiStatus"), "API de Forense", (payload) => {
      const cases = Array.isArray(payload && payload.items) ? payload.items.length : 0;
      return "consulta de casos completada; " + cases + " caso(s) devuelto(s) en esta muestra.";
    });
  });

  $("copyGuidedResults").addEventListener("click", async () => {
    const completed = checks.filter((input) => input.checked).length;
    const stored = readProgress();
    const completedAt = stored._completedAt || new Date().toISOString();
    const formattedDate = new Intl.DateTimeFormat("es-AR", {
      dateStyle: "long",
      timeStyle: "short"
    }).format(new Date(completedAt));
    const lines = [
      "NetSentinel — Resultado de la prueba guiada",
      "Pasos marcados: " + completed + " de " + total,
      "Cierre: " + formattedDate,
      "Resultado autodeclarado por quien realizó la prueba; no equivale a certificación ni aprobación automática.",
      "",
      ...checks.map((input) => (input.checked ? "[x] " : "[ ] ") + input.closest("label").innerText.replace(/\s+/g, " ").trim())
    ];
    try {
      await copyText(lines.join("\n"));
      announce($("guidedCompletionCopyStatus"), "Resumen copiado. Revisá los pasos pendientes antes de compartirlo.", "is-success");
    } catch (error) {
      announce($("guidedCompletionCopyStatus"), error && error.message ? error.message : "No se pudo copiar el resumen.", "is-error");
    }
  });

  updateProgress(false);
})();