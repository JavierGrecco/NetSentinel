(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const state = {
    devices: [],
    scans: [],
    scansHasMore: false,
    scansLoadingOlder: false,
    scansCursor: null,
    selectedScanId: null,
    deviceEventsRequest: 0,
    deviceEventsRequestDeviceId: null,
    topologyGraph: null,
    topologyGraphScanId: null,
    selectedId: null,
    historyDeviceId: null,
    historyRequestDeviceId: null,
    historyRequest: 0
  };

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
  }

  function dateTime(value) {
    if (!value) return "Sin dato";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  const SCAN_PAGE_SIZE = 100;

  function mergeScans(existing, incoming) {
    const merged = new Map(existing.map(scan => [String(scan.id), scan]));
    for (const scan of incoming) merged.set(String(scan.id), scan);
    return Array.from(merged.values()).sort((left, right) => {
      const leftTime = Date.parse(left.started_at || left.finished_at || "");
      const rightTime = Date.parse(right.started_at || right.finished_at || "");
      if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
        return rightTime - leftTime;
      }
      return Number(right.id || 0) - Number(left.id || 0);
    });
  }

  function toast(message) {
    const element = $("toast");
    element.textContent = message;
    element.hidden = false;
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => { element.hidden = true; }, 4200);
  }

  async function api(url, options) {
    let response;
    try {
      response = await fetch(url, {
        ...(options || {}),
        headers: { "Content-Type": "application/json", ...((options && options.headers) || {}) }
      });
    } catch (_) {
      throw new Error("No se pudo contactar con NetSentinel. Verificá que el programa siga abierto.");
    }

    let body = null;
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) {
      const detail = typeof body?.detail === "string" ? body.detail : "La solicitud falló (HTTP " + response.status + ").";
      const code = typeof body?.error_code === "string" ? " Código: " + body.error_code + "." : "";
      const requestId = typeof body?.request_id === "string" ? " Referencia: " + body.request_id + "." : "";
      throw new Error(detail + code + requestId);
    }
    if (body === null) throw new Error("El servidor devolvió una respuesta vacía o inválida.");
    return body;
  }

  function availableNetworkScans() {
    // La API ofrece hasta 100 lecturas recientes. La vista inicial sigue eligiendo
    // la última que tenga subredes válidas, pero una lectura dañada también se
    // puede abrir para mostrar observaciones sin inventar sus asociaciones.
    return state.scans.slice().sort((left, right) => {
      const leftTime = Date.parse(left.started_at || left.finished_at || "");
      const rightTime = Date.parse(right.started_at || right.finished_at || "");
      if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
        return rightTime - leftTime;
      }
      return Number(right.id || 0) - Number(left.id || 0);
    });
  }

  function renderNetworkScanOptions() {
    const select = $("topologyScanSelect");
    if (!select) return;
    const scans = availableNetworkScans();
    const availableIds = new Set(scans.map(scan => String(scan.id)));
    if (!state.selectedScanId || !availableIds.has(String(state.selectedScanId))) {
      const graph = window.NetSentinelTopology;
      const preferred = graph ? graph.latestNetworkScan(scans) : null;
      state.selectedScanId = preferred ? String(preferred.id) :
        scans.length ? String(scans[0].id) : null;
      state.topologyGraph = null;
      state.topologyGraphScanId = null;
    }
    select.replaceChildren();
    if (!scans.length) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No hay capturas de red disponibles";
      select.appendChild(option);
      select.disabled = true;
      return;
    }
    for (const scan of scans) {
      const option = document.createElement("option");
      option.value = String(scan.id);
      option.textContent = "Lectura #" + scan.id + " · " +
        dateTime(scan.started_at || scan.finished_at) + " · " +
        Number(scan.devices_found || 0) + " equipo(s)";
      select.appendChild(option);
    }
    select.disabled = false;
    select.value = String(state.selectedScanId);
  }

  async function refresh() {
    try {
      const [devices, scans] = await Promise.all([
        api("/api/devices"),
        api("/api/scans?limit=100")
      ]);
      state.devices = Array.isArray(devices) ? devices : [];
      const firstScanLoad = state.scans.length === 0;
      state.scans = mergeScans(state.scans, Array.isArray(scans) ? scans : []);
      if (firstScanLoad) {
        state.scansHasMore = scans.length === SCAN_PAGE_SIZE;
        state.scansCursor = scans.length ? scans[scans.length - 1] : null;
      }
      updateScanHistoryControls();
      const graph = window.NetSentinelTopology;
      renderNetworkScanOptions();
      if (window.NetSentinelScanComparison) {
        window.NetSentinelScanComparison.renderSelectors(state.scans);
      }

      const scan = state.selectedScanId
        ? state.scans.find(item => String(item.id) === String(state.selectedScanId))
        : graph ? graph.latestNetworkScan(state.scans) : null;
      const targetScanId = scan ? String(scan.id) : null;
      if (!targetScanId) {
        state.topologyGraph = null;
        state.topologyGraphScanId = null;
      } else if (targetScanId !== state.topologyGraphScanId || state.topologyGraph === null) {
        state.topologyGraphScanId = targetScanId;
        state.topologyGraph = null;
        try {
          const model = await api("/api/scans/" + encodeURIComponent(targetScanId) + "/topology");
          if (state.topologyGraphScanId === targetScanId) state.topologyGraph = model;
        } catch (error) {
          // Sin la lectura exacta no sustituimos evidencia histórica por datos actuales.
          if (state.topologyGraphScanId === targetScanId) {
            state.topologyGraph = {
              scan_id: targetScanId,
              evidence_available: false,
              network_scope_available: false,
              nodes: [],
              edges: [],
              stats: {},
              warnings: [error.message]
            };
            state.topologyGraphScanId = null;
          }
        }
      }

      renderTopologyView();
      // Al actualizar, refrescamos también el contexto del equipo seleccionado.
      // Si no se vuelve a cargar, el mapa cambia pero el historial y los eventos
      // pueden quedar mostrando información anterior hasta elegir otro dispositivo.
      if (state.selectedId) {
        const selected = state.devices.find(device => String(device.id) === String(state.selectedId));
        if (selected) {
          loadDeviceHistory(selected, true);
          loadDeviceEvents(selected, true);
        }
      }
      $("appVersion").textContent = "NetSentinel · Datos guardados en tu computadora";
    } catch (error) {
      $("topologySummary").textContent = "No se pudo actualizar el explorador. " + error.message;
      toast("No se pudo actualizar el mapa: " + error.message);
    }
  }

  async function openEvidence(scanId, deviceId) {
    const targetScanId = String(scanId);
    const targetDeviceId = String(deviceId);
    const scanSelect = $("topologyScanSelect");
    const scan = state.scans.find(item => String(item.id) === targetScanId);
    if (!scan || !scanSelect) {
      toast("No se encontró esa captura entre las lecturas cargadas. Cargá capturas anteriores y volvé a intentarlo.");
      return false;
    }

    // Abrir la captura y limpiar filtros para no ocultar el equipo que originó la diferencia.
    state.selectedScanId = targetScanId;
    state.selectedId = targetDeviceId;
    state.topologyGraph = null;
    state.topologyGraphScanId = null;
    scanSelect.value = targetScanId;
    $("topologySearch").value = "";
    $("topologyStatusFilter").value = "all";
    clearDeviceHistory();
    clearDeviceEvents();

    await refresh();

    const selectedButton = Array.from(
      $("topologyAccessibleList").querySelectorAll(".topology-accessible-node")
    ).find(button => button.dataset.deviceId === targetDeviceId);
    const selected = state.selectedId === targetDeviceId &&
      selectedButton && selectedButton.getAttribute("aria-pressed") === "true";
    const panel = $("topologyPanel");
    if (panel && typeof panel.scrollIntoView === "function") {
      panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (selected) {
      toast("Lectura #" + targetScanId + " abierta con el equipo seleccionado.");
    } else {
      toast(
        "Se abrió la lectura #" + targetScanId +
        ", pero esta captura no aporta evidencia suficiente para ubicar ese equipo en el mapa. " +
        "Esto no demuestra que esté desconectado."
      );
    }
    return Boolean(selected);
  }

  window.NetSentinelNetworkNavigation = { openEvidence: openEvidence };

  function updateScanHistoryControls() {
    const button = $("loadMoreScansButton");
    const status = $("scanHistoryLoadStatus");
    if (!button || !status) return;
    button.disabled = state.scansLoadingOlder || !state.scansHasMore;
    button.textContent = state.scansLoadingOlder ? "Cargando capturas…" :
      state.scansHasMore ? "Cargar capturas anteriores" : "No hay más capturas";
    status.textContent = state.scansLoadingOlder
      ? "Buscando capturas anteriores…"
      : state.scansHasMore
        ? "Hay " + state.scans.length + " capturas cargadas. Podés consultar más antiguas."
        : "Capturas cargadas: " + state.scans.length + ". No hay más resultados por cargar.";
  }

  async function loadOlderScans() {
    if (state.scansLoadingOlder || !state.scansHasMore || !state.scans.length) return;
    const cursor = state.scansCursor;
    if (!cursor || !cursor.started_at || cursor.id === undefined || cursor.id === null) {
      toast("No se pudo continuar el historial porque la última captura no tiene una referencia válida.");
      return;
    }
    state.scansLoadingOlder = true;
    updateScanHistoryControls();
    try {
      const query = new URLSearchParams({
        limit: String(SCAN_PAGE_SIZE),
        before_started_at: cursor.started_at,
        before_id: String(cursor.id)
      });
      const older = await api("/api/scans?" + query.toString());
      const page = Array.isArray(older) ? older : [];
      state.scans = mergeScans(state.scans, page);
      if (page.length) state.scansCursor = page[page.length - 1];
      state.scansHasMore = page.length === SCAN_PAGE_SIZE;
      renderNetworkScanOptions();
      if (window.NetSentinelScanComparison) window.NetSentinelScanComparison.renderSelectors(state.scans);
    } catch (error) {
      toast("No se pudieron cargar capturas anteriores: " + error.message);
      const status = $("scanHistoryLoadStatus");
      if (status) status.textContent = "No se pudieron cargar capturas anteriores. Volvé a intentarlo.";
    } finally {
      state.scansLoadingOlder = false;
      updateScanHistoryControls();
    }
  }

  function renderTopologyView() {
    const graph = window.NetSentinelTopology;
    if (!graph) {
      $("topologySummary").textContent = "No se pudo cargar el motor local del mapa. Recargá la página y revisá los recursos instalados.";
      return;
    }
    const model = graph.renderTopology({
      topologyGraph: state.topologyGraph,
      canvas: $("topologyCanvas"),
      summary: $("topologySummary"),
      selection: $("topologySelection"),
      accessible: $("topologyAccessibleList"),
      devices: state.devices,
      scans: state.scans,
      selectedScanId: state.selectedScanId,
      search: $("topologySearch").value,
      status: $("topologyStatusFilter").value,
      selectedId: state.selectedId,
      onSelect: device => {
        state.selectedId = device ? String(device.id) : null;
        if (device) {
          loadDeviceHistory(device, true);
          loadDeviceEvents(device, true);
        } else {
          clearDeviceHistory();
          clearDeviceEvents();
        }
      },
      onOpenHistory: device => showDeviceHistory(device.id)
    });

    $("networkTotalMetric").textContent = state.devices.length;
    // Si no hay evidencia exacta para la lectura, el valor es desconocido, no cero.
    $("networkObservedMetric").textContent =
      model && model.hasNetworkData ? Number(model.scanObservedCount || 0) : "—";
    $("networkReviewMetric").textContent = state.devices.filter(device => !device.trusted).length;
    $("networkSubnetMetric").textContent =
      model && model.scan && model.networkScopeAvailable !== false && Array.isArray(model.networks)
        ? model.networks.length : "—";

    if (state.selectedId && !(model && Array.isArray(model.visibleDeviceIds) &&
        model.visibleDeviceIds.includes(String(state.selectedId)))) {
      state.selectedId = null;
      clearDeviceHistory();
      clearDeviceEvents();
    }
  }

  function clearDeviceHistory() {
    state.historyRequest += 1;
    state.historyRequestDeviceId = null;
    state.historyDeviceId = null;
    const box = $("topologyHistory");
    if (box) {
      box.innerHTML = '<p class="topology-selection-empty">Seleccioná un equipo para consultar cuándo se observó y qué direcciones tenía.</p>';
    }
  }

  async function loadDeviceHistory(device, force) {
    if (!device || device.id === undefined || device.id === null) return;
    const id = String(device.id);
    if (!force && (state.historyDeviceId === id || state.historyRequestDeviceId === id)) return;
    state.historyRequest += 1;
    const requestId = state.historyRequest;
    state.historyRequestDeviceId = id;
    const box = $("topologyHistory");
    box.innerHTML = '<div class="empty">Cargando observaciones…</div>';
    try {
      const data = await api("/api/devices/" + encodeURIComponent(id) + "/history?limit=12");
      if (requestId !== state.historyRequest || String(state.selectedId) !== id) return;
      state.historyDeviceId = id;
      state.historyRequestDeviceId = null;
      if (!Array.isArray(data.observations) || !data.observations.length) {
        box.innerHTML = '<div class="empty">Todavía no hay observaciones guardadas para este dispositivo. Ejecutá un nuevo descubrimiento para empezar a construir el historial.</div>';
        return;
      }
      box.innerHTML = data.observations.map(item =>
        '<article class="topology-history-entry">' +
          '<span class="topology-history-marker" aria-hidden="true"></span>' +
          '<div><strong>' + escapeHtml(item.ip_address || "Dirección sin identificar") + '</strong>' +
          '<div class="topology-history-meta">' + escapeHtml(dateTime(item.observed_at)) + '</div>' +
          '<div class="topology-history-meta">Fuente: ' + escapeHtml(item.source || item.scan_source || "desconocida") + '</div></div>' +
        '</article>'
      ).join("");
    } catch (error) {
      if (requestId !== state.historyRequest || String(state.selectedId) !== id) return;
      state.historyDeviceId = id;
      state.historyRequestDeviceId = null;
      box.textContent = "No se pudo cargar el historial: " + error.message;
    }
  }

  function eventLabel(event) {
    const labels = {
      "new_device": "Dispositivo detectado por primera vez",
      "trust_changed": "Cambio en el estado de confianza",
      "ip_changed": "Cambio de dirección IP",
      "new_address": "Nueva dirección observada"
    };
    return labels[event.event_type] || String(event.event_type || "Evento registrado");
  }

  function clearDeviceEvents() {
    state.deviceEventsRequest += 1;
    state.deviceEventsRequestDeviceId = null;
    const box = $("topologyEvents");
    if (box) {
      box.innerHTML = '<p class="topology-selection-empty">Seleccioná un equipo para ver los eventos de inventario relacionados.</p>';
    }
  }

  async function loadDeviceEvents(device, force) {
    if (!device || device.id === undefined || device.id === null) {
      clearDeviceEvents();
      return;
    }
    const id = String(device.id);
    if (!force && state.deviceEventsRequestDeviceId === id) return;
    state.deviceEventsRequest += 1;
    const requestId = state.deviceEventsRequest;
    state.deviceEventsRequestDeviceId = id;
    const box = $("topologyEvents");
    box.innerHTML = '<div class="empty">Cargando cambios registrados…</div>';
    try {
      const events = await api("/api/events?device_id=" + encodeURIComponent(id) + "&limit=8");
      if (requestId !== state.deviceEventsRequest || String(state.selectedId) !== id) return;
      state.deviceEventsRequestDeviceId = null;
      renderDeviceEvents(device, Array.isArray(events) ? events : []);
    } catch (error) {
      if (requestId !== state.deviceEventsRequest || String(state.selectedId) !== id) return;
      state.deviceEventsRequestDeviceId = null;
      box.textContent = "No se pudieron cargar los cambios registrados: " + error.message;
    }
  }

  function renderDeviceEvents(device, events) {
    const box = $("topologyEvents");
    if (!device) {
      clearDeviceEvents();
      return;
    }
    const related = Array.isArray(events) ? events : [];
    if (!related.length) {
      box.innerHTML = '<div class="empty">No hay eventos de inventario asociados a este equipo en el historial reciente.</div>';
      return;
    }
    box.innerHTML = related.map(event =>
      '<article class="topology-history-entry">' +
        '<span class="topology-history-marker" aria-hidden="true"></span>' +
        '<div><strong>' + escapeHtml(eventLabel(event)) + '</strong>' +
        '<div class="topology-history-meta">' + escapeHtml(dateTime(event.created_at)) + '</div>' +
        (event.ip_address ? '<div class="topology-history-meta">IP: ' + escapeHtml(event.ip_address) + '</div>' : '') +
        '<div class="topology-history-meta">' + escapeHtml(event.message || "NetSentinel registró un cambio en el inventario.") + '</div></div>' +
      '</article>'
    ).join("");
  }

  async function showDeviceHistory(id) {
    $("historyContent").innerHTML = '<div class="empty">Cargando historial…</div>';
    $("historyDialog").showModal();
    try {
      const data = await api("/api/devices/" + encodeURIComponent(id) + "/history?limit=200");
      const device = data.device || {};
      $("historyTitle").textContent = "Historial · " + (device.display_name || device.ip_address || ("Dispositivo " + id));
      $("historySubtitle").textContent = data.count + " observación(es) recuperadas; más recientes primero.";
      $("historyContent").innerHTML = data.observations.length ? data.observations.map(item =>
        '<article class="event"><span class="dot info" aria-hidden="true"></span><div>' +
        '<div class="event-title">' + escapeHtml(item.ip_address || "Dirección sin identificar") + '</div>' +
        '<div class="event-meta">' + escapeHtml(dateTime(item.observed_at)) + ' · Fuente: ' +
        escapeHtml(item.source || item.scan_source || "desconocida") + '</div></div></article>'
      ).join("") : '<div class="empty">Todavía no hay observaciones guardadas para este dispositivo.</div>';
    } catch (error) {
      $("historyContent").textContent = "No se pudo cargar el historial: " + error.message;
    }
  }

  $("loadMoreScansButton").addEventListener("click", loadOlderScans);
  $("topologyScanSelect").addEventListener("change", () => {
    state.selectedScanId = $("topologyScanSelect").value || null;
    state.topologyGraph = null;
      state.topologyGraphScanId = null;
    state.selectedId = null;
    clearDeviceHistory();
    clearDeviceEvents();
    refresh();
  });
  $("topologySearch").addEventListener("input", renderTopologyView);
  $("topologyStatusFilter").addEventListener("change", renderTopologyView);
  $("topologyResetSearch").addEventListener("click", () => {
    $("topologySearch").value = "";
    $("topologyStatusFilter").value = "all";
    renderTopologyView();
    $("topologySearch").focus();
  });
  $("topologyZoomIn").addEventListener("click", () => window.NetSentinelTopology && window.NetSentinelTopology.zoomBy(1));
  $("topologyZoomOut").addEventListener("click", () => window.NetSentinelTopology && window.NetSentinelTopology.zoomBy(-1));
  $("topologyFit").addEventListener("click", () => window.NetSentinelTopology && window.NetSentinelTopology.fit());
  $("topologyRelayout").addEventListener("click", () => window.NetSentinelTopology && window.NetSentinelTopology.relayout());
  $("refreshBtn").addEventListener("click", refresh);
  $("closeHistory").addEventListener("click", () => $("historyDialog").close());
  $("scanBtn").addEventListener("click", async () => {
    if (!window.confirm("NetSentinel buscará equipos en subredes IPv4 privadas detectadas en esta computadora. Esto genera tráfico de descubrimiento en tu red local. ¿Querés continuar?")) return;
    const button = $("scanBtn");
    button.disabled = true;
    button.textContent = "Buscando…";
    try {
      const result = await api("/api/scan", { method: "POST" });
      const warnings = (result.errors || []).length ? " Avisos: " + result.errors.join(" · ") : "";
      toast((result.message || "El descubrimiento terminó.") + " Equipos: " + result.devices_found +
        "; nuevas incorporaciones: " + result.new_devices + "." + warnings);
      await refresh();
    } catch (error) {
      toast("Falló el descubrimiento: " + error.message);
    } finally {
      button.disabled = false;
      button.textContent = "⌕ Descubrir dispositivos";
    }
  });

  window.addEventListener("resize", () => {
    // El contenedor cambia de tamaño con los breakpoints; Cytoscape actualiza su lienzo al hacerlo.
    if (window.NetSentinelTopology && window.NetSentinelTopology.fit) {
      // No reajustamos automáticamente el zoom para no perder la posición elegida por el usuario.
    }
  });

  api("/api/health").then(info => {
    $("appVersion").textContent = "NetSentinel v" + info.version + " · Datos guardados en tu computadora";
  }).catch(() => {});
  refresh();
})();
