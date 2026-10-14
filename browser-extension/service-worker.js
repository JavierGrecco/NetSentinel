const SETTINGS_KEY = "netsentinelSettings";
const EVENTS_KEY = "netsentinelEvents";
const MAX_EVENTS = 1000;
const MAX_QUERY_PARAMETERS = 200; // Must match the backend CSV URL parser limit.
const MAX_SAFE_URL_LENGTH = 2048; // Must match activity_tracking._safe_page_url.
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

function normalizeRetentionDays(value) {
  // Storage is persistent but not type-safe: tolerate old/corrupt values without
  // letting NaN turn the retention cutoff into a filter that discards every event.
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
  // Storage can contain stale or malformed records. Reject them before UI or
  // navigation code reads their fields; keep valid records inside the window.
  if (!event || typeof event !== "object" || Array.isArray(event)) return false;
  let observedAt;
  try { observedAt = Date.parse(event.observed_at); } catch { return false; }
  return Number.isFinite(observedAt) && observedAt >= cutoff;
}
function hostMatches(host, rule) { return host === rule || host.endsWith("." + rule); }
function isPrivateOrLocalIPv4(host) {
  const parts = String(host || "").split(".");
  if (parts.length !== 4 || parts.some(part => !/^\d{1,3}$/.test(part) || Number(part) > 255)) return false;
  const [a, b, c, d] = parts.map(Number);
  // Suppress common non-public ranges as well as RFC1918: shared CGNAT,
  // documentation/test networks, benchmarking, multicast and reserved space.
  return a === 0 || a === 10 || a === 127 ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    // Most of 192.0.0.0/24 is special-purpose; preserve IANA global exceptions .9 and .10.
    (a === 192 && b === 0 && c === 0 && d !== 9 && d !== 10) ||
    (a === 192 && b === 88 && c === 99) || // deprecated 6to4 relay anycast
    (a === 192 && b === 168) ||
    (a === 192 && b === 0 && c === 2) ||
    (a === 198 && (b === 18 || b === 19)) ||
    (a === 198 && b === 51 && c === 100) ||
    (a === 203 && b === 0 && c === 113) ||
    a >= 224;
}

function mappedIPv4FromIPv6(host) {
  const value = String(host || "").replace(/^\[|\]$/g, "").toLowerCase();
  if (!value.startsWith("::ffff:")) return null;
  const suffix = value.slice("::ffff:".length);
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(suffix)) {
    const octets = suffix.split(".").map(Number);
    return octets.every(part => part >= 0 && part <= 255) ? octets.join(".") : null;
  }
  const groups = suffix.split(":");
  if (groups.length !== 2 || groups.some(group => !/^[0-9a-f]{1,4}$/.test(group))) return null;
  const high = Number.parseInt(groups[0], 16);
  const low = Number.parseInt(groups[1], 16);
  return [high >> 8, high & 255, low >> 8, low & 255].join(".");
}

// Parse an IPv6 literal into eight 16-bit words. Invalid or unusual spellings
// are rejected by the caller rather than treated as confirmed public hosts.
function ipv6Words(host) {
  const value = String(host || "").replace(/^\[|\]$/g, "").toLowerCase();
  if (!value.includes(":") || value.includes(".")) return null;
  const marker = value.indexOf("::");
  if (marker >= 0 && value.indexOf("::", marker + 2) >= 0) return null;
  const compressed = marker >= 0;
  const sides = compressed ? value.split("::") : [value];
  const parseSide = side => {
    if (!side) return [];
    const groups = side.split(":");
    if (groups.some(group => !/^[0-9a-f]{1,4}$/.test(group))) return null;
    return groups.map(group => Number.parseInt(group, 16));
  };
  const left = parseSide(sides[0]);
  const right = compressed ? parseSide(sides[1]) : [];
  if (left === null || right === null) return null;
  const explicitCount = left.length + right.length;
  if ((!compressed && explicitCount !== 8) || (compressed && explicitCount >= 8)) return null;
  return [...left, ...Array(compressed ? 8 - explicitCount : 0).fill(0), ...right];
}

function mappedIPv4FromWords(words) {
  if (!words || !words.slice(0, 5).every(word => word === 0) || words[5] !== 0xffff) return null;
  return [
    words[6] >> 8, words[6] & 255,
    words[7] >> 8, words[7] & 255
  ].join(".");
}

const NON_PUBLIC_HOST_SUFFIXES = [
  "localhost", "local", "lan", "localdomain", "test", "example", "invalid", "arpa"
];

