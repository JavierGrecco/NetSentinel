const SETTINGS_KEY = "netsentinelSettings";
const EVENTS_KEY = "netsentinelEvents";
const $ = id => document.getElementById(id);
const DEFAULTS = { enabled: false, capturePages: true, captureSearches: true, retentionDays: 7, excludeDomains: [] };

function normalizeRetentionDays(value) {
  // Do not let malformed storage values become NaN and hide every saved event.
  if (value === undefined || value === null || value === "") return DEFAULTS.retentionDays;
  const parsed = typeof value === "number"
    ? value
    : typeof value === "string" && /^\d+$/.test(value.trim())
      ? Number(value.trim())
      : NaN;
  if (!Number.isSafeInteger(parsed)) return DEFAULTS.retentionDays;
  return Math.max(1, Math.min(90, parsed));
}
function normalizeStoredBoolean(settings, key, fallback) {
  if (!settings || typeof settings !== "object" || Array.isArray(settings)) return false;
  if (!Object.prototype.hasOwnProperty.call(settings, key)) return fallback;
  // Only real booleans are trusted. Malformed persisted values fail closed so
  // strings like "false" cannot accidentally enable browser tracking.
  return typeof settings[key] === "boolean" ? settings[key] : false;
}

function isRetainedEvent(event, cutoff) {
  // Storage can contain stale or malformed records. Reject them before rendering.
  if (!event || typeof event !== "object" || Array.isArray(event)) return false;
  let observedAt;
  try { observedAt = Date.parse(event.observed_at); } catch { return false; }
  return Number.isFinite(observedAt) && observedAt >= cutoff;
}
function setStatus(message, { error = false } = {}) {
  const status = $("statusText");
  if (!status) return;
  status.textContent = message;
  if (status.classList) {
    if (error) status.classList.add("error");
    else status.classList.remove("error");
  }
  if (typeof status.setAttribute === "function") status.setAttribute("role", error ? "alert" : "status");
}

function reportPopupFailure(operation, userMessage, error) {
  const rawName = error && typeof error.name === "string" ? error.name : "Error";
  const safeName = rawName.replace(/[^A-Za-z0-9_-]/g, "").slice(0, 40) || "Error";
  // Never log URLs, search terms, stored records, or raw exception messages.
  console.error("NetSentinel: error al " + operation + " (" + safeName + ").");
  setStatus(userMessage, { error: true });
}

