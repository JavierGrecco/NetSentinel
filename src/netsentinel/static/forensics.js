/* Interfaz de casos: usa la API local, no procesa archivos ni captura secretos. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const state = { cases: [], selectedCaseId: null, selectedCase: null, evidence: [], audit: [], busy: false };
  const sourceLabels = {
    disk_image: "Imagen de disco", file_copy: "Copia de archivo",
    browser_export: "Exportación de navegador", email_export: "Exportación de correo",
    network_log: "Registro de red", other: "Otro tipo de fuente"
  };
  const actionLabels = {
    case_opened: "Caso abierto",
    case_closed: "Caso cerrado",
    evidence_registered: "Evidencia registrada",
    evidence_custody_transferred: "Transferencia de custodia registrada",
    evidence_hash_compared: "Hash comparado",
    evidence_hash_check_failed: "Falló la comparación del hash"
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function setStatus(message, kind = "info") {
    const status = $("forensicWorkspaceStatus");
    if (!status) return;
    status.textContent = message;
    status.dataset.kind = kind;
  }
  function operatorName() {
    const value = $("forensicOperator").value.trim();
    if (!value) {
      setStatus("Completá el nombre de quien realiza la operación antes de continuar.", "error");
      $("forensicOperator").focus();
      return null;
    }
    return value;
  }
  async function api(url, options = {}) {
    let response;
    try {
      response = await fetch(url, {
        ...options, cache: "no-store", credentials: "same-origin",
        headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) }
      });
    } catch (_) {
      throw new Error("No se pudo contactar con el servidor local. Verificá que NetSentinel siga abierto y volvé a intentar.");
    }
    let body = null;
    try { body = await response.json(); } catch (_) { body = null; }
    if (!response.ok) {
      const detail = body && body.detail;
      const message = Array.isArray(detail)
        ? detail.map((item) => item && item.msg ? item.msg : "Revisá los campos indicados.").join(" ")
        : typeof detail === "string" ? detail
          : detail && typeof detail.message === "string"
            ? (detail.code ? detail.code + ": " + detail.message : detail.message)
            : "La operación no pudo completarse. Volvé a intentarlo.";
      throw new Error(message);
    }
    return body;
  }
  function addMetaLine(container, label, value) {
    const span = element("span");
    span.append(element("strong", "", label + ": "));
    span.append(document.createTextNode(value || "No informado"));
    container.append(span);
  }
  function renderCaseList() {
    const list = $("forensicCaseList");
    list.replaceChildren();
    $("forensicCaseCount").textContent = String(state.cases.length);
    if (!state.cases.length) {
      list.append(element("p", "forensic-empty-inline", "Todavía no hay casos. Abrí uno para empezar a documentar el trabajo."));
      return;
    }
    state.cases.forEach((item) => {
      const button = element("button", "forensic-case-item");
      button.type = "button";
      button.setAttribute("aria-pressed", String(item.id === state.selectedCaseId));
      button.append(element("span", "forensic-case-item-title", item.title));
      button.append(element("span", "forensic-case-item-number", item.case_number));
      const meta = element("span", "forensic-case-item-meta");
      meta.append(element("span", "", item.status === "open" ? "Abierto" : "Cerrado"));
      meta.append(element("span", "", String(item.evidence_count) + (item.evidence_count === 1 ? " elemento" : " elementos")));
      button.append(meta);
      button.addEventListener("click", () => selectCase(item.id));
      list.append(button);
    });
  }
  function renderCaseSummary() {
    const current = state.selectedCase;
    $("forensicCaseEmpty").hidden = Boolean(current);
    $("forensicSelectedCase").hidden = !current;
    $("exportForensicAuditManifest").disabled = !current || state.busy;
    $("exportForensicCaseManifest").disabled = !current || state.busy;
    if (!current) return;
    $("forensicSelectedCaseTitle").textContent = current.title;
    $("forensicSelectedCaseNumber").textContent = current.case_number;
    $("forensicSelectedCaseStatus").textContent = current.status === "open" ? "Abierto" : "Cerrado";
    $("forensicSelectedCaseStatus").dataset.status = current.status;
    $("forensicSelectedAuthority").textContent = current.authority_reference;
    $("forensicSelectedExaminer").textContent = current.examiner;
    $("forensicSelectedObjective").textContent = current.objective;
    $("forensicSelectedScope").textContent = current.scope;
    const closed = current.status === "closed";
    $("closeForensicCase").hidden = closed;
    $("newForensicEvidenceDetails").hidden = closed;
    $("forensicEvidenceForm").querySelectorAll("input,select,textarea,button").forEach((control) => {
      control.disabled = closed;
    });
  }
  function createIntegrityCheckPanel(item) {
    const panel = element("details", "forensic-verify-panel");
    panel.append(element("summary", "", "Comparar con una copia de trabajo"));

    const warning = element(
      "p",
      "forensic-verify-warning",
      "Elegí una copia autorizada, no el soporte original. La lectura puede cambiar metadatos de acceso. Solo se consulta el nombre dentro de la carpeta forensics-working-copies del directorio de datos; la ubicación no se guarda."
    );
    const form = element("form", "forensic-verify-form");
    const pathLabel = element("label", "", "Nombre del archivo de la copia");
    const pathInput = document.createElement("input");
    pathInput.type = "text";
    pathInput.name = "source_name";
    pathInput.id = "forensic-copy-name-" + item.id;
    pathInput.required = true;
    pathInput.maxLength = 255;
    pathInput.autocomplete = "off";
    pathInput.spellcheck = false;
    pathInput.placeholder = "Ej.: netsentinel-forensic-sample.bin";
    pathLabel.htmlFor = pathInput.id;

    const confirmation = element("label", "forensic-verify-confirm");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "confirm_working_copy";
    checkbox.required = true;
    confirmation.append(checkbox);
    confirmation.append(document.createTextNode(
      " Confirmo que es una copia de trabajo autorizada y no el soporte original."
    ));

    const button = element("button", "primary", "Calcular y comparar SHA-256");
    button.type = "submit";
    form.append(pathLabel, pathInput, confirmation, button);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (state.busy) return;
      if (!state.selectedCase || state.selectedCase.status !== "open") {
        setStatus("El caso está cerrado. No se pueden iniciar nuevas comprobaciones.", "error");
        return;
      }
      const actor = operatorName();
      if (!actor || !form.reportValidity()) return;

      state.busy = true;
      setStatus("Leyendo la copia elegida y comparando su SHA-256. No cierres la aplicación…");
      try {
        const result = await api(
          "/api/forensics/cases/" + encodeURIComponent(state.selectedCaseId)
            + "/evidence/" + encodeURIComponent(item.id) + "/verify-hash",
          {
            method: "POST",
            body: JSON.stringify({
              source_name: pathInput.value.trim(),
              actor,
              confirm_working_copy: checkbox.checked,
            }),
          }
        );
        state.busy = false;
        await loadCases();
        if (result.status === "match") {
          setStatus(
            "La copia coincide con el SHA-256 informado por la fuente. Esto verifica la coincidencia con ese valor, no la autenticidad del origen.",
            "success"
          );
        } else {
          setStatus(
            "El SHA-256 calculado no coincide con el informado. Revisá que sea la copia correcta y confirmá el valor de referencia; la diferencia por sí sola no demuestra una manipulación.",
            "warning"
          );
        }
      } catch (error) {
        state.busy = false;
        await loadCases();
        setStatus(error.message, "error");
      } finally {
        state.busy = false;
      }
    });
    panel.append(warning, form);
    return panel;
  }

  function addCustodyField(form, itemId, labelText, name, value, options = {}) {
    const wrapper = element("div", options.wide ? "forensic-field forensic-field-wide" : "forensic-field");
    const id = "forensic-custody-" + name + "-" + itemId;
    const label = element("label", "", labelText);
    label.htmlFor = id;
    let control;
    if (options.multiline) {
      control = document.createElement("textarea");
      control.rows = options.rows || 2;
    } else {
      control = document.createElement("input");
      control.type = options.type || "text";
    }
    control.id = id;
    control.name = name;
    control.value = value || "";
    control.maxLength = options.maxLength || 500;
    control.required = options.required !== false;
    if (options.pattern) control.pattern = options.pattern;
    if (options.placeholder) control.placeholder = options.placeholder;
    if (options.autocomplete) control.autocomplete = options.autocomplete;
    wrapper.append(label, control);
    if (options.help) wrapper.append(element("span", "", options.help));
    form.append(wrapper);
    return control;
  }

  function createCustodyTransferPanel(item) {
    const panel = element("details", "forensic-transfer-panel");
    panel.append(element("summary", "", "Registrar transferencia de custodia"));
    const intro = element(
      "p",
      "forensic-evidence-description",
      "Registrá la entrega real con datos observados. La hora de la transferencia se conserva aparte de la hora en que NetSentinel registra el evento. El nombre del operador es declarado, no autenticado."
    );
    const form = element("form", "forensic-form-grid forensic-custody-form");
    const previousTransfer = state.audit.find((event) =>
      event.action === "evidence_custody_transferred" && event.evidence_id === item.id
    );
    const knownSender = previousTransfer && previousTransfer.details
      ? previousTransfer.details.to_custodian
      : item.received_from;
    addCustodyField(form, item.id, "Persona que entrega", "from_custodian", knownSender, {
      maxLength: 160,
      autocomplete: "off",
      help: "Se propone el último destinatario registrado o, si no hay transferencias, la fuente que entregó el elemento."
    });
    addCustodyField(form, item.id, "Persona que recibe", "to_custodian", "", {
      maxLength: 160,
      autocomplete: "off"
    });
    addCustodyField(form, item.id, "Fecha/hora de la entrega (ISO-8601 con offset)", "transferred_at_original",
      currentLocalTimestampWithOffset(), {
        maxLength: 64,
        autocomplete: "off",
        pattern: "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})",
        help: "Es la fecha/hora declarada de la entrega, no el sello de tiempo del servidor."
      });
    addCustodyField(form, item.id, "Motivo de la transferencia", "purpose", "", {
      maxLength: 500,
      multiline: true,
      rows: 2,
      wide: true,
      placeholder: "Ej.: entrega para examen autorizado"
    });
    addCustodyField(form, item.id, "Método de entrega", "delivery_method", "", {
      maxLength: 160,
      placeholder: "Ej.: entrega presencial en sobre sellado"
    });
    addCustodyField(form, item.id, "Estado del elemento o embalaje", "condition_notes", "", {
      maxLength: 500,
      required: false,
      multiline: true,
      wide: true,
      help: "Opcional. Describí el estado observado; no afirmes algo que no hayas comprobado."
    });
    addCustodyField(form, item.id, "Identificador del precinto", "seal_identifier", "", {
      maxLength: 120,
      required: false,
      placeholder: "Opcional, si existe"
    });

    const actions = element("div", "forensic-form-actions");
    const submit = element("button", "primary", "Registrar transferencia");
    submit.type = "submit";
    actions.append(submit);
    form.append(actions);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (state.busy || !state.selectedCaseId) return;
      if (!state.selectedCase || state.selectedCase.status !== "open") {
        setStatus("El caso está cerrado. No se pueden registrar nuevas transferencias.", "error");
        return;
      }
      const actor = operatorName();
      if (!actor || !form.reportValidity()) return;
      const caseId = state.selectedCaseId;
      const values = Object.fromEntries(new FormData(form).entries());
      values.actor = actor;
      for (const key of ["condition_notes", "seal_identifier"]) {
        values[key] = values[key] || null;
      }

      state.busy = true;
      submit.disabled = true;
      setStatus("Registrando la transferencia y encadenándola a la auditoría…");
      try {
        const result = await api(
          "/api/forensics/cases/" + encodeURIComponent(caseId)
            + "/evidence/" + encodeURIComponent(item.id) + "/custody-transfers",
          { method: "POST", body: JSON.stringify(values) }
        );
        state.busy = false;
        await selectCase(caseId);
        setStatus(
          "Transferencia registrada para " + item.evidence_number
            + ". Revisá la continuidad y el estado de integridad de la auditoría.",
          result.integrity_status === "valid" ? "success" : "error"
        );
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        state.busy = false;
        submit.disabled = false;
      }
    });
    panel.append(intro, form);
    return panel;
  }

  function renderEvidence() {
    const list = $("forensicEvidenceList");
    list.replaceChildren();
    if (!state.evidence.length) {
      list.append(element("p", "forensic-empty-inline", "Este caso todavía no tiene elementos registrados."));
      return;
    }
    state.evidence.forEach((item) => {
      const card = element("article", "forensic-evidence-card");
      const header = element("div", "forensic-evidence-card-head");
      const left = element("div");
      left.append(element("span", "forensic-evidence-number", item.evidence_number));
      left.append(element("h4", "", item.label));
      header.append(left);
      header.append(element("span", "forensic-hash-state",
        item.hash_status === "reported" ? "Hash informado · no verificado" : "Sin hash informado"));
      card.append(header);
      card.append(element("p", "forensic-evidence-description", item.source_description));
      const meta = element("div", "forensic-evidence-meta");
      addMetaLine(meta, "Tipo", sourceLabels[item.source_type] || "Otro tipo de fuente");
      addMetaLine(meta, "Nombre original", item.original_name);
      addMetaLine(meta, "Entregado por", item.received_from);
      addMetaLine(meta, "Fecha de recepción", item.received_at_original + " · " + item.received_timezone);
      addMetaLine(meta, "Tamaño", item.size_bytes === null ? "No informado" : Number(item.size_bytes).toLocaleString() + " bytes");
      addMetaLine(meta, "Registrado en NetSentinel", item.created_at);
      const latestTransfer = state.audit.find((event) =>
        event.action === "evidence_custody_transferred" && event.evidence_id === item.id
      );
      if (latestTransfer && latestTransfer.details) {
        addMetaLine(meta, "Último destinatario registrado", latestTransfer.details.to_custodian);
        addMetaLine(meta, "Fecha declarada de transferencia", latestTransfer.details.transferred_at_original);
        if (latestTransfer.integrity_status !== "valid") {
          card.append(element("p", "forensic-check-summary forensic-check-failed",
            "Advertencia: el evento de transferencia no tiene integridad válida en la cadena de auditoría."));
        }
      } else {
        addMetaLine(meta, "Historial de transferencias", "No hay transferencias posteriores registradas");
      }
      card.append(meta);
      if (item.reported_sha256) {
        card.append(element("code", "forensic-hash-value", "SHA-256 declarado: " + item.reported_sha256));
        card.append(element("p", "forensic-evidence-description",
          "Origen declarado: " + (item.hash_source || "No informado") + ". Este valor no se considera verificado hasta compararlo con una copia de trabajo."));
        if (item.last_integrity_check_status) {
          const summaryText = {
            match: "Última comparación: coincide con el hash declarado.",
            mismatch: "Última comparación: no coincide con el hash declarado.",
            failed: "Última comprobación: no se pudo leer la copia o completar la operación."
          };
          const summary = element(
            "p",
            "forensic-check-summary forensic-check-" + item.last_integrity_check_status,
            summaryText[item.last_integrity_check_status] || "Hay una comprobación anterior."
          );
          if (item.last_integrity_check_at) {
            summary.append(document.createTextNode(" " + item.last_integrity_check_at));
          }
          card.append(summary);
          if (item.last_calculated_sha256) {
            card.append(element("code", "forensic-hash-value", "SHA-256 calculado: " + item.last_calculated_sha256));
          }
        }
        if (state.selectedCase && state.selectedCase.status === "open") {
          card.append(createIntegrityCheckPanel(item));
        } else {
          card.append(element("p", "forensic-evidence-description",
            "El caso está cerrado; se conservan las comprobaciones anteriores, pero no se permiten nuevas operaciones."));
        }
      }
      if (state.selectedCase && state.selectedCase.status === "open") {
        card.append(createCustodyTransferPanel(item));
      } else {
        card.append(element("p", "forensic-evidence-description",
          "El caso está cerrado; se conservan las transferencias anteriores, pero no se permiten nuevas operaciones."));
      }
      list.append(card);
    });
  }
  function renderAudit() {
    const list = $("forensicAuditList");
    list.replaceChildren();
    if (!state.audit.length) {
      list.append(element("li", "forensic-empty-inline", "Todavía no hay operaciones registradas."));
      return;
    }
    state.audit.forEach((item) => {
      const row = element("li", "forensic-audit-item");
      row.append(element("span", "forensic-audit-dot"));
      const copy = element("div");
      copy.append(element("strong", "", actionLabels[item.action] || item.action));
      copy.append(element("p", "", item.actor + " · " + item.occurred_at));
      const integrityStatus = item.integrity_status || "missing";
      const integrityMessage = integrityStatus === "valid"
        ? "Integridad del evento: válida"
        : integrityStatus === "missing"
          ? "Integridad del evento: falta la huella de auditoría"
          : "Integridad del evento: inválida; revisar la cadena";
      copy.append(element(
        "p",
        "forensic-audit-integrity forensic-check-" + integrityStatus,
        integrityMessage
      ));
      const detailLabels = {
        evidence_number: "Elemento",
        from_custodian: "Entrega",
        to_custodian: "Recibe",
        transferred_at_original: "Fecha/hora declarada",
        purpose: "Motivo",
        delivery_method: "Método de entrega",
        condition_notes: "Estado",
        seal_identifier: "Precinto"
      };
      const detailEntries = item.details ? Object.entries(item.details) : [];
      const details = detailEntries
        .filter(([, value]) => value !== null && value !== undefined && value !== "")
        .map(([key, value]) => (detailLabels[key] || key) + ": " + String(value))
        .join(" · ");
      if (details) copy.append(element("p", "", details));
      row.append(copy);
      list.append(row);
    });
  }
  async function selectCase(caseId) {
    if (state.busy) return;
    state.selectedCaseId = caseId;
    renderCaseList();
    setStatus("Cargando los datos del caso…");
    try {
      const results = await Promise.all([
        api("/api/forensics/cases/" + encodeURIComponent(caseId)),
        api("/api/forensics/cases/" + encodeURIComponent(caseId) + "/evidence"),
        api("/api/forensics/cases/" + encodeURIComponent(caseId) + "/audit?limit=200")
      ]);
      state.selectedCase = results[0];
      state.evidence = results[1].items || [];
      state.audit = results[2].items || [];
      renderCaseSummary();
      renderEvidence();
      renderAudit();
      renderCaseList();
      setStatus("Caso " + state.selectedCase.case_number + " seleccionado. Los metadatos están guardados en esta computadora.");
    } catch (error) {
      state.selectedCase = null;
      state.evidence = [];
      state.audit = [];
      renderCaseSummary();
      renderCaseList();
      setStatus(error.message, "error");
    }
  }
  async function loadCases() {
    if (state.busy) return;
    setStatus("Consultando los casos registrados…");
    try {
      const result = await api("/api/forensics/cases?limit=200");
      state.cases = result.items || [];
      if (!state.cases.some((item) => item.id === state.selectedCaseId)) {
        state.selectedCaseId = state.cases.length ? state.cases[0].id : null;
      }
      renderCaseList();
      if (state.selectedCaseId) {
        await selectCase(state.selectedCaseId);
      } else {
        state.selectedCase = null;
        state.evidence = [];
        state.audit = [];
        renderCaseSummary();
        renderEvidence();
        renderAudit();
        setStatus("Todavía no hay casos. Usá «Abrir un caso» para registrar la autorización y el alcance.");
      }
    } catch (error) {
      renderCaseList();
      setStatus(error.message, "error");
    }
  }
  function currentLocalTimestampWithOffset() {
    const now = new Date();
    const localText = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 19);
    const offset = -now.getTimezoneOffset();
    const sign = offset >= 0 ? "+" : "-";
    const absolute = Math.abs(offset);
    const hours = String(Math.floor(absolute / 60)).padStart(2, "0");
    const minutes = String(absolute % 60).padStart(2, "0");
    return localText + sign + hours + ":" + minutes;
  }
  function installRoadmapFilters() {
    const cards = Array.from(document.querySelectorAll(".forensic-card[data-phase]"));
    const buttons = Array.from(document.querySelectorAll("[data-phase-filter]"));
    const status = $("forensicFilterStatus");
    if (!cards.length || !buttons.length || !status) return;
    const labels = {
      all: "Se muestran las seis etapas previstas.",
      first: "Se muestran las funciones previstas para la primera entrega.",
      later: "Se muestran las funciones previstas para etapas posteriores."
    };
    function applyFilter(phase) {
      const selected = labels[phase] ? phase : "all";
      cards.forEach((card) => {
        card.hidden = selected === "all" ? false : selected === "first" ? card.dataset.phase !== "first" : card.dataset.phase !== "later";
      });
      buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.phaseFilter === selected)));
      status.textContent = labels[selected];
    }
    buttons.forEach((button) => button.addEventListener("click", () => applyFilter(button.dataset.phaseFilter)));
  }

  function installManifestExport(buttonId, endpointSuffix, filename, preparingMessage, errorMessage, successMessage) {
    const button = $(buttonId);
    if (!button) return;
    button.addEventListener("click", async () => {
      const caseId = state.selectedCaseId;
      if (!caseId || state.busy) return;
      const exportButtons = [
        $("exportForensicAuditManifest"),
        $("exportForensicCaseManifest")
      ].filter(Boolean);
      state.busy = true;
      exportButtons.forEach((item) => { item.disabled = true; });
      setStatus(preparingMessage);
      let objectUrl = null;
      try {
        const response = await fetch(
          "/api/forensics/cases/" + encodeURIComponent(caseId) + endpointSuffix,
          { cache: "no-store", credentials: "same-origin" }
        );
        if (!response.ok) {
          let message = errorMessage;
          try {
            const body = await response.json();
            if (typeof body.detail === "string") message = body.detail;
          } catch (_) { /* La respuesta de error puede no contener JSON. */ }
          throw new Error(message);
        }
        const blob = await response.blob();
        objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        link.hidden = true;
        document.body.append(link);
        link.click();
        link.remove();
        // Capturá la URL antes de limpiar la variable que usa el bloque finally.
        const downloadUrl = objectUrl;
        window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
        objectUrl = null;
        setStatus(successMessage, "success");
      } catch (error) {
        setStatus(error.message || errorMessage, "error");
      } finally {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        state.busy = false;
        exportButtons.forEach((item) => { item.disabled = !state.selectedCaseId; });
      }
    });
  }
  function installCaseForms() {
    const caseDetails = $("newForensicCaseDetails");
    const evidenceDetails = $("newForensicEvidenceDetails");
    const caseForm = $("forensicCaseForm");
    const evidenceForm = $("forensicEvidenceForm");

    $("refreshForensicCases").addEventListener("click", loadCases);
    $("cancelForensicCase").addEventListener("click", () => {
      caseForm.reset();
      caseDetails.open = false;
    });
    $("cancelForensicEvidence").addEventListener("click", () => {
      evidenceForm.reset();
      evidenceDetails.open = false;
      $("forensicTimezone").value = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      $("forensicReceivedAt").value = currentLocalTimestampWithOffset();
    });

    caseForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (state.busy) return;
      const actor = operatorName();
      if (!actor || !caseForm.reportValidity()) return;
      const payload = Object.fromEntries(new FormData(caseForm).entries());
      payload.actor = actor;
      state.busy = true;
      setStatus("Guardando el caso y su registro de apertura…");
      try {
        const created = await api("/api/forensics/cases", { method: "POST", body: JSON.stringify(payload) });
        caseForm.reset();
        caseDetails.open = false;
        state.selectedCaseId = created.id;
        state.busy = false;
        await loadCases();
        setStatus("Caso " + created.case_number + " registrado. Revisá que la autorización y el alcance estén bien escritos.", "success");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        state.busy = false;
      }
    });

    evidenceForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (state.busy || !state.selectedCaseId || !state.selectedCase) return;
      if (state.selectedCase.status !== "open") {
        setStatus("El caso está cerrado. Abrí otro caso para registrar nueva evidencia.", "error");
        return;
      }
      const actor = operatorName();
      if (!actor || !evidenceForm.reportValidity()) return;
      const values = Object.fromEntries(new FormData(evidenceForm).entries());
      const payload = {
        label: values.label,
        source_type: values.source_type,
        original_name: values.original_name || null,
        source_description: values.source_description,
        received_from: values.received_from,
        received_at_original: values.received_at_original.trim(),
        received_timezone: values.received_timezone,
        size_bytes: values.size_bytes === "" ? null : Number(values.size_bytes),
        reported_sha256: values.reported_sha256 || null,
        hash_source: values.hash_source || null,
        actor
      };
      if (payload.reported_sha256 && !payload.hash_source) {
        setStatus("Indicá de qué manifiesto o herramienta proviene el hash declarado.", "error");
        $("forensicHashSource").focus();
        return;
      }

      state.busy = true;
      setStatus("Registrando los metadatos de recepción y la operación…");
      try {
        const created = await api("/api/forensics/cases/" + encodeURIComponent(state.selectedCaseId) + "/evidence", {
          method: "POST", body: JSON.stringify(payload)
        });
        evidenceForm.reset();
        evidenceDetails.open = false;
        $("forensicTimezone").value = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
        $("forensicReceivedAt").value = currentLocalTimestampWithOffset();
        state.busy = false;
        await loadCases();
        setStatus(created.evidence_number + " quedó registrada. El hash informado, si lo hay, sigue sin estar verificado.", "success");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        state.busy = false;
      }
    });

    $("closeForensicCase").addEventListener("click", async () => {
      if (state.busy || !state.selectedCase || state.selectedCase.status !== "open") return;
      const actor = operatorName();
      if (!actor) return;
      if (!window.confirm("¿Cerrar este caso? Se conservarán el registro y la evidencia, pero no podrás agregar nuevos elementos.")) return;
      state.busy = true;
      setStatus("Cerrando el caso y registrando la operación…");
      try {
        await api("/api/forensics/cases/" + encodeURIComponent(state.selectedCase.id) + "/close", {
          method: "POST", body: JSON.stringify({ actor })
        });
        state.busy = false;
        await loadCases();
        setStatus("El caso quedó cerrado. Su historial se conserva.", "success");
      } catch (error) {
        setStatus(error.message, "error");
      } finally {
        state.busy = false;
      }
    });

    $("forensicReportedHash").addEventListener("input", () => {
      $("forensicHashSource").required = Boolean($("forensicReportedHash").value.trim());
    });
    $("forensicTimezone").value = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    $("forensicReceivedAt").value = currentLocalTimestampWithOffset();
  }

  installRoadmapFilters();
  installManifestExport(
    "exportForensicAuditManifest",
    "/audit/manifest",
    "netsentinel-forensic-audit-manifest.json",
    "Preparando el manifiesto de auditoría…",
    "No se pudo descargar el manifiesto de auditoría.",
    "Auditoría descargada. Guardá su SHA-256 por separado si necesitás detectar sustituciones; el digest no es una firma digital."
  );
  installManifestExport(
    "exportForensicCaseManifest",
    "/manifest",
    "netsentinel-forensic-case-manifest.json",
    "Preparando el expediente consolidado…",
    "No se pudo descargar el expediente consolidado.",
    "Expediente consolidado descargado. Conservá su SHA-256 por separado si necesitás detectar sustituciones; el digest no es una firma digital."
  );
  installCaseForms();
  loadCases();
})();