function privateOrLocalHost(hostname) {
  const host = String(hostname || "").replace(/^\[|\]$/g, "").toLowerCase().replace(/\.$/, "");
  if (!host || NON_PUBLIC_HOST_SUFFIXES.some(suffix => host === suffix || host.endsWith("." + suffix))) return true;
  // home.arpa is reserved for home-network naming; .arpa is filtered above too.
  if (!host.includes(":")) return isPrivateOrLocalIPv4(host);

  // IPv4-mapped IPv6 spellings can hide a non-public IPv4 destination.
  const mappedIPv4 = mappedIPv4FromIPv6(host);
  if (mappedIPv4 !== null) return isPrivateOrLocalIPv4(mappedIPv4);
  const words = ipv6Words(host);
  if (!words) return true; // fail closed if the IPv6 literal cannot be classified
  const mappedWordsIPv4 = mappedIPv4FromWords(words);
  if (mappedWordsIPv4 !== null) return isPrivateOrLocalIPv4(mappedWordsIPv4);

  const allZero = words.every(word => word === 0);
  const loopback = words.slice(0, 7).every(word => word === 0) && words[7] === 1;
  const uniqueLocal = (words[0] & 0xfe00) === 0xfc00;      // fc00::/7
  const linkLocal = (words[0] & 0xffc0) === 0xfe80;       // fe80::/10
  const multicast = (words[0] & 0xff00) === 0xff00;       // ff00::/8
  const documentation = (words[0] === 0x2001 && words[1] === 0x0db8) ||
    (words[0] === 0x3fff && (words[1] & 0xf000) === 0); // 2001:db8::/32 and 3fff::/20
  const benchmarking = words[0] === 0x2001 && words[1] === 0x0002 && words[2] === 0;
  const discardOnly = words[0] === 0x0100 && words.slice(1, 4).every(word => word === 0); // 100::/64
  const teredo = words[0] === 0x2001 && words[1] === 0;  // 2001::/32
  const sixToFour = words[0] === 0x2002;                 // 2002::/16
  const localUseNat64 = words[0] === 0x0064 && words[1] === 0xff9b && words[2] === 1; // 64:ff9b:1::/48
  const dummyPrefix = words[0] === 0x0100 && words[1] === 0 && words[2] === 0 && words[3] === 1; // 100:0:0:1::/64
  const deprecatedOrchid = words[0] === 0x2001 && words[1] === 0x0010 && (words[2] & 0xfff0) === 0; // 2001:10::/28
  const segmentRouting = words[0] === 0x5f00; // 5f00::/16
  const deprecatedIPv4Compatible = words.slice(0, 6).every(word => word === 0);

  // Keep ordinary globally-routed IPv6 hosts eligible; suppress well-known
  // special-use, multicast, documentation, transition, and local-use prefixes.
  return allZero || loopback || uniqueLocal || linkLocal || multicast ||
    documentation || benchmarking || discardOnly || dummyPrefix || teredo || sixToFour ||
    localUseNat64 || deprecatedOrchid || segmentRouting || deprecatedIPv4Compatible;
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
  // Decode nested percent-encoding, but never keep a key that remains encoded
  // after the bounded pass: otherwise a sensitive name could evade the filter.
  for (let i = 0; i < 8 && normalized.includes("%"); i++) {
    try {
      normalized = decodeURIComponent(normalized.replace(/\+/g, "%20"));
    } catch {
      return null;
    }
  }
  if (normalized.includes("%")) return null;
  return normalized.replace(/[^a-z0-9_]/g, "");
}
function isSensitivePathSegment(value) {
  let decoded = String(value || "");
  for (let i = 0; i < 8; i++) {
    let expanded;
    try { expanded = decodeURIComponent(decoded); } catch {
      return decoded.includes("%");
    }
    if (expanded === decoded) break;
    decoded = expanded;
  }
  // Redact a segment if nested/malformed percent encoding prevents reliable inspection.
  if (decoded.includes("%")) return true;
  if (/^[^/\s@]+@[^/\s@]+\.[^/\s@]+$/.test(decoded)) return true;
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(decoded)) return true;
  if (/^[+()0-9.\-\s]+$/.test(decoded) && (decoded.match(/\d/g) || []).length >= 10) return true;
  return decoded.length >= 32 && /^[A-Za-z0-9._~-]+$/.test(decoded) && /[A-Za-z]/.test(decoded) && /\d/.test(decoded);
}
function cleanUrl(rawUrl) {
  let url;
  try { url = new URL(rawUrl); } catch { return null; }
  if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) return null;

  // The backend uses parse_qsl(max_num_fields=200) before removing sensitive
  // query keys. Match that limit here so an exported CSV cannot fail import just
  // because the original navigation carried too many parameters.
  let queryFieldCount = 0;
  for (const _entry of url.searchParams) {
    if (++queryFieldCount > MAX_QUERY_PARAMETERS) return null;
  }

  url.hash = "";
  url.pathname = url.pathname.split("/").map(segment =>
    isSensitivePathSegment(segment) ? "%5Bredacted%5D" : segment
  ).join("/") || "/";
  for (const key of [...url.searchParams.keys()]) {
    const normalized = normalizedQueryKey(key);
    if (normalized === null || SENSITIVE_KEY.test(normalized) || normalized.startsWith("utm_") ||
        TRACKING_QUERY_KEYS.has(normalized) || SEARCH_QUERY_KEYS.has(normalized)) url.searchParams.delete(key);
  }
  const result = url.toString();
  return result.length <= MAX_SAFE_URL_LENGTH ? result : null;
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
  const savedSettings = stored[SETTINGS_KEY];
  const raw = savedSettings && typeof savedSettings === "object" && !Array.isArray(savedSettings)
    ? savedSettings
    : {};
  const settings = {
    ...DEFAULTS, ...raw,
    enabled: normalizeStoredBoolean(raw, "enabled", DEFAULTS.enabled),
    capturePages: normalizeStoredBoolean(raw, "capturePages", DEFAULTS.capturePages),
    captureSearches: normalizeStoredBoolean(raw, "captureSearches", DEFAULTS.captureSearches),
    retentionDays: normalizeRetentionDays(raw.retentionDays),
    excludeDomains: Array.isArray(raw.excludeDomains) ? raw.excludeDomains.map(normalizedDomain).filter(Boolean).slice(0, 100) : []
  };
  const cutoff = Date.now() - settings.retentionDays * 86400000;
  const events = (Array.isArray(stored[EVENTS_KEY]) ? stored[EVENTS_KEY] : [])
    .filter(event => isRetainedEvent(event, cutoff)).slice(-MAX_EVENTS);
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
  events = events.filter(event => isRetainedEvent(event, now - settings.retentionDays * 86400000)).slice(-MAX_EVENTS);
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
    normalizeRetentionDays,
    normalizeStoredBoolean,
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