function escapeCsv(value) {
  let text = String(value ?? "");
  if (/^[\s\u0000-\u001f]*[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replace(/"/g, '""') + '"';
}
function when(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value || "") : date.toLocaleString();
}
async function getState() {
  const stored = await chrome.storage.local.get([SETTINGS_KEY, EVENTS_KEY]);
  const savedSettings = stored[SETTINGS_KEY];
  const raw = savedSettings && typeof savedSettings === "object" && !Array.isArray(savedSettings)
    ? savedSettings
    : {};
  const settings = { ...DEFAULTS, ...raw };
  settings.enabled = normalizeStoredBoolean(raw, "enabled", DEFAULTS.enabled);
  settings.capturePages = normalizeStoredBoolean(raw, "capturePages", DEFAULTS.capturePages);
  settings.captureSearches = normalizeStoredBoolean(raw, "captureSearches", DEFAULTS.captureSearches);
  settings.retentionDays = normalizeRetentionDays(settings.retentionDays);
  settings.excludeDomains = Array.isArray(settings.excludeDomains) ? settings.excludeDomains : [];
  let storedEvents = Array.isArray(stored[EVENTS_KEY]) ? stored[EVENTS_KEY] : [];
  if (chrome.runtime && typeof chrome.runtime.sendMessage === "function") {
    const response = await chrome.runtime.sendMessage({ type: "NETSENTINEL_GET_SAFE_EVENTS" });
    if (!response || response.ok !== true || !Array.isArray(response.events)) {
      throw new Error("safe events unavailable");
    }
    storedEvents = response.events;
  }
  const cutoff = Date.now() - settings.retentionDays * 86400000;
  const events = storedEvents.filter(event => isRetainedEvent(event, cutoff)).slice(-1000);
  // Reading/rendering must not write a stale event snapshot back over new
  // navigation events created by the service worker in another extension context.
  return { settings, events };
}
function renderRecent(events) {
  const parent = $("recent");
  parent.replaceChildren();
  for (const event of [...events].reverse().slice(0, 5)) {
    const row = document.createElement("div");
    row.className = "entry";
    const title = document.createElement("strong");
    title.textContent = event.event_type === "search_query"
      ? "Búsqueda · " + (event.search_engine || "motor") + ": " + (event.search_terms || "")
      : (event.page_url || event.domain || "Página");
    const meta = document.createElement("span");
    meta.textContent = when(event.observed_at) + " · " + (event.domain || "");
    row.append(title, meta);
    parent.append(row);
  }
}
async function render() {
  try {
    const { settings, events } = await getState();
    $("enabled").checked = Boolean(settings.enabled);
    $("capturePages").checked = Boolean(settings.capturePages);
    $("captureSearches").checked = Boolean(settings.captureSearches);
    $("retention").value = String(settings.retentionDays);
    $("excludeDomains").value = settings.excludeDomains.join("\n");
    $("count").textContent = String(events.length);
    setStatus(settings.enabled
      ? "Activo. Los nuevos eventos quedan guardados en este navegador."
      : "Detenido. No se registra navegación.");
    renderRecent(events);
    $("export").disabled = events.length === 0;
    return true;
  } catch (error) {
    reportPopupFailure(
      "cargar el estado local",
      "No se pudieron cargar la configuración y los registros locales. Comprobá que la extensión siga habilitada y volvé a abrir el panel.",
      error
    );
    const exportButton = $("export");
    if (exportButton) exportButton.disabled = true;
    return false;
  }
}
async function saveSettings({ confirmEnable = false } = {}) {
  try {
    const oldState = await getState();
    let enabled = $("enabled").checked;
    if (confirmEnable && enabled && !oldState.settings.enabled) {
      const accepted = window.confirm("Vas a registrar localmente páginas visitadas y búsquedas compatibles de este navegador. No captura contraseñas ni formularios. ¿Activar el registro?");
      if (!accepted) { $("enabled").checked = false; enabled = false; }
    }
    const settings = {
      enabled,
      capturePages: $("capturePages").checked,
      captureSearches: $("captureSearches").checked,
      retentionDays: normalizeRetentionDays($("retention").value),
      excludeDomains: $("excludeDomains").value.split(/\r?\n/).map(s => s.trim().toLowerCase().replace(/^\.+|\.+$/g, "")).filter(Boolean).slice(0, 100)
    };
    await chrome.storage.local.set({ [SETTINGS_KEY]: settings });
  } catch (error) {
    reportPopupFailure(
      "guardar la configuración",
      "No se pudo guardar la configuración. Los cambios no están confirmados; volvé a intentarlo.",
      error
    );
    return false;
  }
  return render();
}
function buildCsv(events) {
  const columns = ["observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "blocked", "page_url", "search_engine", "search_terms"];
  const rows = [columns.map(escapeCsv).join(",")];
  for (const event of events) rows.push(columns.map(column => escapeCsv(event[column] ?? "")).join(","));
  return "\ufeff" + rows.join("\r\n") + "\r\n";
}
function exportCsv(events) {
  const blob = new Blob([buildCsv(events)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "netsentinel-browser-activity.csv";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function initializePopup() {
  $("enabled").addEventListener("change", () => { void saveSettings({ confirmEnable: true }); });
  $("capturePages").addEventListener("change", () => { void saveSettings(); });
  $("captureSearches").addEventListener("change", () => { void saveSettings(); });
  $("saveSettings").addEventListener("click", () => { void saveSettings(); });
  $("export").addEventListener("click", async () => {
    try {
      const { events } = await getState();
      if (!events.length) {
        setStatus("No hay registros dentro del período de retención para exportar.");
        return;
      }
      exportCsv(events);
      setStatus("CSV preparado. Los registros originales siguen guardados localmente.");
    } catch (error) {
      reportPopupFailure(
        "exportar los registros",
        "No se pudo preparar el CSV. Los registros siguen en este navegador; volvé a intentarlo.",
        error
      );
    }
  });
  $("clear").addEventListener("click", async () => {
    if (!window.confirm("Se borrarán todos los registros que esta extensión conserva en este navegador. ¿Continuar?")) return;
    try {
      const response = await chrome.runtime.sendMessage({ type: "NETSENTINEL_CLEAR_EVENTS" });
      if (!response || response.ok !== true) throw new Error("clear failed");
      await render();
    } catch (error) {
      reportPopupFailure(
        "borrar los registros",
        "No se pudieron borrar los registros. No se confirmó el borrado; volvé a intentarlo.",
        error
      );
    }
  });
  void render();
}
if (typeof document !== "undefined" && typeof chrome !== "undefined") initializePopup();

if (typeof module !== "undefined" && module.exports) {
  module.exports = { DEFAULTS, normalizeRetentionDays, normalizeStoredBoolean, escapeCsv, buildCsv, getState, render, saveSettings };
}
