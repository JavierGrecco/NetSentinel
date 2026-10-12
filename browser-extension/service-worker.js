const SETTINGS_KEY = "netsentinelSettings";
const EVENTS_KEY = "netsentinelEvents";
const MAX_EVENTS = 1000;
const DEFAULTS = { enabled: false, capturePages: true, captureSearches: true, retentionDays: 7, excludeDomains: [] };
const SEARCH_QUERY_KEYS = new Set(["q", "query", "text", "wd", "word", "search_query", "search"]);
const TRACKING_QUERY_KEYS = new Set([
  "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ttclid",
  "twclid", "li_fat_id", "mkt_tok", "vero_id", "s_cid", "_ga", "_gl", "_hsenc", "_hsmi"
]);
const SENSITIVE_KEY = /access.?token|refresh.?token|id.?token|client.?secret|client.?assertion|password|passwd|secret|authorization|bearer|api.?key|private.?key|username|email|phone|session|sid|csrf|nonce|signature|redirect.?uri|return.?url|return.?to|returnto|relay.?state|saml.?request|callback|(^|_)(token|auth|code|state|otp|jwt|key|user|account|customer|continue|next)(_|$)/i;

function normalizedDomain(value) {
  return String(value || "").trim().toLowerCase().replace(/^\.+|\.+$/g, "");
}
function hostMatches(host, rule) { return host === rule || host.endsWith("." + rule); }
function privateOrLocalHost(hostname) {
  const host = String(hostname || "").replace(/^\[|\]$/g, "").toLowerCase().replace(/\.$/, "");
  if (!host || host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local") || host.endsWith(".lan")) return true;
  if (host.includes(":")) return host === "::1" || host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:");
  const parts = host.split(".");
  if (parts.length !== 4 || parts.some(part => !/^\d{1,3}$/.test(part) || Number(part) > 255)) return false;
  const [a, b] = parts.map(Number);
  return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}
function isExcluded(hostname, excludeDomains) {
  const host = String(hostname || "").toLowerCase().replace(/\.$/, "");
  if (privateOrLocalHost(host)) return true;
  return (excludeDomains || []).some(entry => {
    const rule = normalizedDomain(entry);
    return rule && hostMatches(host, rule);
  });
}
function normalizedQueryKey(value) {
  let normalized = String(value || "").toLowerCase();
  for (let i = 0; i < 3; i++) {
    let decoded;
    try { decoded = decodeURIComponent(normalized.replace(/\+/g, "%20")); } catch { break; }
    if (decoded === normalized) break;
    normalized = decoded;
  }
  return normalized.replace(/[^a-z0-9_]/g, "");
}
function isSensitivePathSegment(value) {
  let decoded = String(value || "");
  for (let i = 0; i < 3; i++) {
    let expanded;
    try { expanded = decodeURIComponent(decoded); } catch { break; }
    if (expanded === decoded) break;
    decoded = expanded;
  }
  if (/^[^/\s@]+@[^/\s@]+\.[^/\s@]+$/.test(decoded)) return true;
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(decoded)) return true;
  if (/^[+()0-9.\-\s]+$/.test(decoded) && (decoded.match(/\d/g) || []).length >= 10) return true;
  return decoded.length >= 32 && /^[A-Za-z0-9._~-]+$/.test(decoded) && /[A-Za-z]/.test(decoded) && /\d/.test(decoded);
}
function cleanUrl(rawUrl) {
  let url;
  try { url = new URL(rawUrl); } catch { return null; }
  if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) return null;
  url.hash = "";
  url.pathname = url.pathname.split("/").map(segment =>
    isSensitivePathSegment(segment) ? "%5Bredacted%5D" : segment
  ).join("/") || "/";
  for (const key of [...url.searchParams.keys()]) {
    const normalized = normalizedQueryKey(key);
    if (SENSITIVE_KEY.test(normalized) || normalized.startsWith("utm_") ||
        TRACKING_QUERY_KEYS.has(normalized) || SEARCH_QUERY_KEYS.has(normalized)) url.searchParams.delete(key);
  }
  const result = url.toString();
  return result.length <= 2048 ? result : null;
}
function googleHost(host) {
  return host === "google.com" || host.endsWith(".google.com") ||
    /(^|\.)google\.[a-z]{2,3}(\.[a-z]{2})?$/.test(host);
}
function searchInfo(url) {
  const host = url.hostname.toLowerCase();
  let engine = null, key = null;
  if (googleHost(host)) { engine = "Google"; key = "q"; }
  else if (hostMatches(host, "bing.com")) { engine = "Bing"; key = "q"; }
  else if (hostMatches(host, "duckduckgo.com")) { engine = "DuckDuckGo"; key = "q"; }
  else if (host === "search.yahoo.com") { engine = "Yahoo"; key = "p"; }
  else if (hostMatches(host, "ecosia.org")) { engine = "Ecosia"; key = "q"; }
  else if (host === "search.brave.com") { engine = "Brave Search"; key = "q"; }
  else if (hostMatches(host, "yandex.com") || hostMatches(host, "yandex.ru")) { engine = "Yandex"; key = "text"; }
  else if (hostMatches(host, "baidu.com")) { engine = "Baidu"; key = "wd"; }
  else if (hostMatches(host, "youtube.com") && url.pathname === "/results") { engine = "YouTube"; key = "search_query"; }
  else if (hostMatches(host, "wikipedia.org") && url.pathname === "/w/index.php") { engine = "Wikipedia"; key = "search"; }
  else if (/\.amazon\.[a-z.]+$/.test(host) && url.pathname === "/s") { engine = "Amazon"; key = "k"; }
  else if (hostMatches(host, "reddit.com") && url.pathname.startsWith("/search")) { engine = "Reddit"; key = "q"; }
  else if (hostMatches(host, "tiktok.com") && url.pathname.startsWith("/search")) { engine = "TikTok"; key = "q"; }
  if (!engine || !key) return null;
  const terms = String(url.searchParams.get(key) || "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, 500);
  return terms ? { search_engine: engine, search_terms: terms } : null;
}
async function loadState() {
  const stored = await chrome.storage.local.get([SETTINGS_KEY, EVENTS_KEY]);
  const raw = stored[SETTINGS_KEY] || {};
  const settings = {
    ...DEFAULTS, ...raw,
    retentionDays: Math.max(1, Math.min(90, Number(raw.retentionDays || DEFAULTS.retentionDays))),
    excludeDomains: Array.isArray(raw.excludeDomains) ? raw.excludeDomains.map(normalizedDomain).filter(Boolean).slice(0, 100) : []
  };
  const cutoff = Date.now() - settings.retentionDays * 86400000;
  const events = (Array.isArray(stored[EVENTS_KEY]) ? stored[EVENTS_KEY] : [])
    .filter(event => Date.parse(event.observed_at) >= cutoff).slice(-MAX_EVENTS);
  return { settings, events };
}
async function captureNavigation(details) {
  if (details.frameId !== 0 || (chrome.extension && chrome.extension.inIncognitoContext)) return;
  const state = await loadState();
  const { settings } = state;
  if (!settings.enabled || (!settings.capturePages && !settings.captureSearches)) return;
  let url;
  try { url = new URL(details.url); } catch { return; }
  if (!["http:", "https:"].includes(url.protocol) || isExcluded(url.hostname, settings.excludeDomains)) return;
  const pageUrl = cleanUrl(details.url);
  if (!pageUrl) return;
  const domain = url.hostname.toLowerCase().replace(/\.$/, "");
  const timestamp = new Date(Number(details.timeStamp) || Date.now()).toISOString();
  const created = [];
  if (settings.capturePages) created.push({
    observed_at: timestamp, event_type: "page_visit", domain,
    app_name: "NetSentinel Browser Extension (Chromium)", blocked: false, page_url: pageUrl,
    _dedupeKey: "page_visit:" + details.tabId + ":" + pageUrl
  });
  if (settings.captureSearches) {
    const search = searchInfo(url);
    if (search) created.push({
      observed_at: timestamp, event_type: "search_query", domain,
      app_name: "NetSentinel Browser Extension (Chromium)", blocked: false, page_url: pageUrl,
      ...search, _dedupeKey: "search_query:" + details.tabId + ":" + search.search_engine + ":" + search.search_terms
    });
  }
  if (!created.length) return;
  const now = Date.now();
  let events = state.events;
  for (const event of created) {
    const duplicate = events.some(old => old._dedupeKey === event._dedupeKey &&
      Math.abs(now - Date.parse(old.observed_at)) < 4000);
    if (!duplicate) events.push(event);
  }
  events = events.filter(event => Date.parse(event.observed_at) >= now - settings.retentionDays * 86400000).slice(-MAX_EVENTS);
  await chrome.storage.local.set({ [EVENTS_KEY]: events });
}
// Chrome can deliver several navigation events while storage operations are
// pending. Popup cleanup/clear and lifecycle cleanup must use this same queue too:
// chrome.storage.local has no transaction/CAS, so independent read-modify-write
// cycles can overwrite newer events with stale snapshots.
let navigationQueue = Promise.resolve();

function enqueueStorageTask(task) {
  const result = navigationQueue.catch(() => undefined).then(task);
  navigationQueue = result.catch(error => {
    // Do not log URLs or event contents, which may contain sensitive metadata.
    const name = error && typeof error.name === "string" ? error.name : "Error";
    console.error("NetSentinel: fallo una operación de almacenamiento (" + name + ").");
  });
  return result;
}

function enqueueNavigation(details) {
  return enqueueStorageTask(() => captureNavigation(details));
}

function clearStoredEvents() {
  return enqueueStorageTask(() => chrome.storage.local.set({ [EVENTS_KEY]: [] }));
}

function normalizeStoredState() {
  return enqueueStorageTask(async () => {
    const state = await loadState();
    // Only cleanup the event list here. The popup owns settings writes, and a
    // lifecycle cleanup must not race a user's concurrent settings change.
    await chrome.storage.local.set({ [EVENTS_KEY]: state.events });
  });
}

chrome.webNavigation.onCompleted.addListener(details => { void enqueueNavigation(details).catch(() => undefined); });
chrome.webNavigation.onHistoryStateUpdated.addListener(details => { void enqueueNavigation(details).catch(() => undefined); });
chrome.runtime.onStartup.addListener(() => { void normalizeStoredState().catch(() => undefined); });
chrome.runtime.onInstalled.addListener(() => { void normalizeStoredState().catch(() => undefined); });
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "NETSENTINEL_CLEAR_EVENTS") return;
  void clearStoredEvents().then(
    () => sendResponse({ ok: true }),
    () => sendResponse({ ok: false })
  );
  return true;
});

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    SETTINGS_KEY,
    EVENTS_KEY,
    MAX_EVENTS,
    normalizedDomain,
    privateOrLocalHost,
    isExcluded,
    normalizedQueryKey,
    isSensitivePathSegment,
    cleanUrl,
    searchInfo,
    loadState,
    captureNavigation,
    enqueueNavigation,
    clearStoredEvents,
    enqueueStorageTask
  };
}
