(() => {
  const $ = id => document.getElementById(id);
  const stateFilter = $("stateFilter");
  const list = $("findingsList");
  const status = $("status");
  const refreshBtn = $("refreshBtn");
  const exportLink = $("exportLink");
  let loading = false;

  function node(tag, className, value) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (value !== undefined && value !== null) item.textContent = String(value);
    return item;
  }

  function dateText(value) {
    if (!value) return "Sin fecha";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString();
  }

  function labelForState(value) {
    return ({active:"Pendiente", acknowledged:"Revisado", resolved:"Recuperado"})[value] || value || "Sin estado";
  }

  function labelForCategory(value) {
    return ({inventory:"Inventario", availability:"Disponibilidad"})[value] || value || "Otro";
  }

  function evidenceLabel(key) {
    return ({
      event_type:"Tipo de evento", created_at:"Fecha del evento", event_severity:"Severidad registrada",
      message:"Mensaje original", acknowledged:"Reconocido",
      opened_at:"Inicio del incidente", updated_at:"Última actualización", resolved_at:"Recuperación registrada",
      failure_count:"Comprobaciones fallidas", last_detail:"Último detalle", monitor_kind:"Tipo de comprobación",
      target:"Objetivo"
    })[key] || key.replaceAll("_", " ");
  }

  function appendSection(card, title, content) {
    const section = node("section", "finding-section");
    section.append(node("h3", "", title));
    if (typeof content === "string") {
      section.append(node("p", "", content));
    } else {
      section.append(content);
    }
    card.append(section);
  }

  function appendEvidence(card, finding) {
    const details = node("details", "finding-section");
    details.append(node("summary", "", "Ver evidencia y procedencia"));
    const evidence = finding.evidence || {};
    for (const [key, value] of Object.entries(evidence)) {
      if (value === null || value === undefined || value === "") continue;
      let printable = value;
      if (typeof value === "object") {
        try { printable = JSON.stringify(value); } catch (_) { printable = "[dato no disponible]"; }
      } else if (typeof value === "boolean") {
        printable = value ? "Sí" : "No";
      } else if (key.endsWith("_at")) {
        printable = dateText(value);
      }
      const row = node("p");
      const strong = node("strong", "", evidenceLabel(key) + ": ");
      row.append(strong, document.createTextNode(String(printable)));
      details.append(row);
    }
    const source = finding.source || {};
    const provenance = node("p");
    provenance.append(
      node("strong", "", "Fuente: "),
      document.createTextNode([source.system, source.record_type, source.record_id].filter(v => v !== null && v !== undefined).join(" · ") || "No indicada")
    );
    details.append(provenance);
    card.append(details);
  }

  function renderFinding(finding) {
    const card = node("article", "finding-card");
    const head = node("div", "finding-head");
    const titleWrap = node("div");
    titleWrap.append(node("h3", "finding-title", finding.title || "Hallazgo sin título"));
    titleWrap.append(node("p", "finding-summary", finding.summary || "Sin detalle disponible."));
    head.append(titleWrap);
    const tags = node("div", "finding-tags");
    tags.append(node("span", "finding-tag " + (finding.status || ""), labelForState(finding.status)));
    tags.append(node("span", "finding-tag " + (finding.severity || ""), "Severidad: " + (finding.severity || "no indicada")));
    tags.append(node("span", "finding-tag", labelForCategory(finding.category)));
    head.append(tags);
    card.append(head);

    const asset = finding.asset || {};
    card.append(node("div", "finding-meta", "Activo/objetivo: " + (asset.label || "No asociado") + (asset.ip_address ? " · IP " + asset.ip_address : "") + (asset.target ? " · " + asset.target : "")));
    card.append(node("div", "finding-meta", "Actualizado: " + dateText(finding.updated_at || finding.first_seen_at) + " · Confianza: " + ((finding.confidence || {}).level || "no indicada")));
    appendSection(card, "Qué significa y sus límites", ((finding.confidence || {}).explanation || "No se indicó una explicación de confianza.") + " " + (finding.severity_basis || ""));
    appendSection(card, "Próximo paso sugerido", finding.recommended_action || "Contrastá el dato con una fuente independiente.");
    appendEvidence(card, finding);

    if (Array.isArray(finding.limitations) && finding.limitations.length) {
      const list = document.createElement("ul");
      for (const limitation of finding.limitations) list.append(node("li", "", limitation));
      appendSection(card, "Limitaciones", list);
    }

    if (finding.source && finding.source.system === "inventory" && finding.status === "active" && Number.isInteger(finding.source.record_id)) {
      const actions = node("div", "finding-actions");
      const asset = finding.asset || {};
      if (Number.isInteger(asset.device_id)) {
        const trustButton = node("button", "primary", "Marcar dispositivo como conocido");
        trustButton.type = "button";
        trustButton.addEventListener("click", () => trustDeviceFromFinding(finding, trustButton));
        actions.append(trustButton);
      }
      const reviewButton = node("button", "", "Solo marcar como revisado");
      reviewButton.type = "button";
      reviewButton.addEventListener("click", () => acknowledgeFinding(finding, reviewButton));
      actions.append(reviewButton);
      card.append(actions);
      const actionHint = node("p", "finding-action-hint",
        "“Conocido” cambia la confianza del dispositivo en el inventario. “Revisado” solo quita este evento de la bandeja pendiente; no borra datos ni demuestra que el equipo sea seguro.");
      card.append(actionHint);
    } else if (finding.category === "availability" && finding.status === "active") {
      const actions = node("div", "finding-actions");
      const link = node("a", "monitor-link", "Revisar monitor e incidente");
      link.href = "/monitors#incidentes";
      actions.append(link);
      card.append(actions);
    }
    return card;
  }

  async function trustDeviceFromFinding(finding, button) {
    if (button.disabled) return;
    const asset = finding.asset || {};
    const deviceLabel = asset.display_name || asset.label || asset.ip_address || "este dispositivo";
    if (!window.confirm("¿Confirmás que reconocés " + deviceLabel + " y querés marcarlo como conocido? Esto registra tu decisión, pero no demuestra por sí solo que el equipo sea seguro.")) return;
    button.disabled = true;
    try {
      const deviceResponse = await fetch("/api/devices/" + asset.device_id, {
        method: "PATCH",
        headers: {"Content-Type":"application/json", "Accept":"application/json"},
        body: JSON.stringify({trusted:true}),
        cache: "no-store"
      });
      const devicePayload = await deviceResponse.json().catch(() => ({}));
      if (!deviceResponse.ok) throw new Error(devicePayload.detail || ("No se pudo actualizar el dispositivo (HTTP " + deviceResponse.status + ")."));

      const eventResponse = await fetch("/api/events/" + finding.source.record_id, {
        method: "PATCH",
        headers: {"Content-Type":"application/json", "Accept":"application/json"},
        body: JSON.stringify({acknowledged:true}),
        cache: "no-store"
      });
      const eventPayload = await eventResponse.json().catch(() => ({}));
      if (!eventResponse.ok) {
        await loadFindings();
        status.textContent = "El dispositivo quedó marcado como conocido, pero el evento no se pudo marcar como revisado: " + (eventPayload.detail || ("HTTP " + eventResponse.status)) + ". Actualizá la bandeja para comprobar el estado.";
        return;
      }
      await loadFindings();
      status.textContent = "Dispositivo marcado como conocido y evento revisado. Esto no equivale a una certificación de seguridad.";
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : "No se pudo actualizar la confianza del dispositivo.";
      button.disabled = false;
    }
  }

  async function acknowledgeFinding(finding, button) {
    if (button.disabled) return;
    button.disabled = true;
    try {
      const response = await fetch("/api/events/" + finding.source.record_id, {
        method: "PATCH",
        headers: {"Content-Type":"application/json", "Accept":"application/json"},
        body: JSON.stringify({acknowledged:true}),
        cache: "no-store"
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || ("Error HTTP " + response.status));
      await loadFindings();
      status.textContent = "Evento marcado como revisado. No se borró el registro ni se cambió la confianza del dispositivo.";
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : "No se pudo actualizar el evento.";
      button.disabled = false;
    }
  }

  async function loadFindings() {
    if (loading) return;
    loading = true;
    refreshBtn.disabled = true;
    stateFilter.disabled = true;
    list.setAttribute("aria-busy", "true");
    list.replaceChildren();
    const selectedState = stateFilter.value;
    exportLink.href = "/api/export/findings.json?state=" + encodeURIComponent(selectedState) + "&limit=200";
    status.textContent = "Consultando hallazgos locales…";
    try {
      const response = await fetch("/api/findings?state=" + encodeURIComponent(selectedState) + "&limit=200", {
        headers: {"Accept":"application/json"},
        cache: "no-store"
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || ("Error HTTP " + response.status));
      const summary = payload.summary || {};
      $("countReturned").textContent = summary.returned ?? 0;
      $("countActive").textContent = summary.active ?? 0;
      $("countClosed").textContent = Number(summary.acknowledged || 0) + Number(summary.resolved || 0);
      const findings = Array.isArray(payload.findings) ? payload.findings : [];
      status.textContent = findings.length
        ? findings.length + " resultado(s) · Estado: " + labelForState(selectedState) + ". " + (payload.notice || "")
        : "No hay hallazgos en el estado seleccionado. Esta vista refleja solo las fuentes locales disponibles.";
      if (!findings.length) {
        const empty = node("div", "empty-state");
        empty.append(node("strong", "", "No hay resultados en este filtro"), document.createTextNode("Probá otro estado o actualizá cuando se hayan registrado nuevos eventos."));
        list.append(empty);
      } else {
        for (const finding of findings) list.append(renderFinding(finding));
      }
    } catch (error) {
      $("countReturned").textContent = "—";
      $("countActive").textContent = "—";
      $("countClosed").textContent = "—";
      const empty = node("div", "empty-state");
      empty.append(node("strong", "", "No se pudieron cargar los hallazgos"), document.createTextNode(error instanceof Error ? error.message : "Error inesperado."));
      list.append(empty);
      status.textContent = "La consulta falló. Los registros almacenados no se modificaron.";
    } finally {
      list.setAttribute("aria-busy", "false");
      refreshBtn.disabled = false;
      stateFilter.disabled = false;
      loading = false;
    }
  }

  refreshBtn.addEventListener("click", loadFindings);
  stateFilter.addEventListener("change", loadFindings);
  loadFindings();
})();
