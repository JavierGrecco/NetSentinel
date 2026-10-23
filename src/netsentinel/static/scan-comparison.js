(function (root) {
  "use strict";

  const STATUS_LABELS = {
    only_in_comparison: "Solo observado en la captura posterior",
    only_in_baseline: "No observado en la captura posterior",
    address_changed: "Cambió el conjunto de direcciones observadas"
  };
  const STAT_LABELS = [
    ["only_in_comparison", "Solo en la captura posterior"],
    ["only_in_baseline", "No observado en la posterior"],
    ["address_changed", "Direcciones modificadas"],
    ["unchanged", "Sin cambios de direcciones"]
  ];

  function element(id) {
    return root.document ? root.document.getElementById(id) : null;
  }
  function dateLabel(value) {
    if (!value) return "fecha desconocida";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }
  function orderedScans(scans) {
    return (Array.isArray(scans) ? scans.slice() : []).sort((left, right) => {
      const leftTime = Date.parse(left && (left.started_at || left.finished_at) || "");
      const rightTime = Date.parse(right && (right.started_at || right.finished_at) || "");
      if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) return rightTime - leftTime;
      return Number(right && right.id || 0) - Number(left && left.id || 0);
    });
  }
  function appendText(parent, tagName, text, className) {
    const child = root.document.createElement(tagName);
    child.textContent = String(text == null ? "" : text);
    if (className) child.className = className;
    parent.appendChild(child);
    return child;
  }
  function resetSelect(select, scans, selectedId, defaultId, placeholder) {
    if (!select) return;
    select.replaceChildren();
    const prompt = root.document.createElement("option");
    prompt.value = "";
    prompt.textContent = placeholder;
    select.appendChild(prompt);
    for (const scan of scans) {
      const option = root.document.createElement("option");
      option.value = String(scan.id);
      option.textContent = "Lectura #" + scan.id + " · " +
        dateLabel(scan.started_at || scan.finished_at) + " · " +
        Number(scan.devices_found || 0) + " equipo(s)";
      select.appendChild(option);
    }
    const available = new Set(scans.map(scan => String(scan.id)));
    const desired = selectedId && available.has(String(selectedId)) ? String(selectedId) : String(defaultId || "");
    select.value = desired;
  }
  function renderSelectors(scans) {
    const first = element("scanCompareFirst");
    const second = element("scanCompareSecond");
    const button = element("scanCompareButton");
    if (!first || !second || !button) return;
    const ordered = orderedScans(scans);
    resetSelect(first, ordered, first.value, ordered.length > 1 ? ordered[1].id : "", "Elegí una lectura");
    resetSelect(second, ordered, second.value, ordered.length > 0 ? ordered[0].id : "", "Elegí una lectura");
    button.disabled = ordered.length < 2 || !first.value || !second.value || first.value === second.value;
    if (ordered.length < 2) {
      const result = element("scanComparisonResult");
      if (result) {
        result.replaceChildren();
        appendText(result, "p", "Guardá al menos dos lecturas para poder compararlas.", "scan-comparison-empty");
      }
    }
  }
  function showMessage(message, className) {
    const result = element("scanComparisonResult");
    if (!result) return;
    result.replaceChildren();
    appendText(result, "p", message, className || "scan-comparison-empty");
  }
  function appendStatCards(parent, summary) {
    const grid = appendText(parent, "div", "", "scan-compare-stats");
    for (const item of STAT_LABELS) {
      const key = item[0];
      const label = item[1];
      const card = appendText(grid, "div", "", "scan-compare-stat");
      appendText(card, "span", label, "scan-compare-stat-label");
      appendText(card, "strong", String(Number(summary[key] || 0)), "scan-compare-stat-value");
    }
  }
  function appendWarnings(parent, response) {
    if (response.partial && Array.isArray(response.warnings) && response.warnings.length) {
      const warning = appendText(
        parent,
        "div",
        "Interpretá estas diferencias con cautela: las capturas informaron límites o errores.",
        "scan-compare-warning"
      );
      const list = appendText(warning, "ul", "", "scan-compare-warning-list");
      for (const item of response.warnings) appendText(list, "li", item);
    }
  }
  function renderCaptureEvidence(parent, label, scan, observations, side, deviceId) {
    const section = appendText(parent, "section", "", "scan-compare-evidence");
    appendText(section, "strong", label + " · captura #" + scan.id, "scan-compare-evidence-title");
    const evidence = Array.isArray(observations) ? observations : [];
    if (!evidence.length) {
      appendText(
        section,
        "p",
        "No se registraron observaciones para este dispositivo en esa captura.",
        "scan-compare-item-meta"
      );
    } else {
      for (const observation of evidence) {
        const address = observation.ip_address || "Dirección sin identificar";
        const source = observation.source || "fuente desconocida";
        appendText(
          section,
          "div",
          address + " · " + dateLabel(observation.observed_at) + " · Fuente: " + source,
          "scan-compare-item-meta"
        );
      }
    }

    const navigator = root.NetSentinelNetworkNavigation;
    if (!navigator || typeof navigator.openEvidence !== "function") return;
    const button = root.document.createElement("button");
    button.type = "button";
    button.className = "quiet scan-compare-evidence-action";
    button.textContent = "Ver equipo en el mapa";
    button.setAttribute(
      "aria-label",
      "Ver equipo #" + deviceId + " en la captura " + side + " #" + scan.id + " en el mapa"
    );
    button.addEventListener("click", async function () {
      button.disabled = true;
      try {
        await navigator.openEvidence(scan.id, deviceId);
      } catch (error) {
        showMessage(
          "No se pudo abrir la evidencia del dispositivo: " +
            (error && error.message ? error.message : "error inesperado") + "."
        );
      } finally {
        button.disabled = false;
      }
    });
    section.appendChild(button);
  }

  function renderChanges(parent, response) {
    const changes = Array.isArray(response.changes) ? response.changes : [];
    if (!changes.length) {
      appendText(parent, "p", "No se detectaron diferencias en las direcciones observadas entre estas capturas.", "scan-comparison-empty");
      return;
    }
    const list = appendText(parent, "div", "", "scan-compare-list");
    for (const change of changes) {
      const item = appendText(list, "article", "", "scan-compare-item");
      const label = change.display_name || (change.mac_address
        ? "Equipo " + change.mac_address
        : "Dispositivo #" + change.device_id);
      appendText(item, "strong", label, "scan-compare-item-title");
      appendText(item, "span", STATUS_LABELS[change.status] || "Cambió la observación registrada", "scan-compare-item-status");
      if (change.mac_address) appendText(item, "div", "MAC: " + change.mac_address, "scan-compare-item-meta");
      const before = Array.isArray(change.baseline_addresses) && change.baseline_addresses.length
        ? change.baseline_addresses.join(", ") : "Sin observación registrada";
      const after = Array.isArray(change.comparison_addresses) && change.comparison_addresses.length
        ? change.comparison_addresses.join(", ") : "Sin observación registrada";
      appendText(item, "div", "En la captura anterior: " + before, "scan-compare-item-meta");
      appendText(item, "div", "En la captura posterior: " + after, "scan-compare-item-meta");
      item.dataset.deviceId = String(change.device_id);
      renderCaptureEvidence(
        item,
        "Captura anterior",
        response.baseline_scan || {},
        change.baseline_evidence,
        "anterior",
        change.device_id
      );
      renderCaptureEvidence(
        item,
        "Captura posterior",
        response.comparison_scan || {},
        change.comparison_evidence,
        "posterior",
        change.device_id
      );
    }
  }
  function renderComparison(response) {
    const result = element("scanComparisonResult");
    if (!result) return;
    result.replaceChildren();
    if (!response || response.comparable !== true) {
      appendText(result, "p", response && response.reason ? response.reason : "No se pudieron comparar estas lecturas.", "scan-comparison-empty");
      return;
    }
    const baseline = response.baseline_scan || {};
    const comparison = response.comparison_scan || {};
    appendText(
      result,
      "p",
      "Se comparó la captura #" + baseline.id + " (" + dateLabel(baseline.started_at) +
        ") con la #" + comparison.id + " (" + dateLabel(comparison.started_at) + ").",
      "scan-compare-caption"
    );
    if (Array.isArray(response.common_networks) && response.common_networks.length) {
      appendText(result, "p", "Subred(es) compartida(s): " + response.common_networks.join(", "), "scan-compare-caption");
    }
    appendWarnings(result, response);
    if (response.summary) appendStatCards(result, response.summary);
    renderChanges(result, response);
    appendText(result, "p", response.absence_note || "La ausencia de una observación no demuestra desconexión.", "scan-compare-disclaimer");
  }
  async function compareSelectedScans() {
    const first = element("scanCompareFirst");
    const second = element("scanCompareSecond");
    const button = element("scanCompareButton");
    if (!first || !second || !button || !first.value || !second.value || first.value === second.value) {
      showMessage("Elegí dos lecturas diferentes para iniciar la comparación.");
      return;
    }
    button.disabled = true;
    const previousLabel = button.textContent;
    button.textContent = "Comparando…";
    showMessage("Consultando las observaciones históricas guardadas…");
    try {
      const query = new URLSearchParams({ first_scan_id: first.value, second_scan_id: second.value });
      const response = await root.fetch("/api/scans/compare?" + query.toString(), {
        headers: { Accept: "application/json" },
        cache: "no-store"
      });
      let body = null;
      try { body = await response.json(); } catch { body = null; }
      if (!response.ok) {
        throw new Error(typeof (body && body.detail) === "string"
          ? body.detail : "No se pudo comparar las lecturas (HTTP " + response.status + ").");
      }
      renderComparison(body);
    } catch (error) {
      showMessage("No se pudo completar la comparación: " +
        (error && error.message ? error.message : "error inesperado") + ".");
    } finally {
      button.textContent = previousLabel;
      button.disabled = !first.value || !second.value || first.value === second.value;
    }
  }
  function initialize() {
    const button = element("scanCompareButton");
    const first = element("scanCompareFirst");
    const second = element("scanCompareSecond");
    if (!button || !first || !second) return;
    button.addEventListener("click", compareSelectedScans);
    const updateButton = () => {
      button.disabled = !first.value || !second.value || first.value === second.value;
    };
    first.addEventListener("change", updateButton);
    second.addEventListener("change", updateButton);
  }

  const api = { renderSelectors: renderSelectors, renderComparison: renderComparison };
  root.NetSentinelScanComparison = api;
  if (root.document) initialize();
  if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
