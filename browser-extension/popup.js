const SETTINGS_KEY = "netsentinelSettings";
const EVENTS_KEY = "netsentinelEvents";
const $ = id => document.getElementById(id);
const DEFAULTS = { enabled: false, capturePages: true, captureSearches: true, retentionDays: 7, excludeDomains: [] };

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
  const settings = { ...DEFAULTS, ...(stored[SETTINGS_KEY] || {}) };
  settings.retentionDays = Math.max(1, Math.min(90, Number(settings.retentionDays || 7)));
  settings.excludeDomains = Array.isArray(settings.excludeDomains) ? settings.excludeDomains : [];
  const cutoff = Date.now() - settings.retentionDays * 86400000;
  const events = (Array.isArray(stored[EVENTS_KEY]) ? stored[EVENTS_KEY] : [])
    .filter(event => Date.parse(event.observed_at) >= cutoff).slice(-1000);
  await chrome.storage.local.set({ [SETTINGS_KEY]: settings, [EVENTS_KEY]: events });
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
  const { settings, events } = await getState();
  $("enabled").checked = Boolean(settings.enabled);
  $("capturePages").checked = Boolean(settings.capturePages);
  $("captureSearches").checked = Boolean(settings.captureSearches);
  $("retention").value = String(settings.retentionDays);
  $("excludeDomains").value = settings.excludeDomains.join("\n");
  $("count").textContent = String(events.length);
  $("statusText").textContent = settings.enabled
    ? "Activo. Los nuevos eventos quedan guardados en este navegador."
    : "Detenido. No se registra navegación.";
  renderRecent(events);
  $("export").disabled = events.length === 0;
}
async function saveSettings({ confirmEnable = false } = {}) {
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
    retentionDays: Math.max(1, Math.min(90, Number($("retention").value || 7))),
    excludeDomains: $("excludeDomains").value.split(/\r?\n/).map(s => s.trim().toLowerCase().replace(/^\.+|\.+$/g, "")).filter(Boolean).slice(0, 100)
  };
  await chrome.storage.local.set({ [SETTINGS_KEY]: settings });
  await render();
}
function exportCsv(events) {
  const columns = ["observed_at", "event_type", "domain", "destination_ip", "destination_port",
    "protocol", "app_name", "blocked", "page_url", "search_engine", "search_terms"];
  const rows = [columns.map(escapeCsv).join(",")];
  for (const event of events) rows.push(columns.map(column => escapeCsv(event[column] ?? "")).join(","));
  const blob = new Blob(["\ufeff" + rows.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "netsentinel-browser-activity.csv";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("enabled").addEventListener("change", () => { void saveSettings({ confirmEnable: true }); });
$("capturePages").addEventListener("change", () => { void saveSettings(); });
$("captureSearches").addEventListener("change", () => { void saveSettings(); });
$("saveSettings").addEventListener("click", () => { void saveSettings(); });
$("export").addEventListener("click", async () => { const { events } = await getState(); if (events.length) exportCsv(events); });
$("clear").addEventListener("click", async () => {
  if (!window.confirm("Se borrarán todos los registros que esta extensión conserva en este navegador. ¿Continuar?")) return;
  await chrome.storage.local.set({ [EVENTS_KEY]: [] });
  await render();
});
void render();
