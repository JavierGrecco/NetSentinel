const test = require("node:test");
const assert = require("node:assert/strict");

function listenerSlot() {
  return {
    listener: null,
    addListener(listener) { this.listener = listener; }
  };
}

let mockStore = {};
// These minimal Chrome mocks let us exercise the real service worker in Node
// without opening a browser profile or touching a user's browsing data.
global.chrome = {
  storage: {
    local: {
      async get(keys) {
        if (!Array.isArray(keys)) return { ...mockStore };
        return Object.fromEntries(keys
          .filter(key => Object.prototype.hasOwnProperty.call(mockStore, key))
          .map(key => [key, mockStore[key]]));
      },
      async set(values) { Object.assign(mockStore, values); }
    }
  },
  webNavigation: { onCompleted: listenerSlot(), onHistoryStateUpdated: listenerSlot() },
  runtime: { onStartup: listenerSlot(), onInstalled: listenerSlot(), onMessage: listenerSlot() },
  extension: { inIncognitoContext: false }
};

const {
  SETTINGS_KEY,
  EVENTS_KEY,
  MAX_EVENTS,
  normalizeRetentionDays,
  normalizeStoredBoolean,
  captureNavigation,
  cleanUrl,
  isExcluded,
  loadState,
  enqueueNavigation,
  clearStoredEvents,
  privateOrLocalHost,
  sanitizeStoredEvent,
  searchInfo
} = require("./service-worker.js");

function setState(settings, events = []) {
  mockStore = { [SETTINGS_KEY]: settings, [EVENTS_KEY]: events };
  global.chrome.extension.inIncognitoContext = false;
}
function enabledSettings(overrides = {}) {
  return {
    enabled: true,
    capturePages: true,
    captureSearches: true,
    retentionDays: 7,
    excludeDomains: [],
    ...overrides
  };
}

test("removes OAuth, double-encoded token, tracking, search query and fragment data", () => {
  const raw = "HTTPS://Example.COM:443/docs?lang=es&access%255Ftoken=secret&state=oauth-state" +
    "&redirect_uri=https%3A%2F%2Fid.example%2Fcallback%3Femail%3Da%2540b.com" +
    "&utm_source=mail&fbclid=click-id#section";
  assert.equal(cleanUrl(raw), "https://example.com/docs?lang=es");
});

test("removes expanded tracking parameters but preserves non-sensitive parameters", () => {
  const raw = "https://example.com/feed?gclid=ad-click&_gl=analytics&_ga=analytics-id" +
    "&ttclid=tiktok-click&sort=recent";
  assert.equal(cleanUrl(raw), "https://example.com/feed?sort=recent");
});

test("redacts email, phone, UUID and opaque token path segments", () => {
  assert.equal(
    cleanUrl("https://example.com/users/jane%40example.com/profile?view=public"),
    "https://example.com/users/%5Bredacted%5D/profile?view=public"
  );
  assert.equal(
    cleanUrl("https://example.com/contact/%2B549112223344?view=compact"),
    "https://example.com/contact/%5Bredacted%5D?view=compact"
  );
  assert.equal(
    cleanUrl("https://example.com/sessions/550e8400-e29b-41d4-a716-446655440000"),
    "https://example.com/sessions/%5Bredacted%5D"
  );
  assert.equal(
    cleanUrl("https://example.com/reset/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ABCDEFGHIJKLMNOPQRST0123456789.ABCDEFGHIJKLMNOPQRST0123456789"),
    "https://example.com/reset/%5Bredacted%5D"
  );
});

test("canonicalizes IPv6, removes default port and drops fragment", () => {
  assert.equal(
    cleanUrl("https://[2001:0db8:0:0:0:0:0:1]:443/docs?lang=es#top"),
    "https://[2001:db8::1]/docs?lang=es"
  );
});

test("normalizes one DNS root dot and rejects malformed or overlong hostnames", () => {
  assert.equal(cleanUrl("https://Example.com./docs"), "https://example.com/docs");
  assert.equal(cleanUrl("https://example.com../docs"), null);
  assert.equal(cleanUrl("https://.example.com/docs"), null);
  assert.equal(cleanUrl("https://" + "a".repeat(64) + ".example/docs"), null);

  // Every label is within 63 characters, but the ASCII hostname exceeds 253.
  const overlongHostname = Array(4).fill("a".repeat(63)).join(".");
  assert.equal(overlongHostname.length, 255);
  assert.equal(cleanUrl("https://" + overlongHostname + "/docs"), null);
});

test("rejects non-HTTP schemes and URLs with embedded credentials", () => {
  assert.equal(cleanUrl("javascript:alert(1)"), null);
  assert.equal(cleanUrl("file:///Users/example/private.txt"), null);
  assert.equal(cleanUrl("https://alice:password@example.com/profile"), null);
});

test("matches backend query-field limit and accepts the exact boundary", () => {
  const atLimit = new URL("https://example.com/");
  for (let i = 0; i < 200; i++) atLimit.searchParams.append("a", "1");
  assert.equal(new URL(cleanUrl(atLimit.toString())).searchParams.size, 200);

  const overLimit = new URL("https://example.com/");
  for (let i = 0; i < 201; i++) overLimit.searchParams.append("a", "1");
  assert.equal(cleanUrl(overLimit.toString()), null);
});

test("enforces query-field limit before removing sensitive parameters", () => {
  const url = new URL("https://example.com/");
  for (let i = 0; i < 200; i++) url.searchParams.append("lang", "es");
  url.searchParams.append("access_token", "sensitive");
  // The backend counts parameters before filtering, so the extension must too.
  assert.equal(cleanUrl(url.toString()), null);
});


test("excludes local/private, shared and special-use IPv4 plus IPv6 and mapped IPv6 hosts", () => {
  for (const host of [
    "0.0.0.1", "10.0.0.1", "127.0.0.1", "169.254.1.1",
    "172.16.0.1", "172.31.255.254", "192.168.1.1",
    "100.64.0.1", "100.127.255.254", "192.0.2.1",
    "192.0.0.1", "192.0.0.8", "192.0.0.170", "192.88.99.1",
    "198.18.0.1", "198.19.255.254", "198.51.100.1",
    "203.0.113.1", "224.0.0.1", "240.0.0.1"
  ]) {
    assert.equal(privateOrLocalHost(host), true, host + " must not be captured as a public destination");
  }
  assert.equal(privateOrLocalHost("100.63.255.255"), false, "the lower CGNAT boundary is public-use");
  assert.equal(privateOrLocalHost("100.128.0.1"), false, "the upper CGNAT boundary is outside 100.64/10");
  assert.equal(privateOrLocalHost("192.0.0.9"), false, "IANA global-reachability exception must remain eligible");
  assert.equal(privateOrLocalHost("192.0.0.10"), false, "IANA global-reachability exception must remain eligible");
  assert.equal(privateOrLocalHost("192.88.98.255"), false, "outside deprecated 192.88.99.0/24");
  assert.equal(privateOrLocalHost("8.8.8.8"), false);
  assert.equal(privateOrLocalHost("router.local."), true);
  assert.equal(privateOrLocalHost("[::1]"), true);
  assert.equal(privateOrLocalHost("::"), true);
  assert.equal(privateOrLocalHost("fd12::1"), true);
  assert.equal(privateOrLocalHost("fe81::1"), true, "the complete fe80::/10 link-local range is excluded");
  assert.equal(privateOrLocalHost("febf::1"), true, "the upper bound of the link-local range is excluded");
  assert.equal(privateOrLocalHost("[::ffff:c0a8:101]"), true, "mapped 192.168.1.1 must not be captured");
  assert.equal(privateOrLocalHost("[::ffff:6440:1]"), true, "mapped 100.64.0.1 CGNAT must not be captured");
  assert.equal(privateOrLocalHost("[::ffff:cb00:7101]"), true, "mapped 203.0.113.1 documentation IP must not be captured");
  assert.equal(privateOrLocalHost("[::ffff:0808:0808]"), false, "mapped public 8.8.8.8 is not classified as private");
  assert.equal(isExcluded("sub.example.com.", ["example.com"]), true);
  assert.equal(isExcluded("public.example.net", ["example.com"]), false);
});

test("filters reserved local-use DNS suffixes but not ordinary public subdomains", () => {
  for (const host of [
    "localhost", "printer.local", "router.lan", "service.localdomain",
    "preview.test", "docs.example", "bad.invalid", "host.arpa", "gateway.home.arpa"
  ]) {
    assert.equal(privateOrLocalHost(host), true, host + " should be treated as local/test naming");
  }
  assert.equal(privateOrLocalHost("example.com"), false);
  assert.equal(privateOrLocalHost("test.example.com"), false, "a reserved suffix must match the whole host suffix");
});

test("excludes special-use IPv6 ranges but preserves ordinary global unicast", () => {
  for (const host of [
    "[ff02::1]",                    // multicast
    "[2001:db8::1]",                // documentation
    "[3fff:0::1]",                  // expanded documentation space (RFC 9637)
    "[2001:2::1]",                  // benchmarking
    "[100::1]",                     // discard-only
    "[100:0:0:1::1]",              // dummy IPv6 prefix (RFC 9780)
    "[2001:10::1]",                // deprecated ORCHID
    "[2001:10:f::1]",              // upper address range still inside /28
    "[2001:10:10::1]",             // /28 prefix applies to the second hextet, not the third
    "[2001:1f:ffff::1]",           // upper boundary of deprecated ORCHID /28
    "[2001:20::1]",                // first address range of ORCHIDv2 /28 (RFC 7343)
    "[2001:2f:ffff::1]",           // upper boundary of ORCHIDv2 /28
    "[5f00::1]",                   // SRv6 Segment Routing SIDs
    "[2001::1]",                    // Teredo
    "[2002:c000:0204::1]",          // 6to4
    "[64:ff9b:1::1]",               // local-use NAT64
    "[0:0:0:0:0:ffff:c0a8:101]",    // expanded mapped private IPv4
    "[::ffff:192.168.1.1]"          // dotted mapped private IPv4
  ]) {
    assert.equal(privateOrLocalHost(host), true, host + " must not be captured as an ordinary public destination");
  }
  for (const host of [
    "[2001:4860:4860::8888]",       // ordinary global unicast
    "[2001:2:1::1]",                // just outside 2001:2::/48
    "[2001:30::1]",                // just outside both ORCHID /28 ranges
    "[5eff:ffff::1]",              // just outside SRv6 prefix
    "[3fff:1000::1]",               // just outside 3fff::/20
    "[100:0:0:2::1]",               // just outside dummy and discard-only prefixes
    "[::ffff:0808:0808]",           // mapped public 8.8.8.8
    "[::ffff:8.8.8.8]"              // dotted mapped public IPv4
  ]) {
    assert.equal(privateOrLocalHost(host), false, host + " should remain eligible");
  }
});

test("recognizes Google search terms separately from the sanitized page URL", () => {
  const url = new URL("https://www.google.com/search?q=private+search&lang=es");
  assert.deepEqual(searchInfo(url), { search_engine: "Google", search_terms: "private search" });
  assert.equal(cleanUrl(url.toString()), "https://www.google.com/search?lang=es");
});

test("sanitizer preserves unknown non-sensitive path and query values", () => {
  const raw = "https://example.com/profile/javier?tab=overview&sort=recent";
  assert.equal(cleanUrl(raw), raw);
});


test("sanitizes historical stored events before exposing them", async () => {
  const timestamp = new Date().toISOString();
  const oldEvent = {
    observed_at: timestamp,
    event_type: "page_visit",
    domain: "wrong.example",
    page_url: "https://Example.com./users/alice%40private.org?access_token=legacy-secret&lang=es#private-fragment",
    app_name: "old raw value with personal data",
    blocked: true,
    email_body: "must-not-survive-migration",
    _dedupeKey: "page_visit:27:https://Example.com/users/alice%40private.org?access_token=legacy-secret"
  };
  setState(enabledSettings(), [oldEvent]);

  const state = await loadState();
  assert.equal(state.events.length, 1);
  const safe = state.events[0];
  assert.equal(safe.page_url, "https://example.com/users/%5Bredacted%5D?lang=es");
  assert.equal(safe.domain, "example.com", "domain must come from the canonical URL, not stale stored metadata");
  assert.equal(safe.app_name, "NetSentinel Browser Extension (Chromium)");
  assert.equal(safe.blocked, false);
  assert.equal(safe._dedupeKey, "page_visit:27:" + safe.page_url);
  assert.doesNotMatch(JSON.stringify(safe), /legacy-secret|private-fragment|private\.org|must-not-survive|wrong\.example/i);
  assert.equal(mockStore[EVENTS_KEY][0], oldEvent, "loadState must remain read-only until migration is committed under the queue");
});

test("drops legacy records with private URLs, malformed hostnames, unsupported types or invalid search metadata", async () => {
  const timestamp = new Date().toISOString();
  const base = { observed_at: timestamp, event_type: "page_visit", page_url: "https://example.com/path" };
  for (const bad of [
    { ...base, page_url: "http://192.168.1.1/admin" },
    { ...base, page_url: "https://example.com../path" },
    { ...base, event_type: "raw_payload" },
    { ...base, event_type: "search_query", search_engine: "Unknown", search_terms: "query" },
    { ...base, event_type: "search_query", search_engine: "Google", search_terms: "   " }
  ]) {
    assert.equal(sanitizeStoredEvent(bad, Date.now() - 86400000), null);
  }
});

test("normalizes legacy search metadata and IP-literal page domains safely", () => {
  const timestamp = new Date().toISOString();
  const search = sanitizeStoredEvent({
    observed_at: timestamp, event_type: "search_query", page_url: "https://www.google.com/search",
    search_engine: "Google", search_terms: "  hello\tworld\u0000  "
  });
  assert.equal(search.search_terms, "hello world");
  assert.equal(search.domain, "www.google.com");
  const ipPage = sanitizeStoredEvent({
    observed_at: timestamp, event_type: "page_visit", page_url: "https://8.8.8.8/help", domain: "8.8.8.8"
  });
  assert.equal(ipPage.domain, "", "IP literals belong in page_url, not the DNS domain field");
});

test("safe-event message persists sanitized legacy events without losing concurrent navigation", async () => {
  const observedAt = new Date().toISOString();
  const legacy = {
    observed_at: observedAt,
    event_type: "page_visit",
    domain: "stale.example",
    page_url: "https://example.com/account?access_token=legacy-secret#private",
    email_body: "must-not-persist"
  };
  setState(enabledSettings(), [legacy]);

  let response;
  const handler = global.chrome.runtime.onMessage.listener;
  assert.equal(typeof handler, "function", "service worker must register its message handler");
  assert.equal(
    handler({ type: "NETSENTINEL_GET_SAFE_EVENTS" }, {}, value => { response = value; }),
    true,
    "asynchronous response must keep the message channel open"
  );

  const navigation = enqueueNavigation({
    frameId: 0,
    tabId: 778,
    url: "https://example.net/new-navigation",
    timeStamp: Date.now()
  });
  await navigation;

  assert.ok(response && response.ok, "background should respond successfully after migration");
  assert.equal(response.events.length, 1, "the migration response should contain the prior safe event only");
  assert.equal(response.events[0].page_url, "https://example.com/account");
  assert.equal(response.events[0].domain, "example.com");
  assert.doesNotMatch(JSON.stringify(response.events), /legacy-secret|private|must-not-persist|stale\.example/i);

  const persisted = mockStore[EVENTS_KEY];
  assert.equal(persisted.length, 2, "the sanitized old event and new navigation must both be persisted");
  assert.equal(persisted[0].page_url, "https://example.com/account");
  assert.equal(persisted[1].page_url, "https://example.net/new-navigation");
  assert.doesNotMatch(JSON.stringify(persisted), /legacy-secret|private|must-not-persist|stale\.example/i);
});

test("capture is disabled by default and performs no storage write", async () => {
  mockStore = {};
  await captureNavigation({
    frameId: 0, tabId: 1, url: "https://example.com/home", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY], undefined);
});

test("opt-in capture stores sanitized page and separate search metadata", async () => {
  setState(enabledSettings(), []);
  const url = "https://www.google.com/search?q=private+search&access%255Ftoken=secret&utm_source=mail#fragment";
  await captureNavigation({ frameId: 0, tabId: 42, url, timeStamp: Date.now() });

  let events = mockStore[EVENTS_KEY];
  assert.equal(events.length, 2);
  const page = events.find(event => event.event_type === "page_visit");
  const search = events.find(event => event.event_type === "search_query");
  assert.equal(page.page_url, "https://www.google.com/search");
  assert.doesNotMatch(page.page_url, /private|secret|access|utm/i);
  assert.equal(search.search_engine, "Google");
  assert.equal(search.search_terms, "private search");
  assert.equal(search.page_url, "https://www.google.com/search");

  await captureNavigation({ frameId: 0, tabId: 42, url, timeStamp: Date.now() });
  events = mockStore[EVENTS_KEY];
  assert.equal(events.length, 2, "rapid duplicate navigation should not be added twice");
});

test("capture drops malformed DNS hostnames before persisting browser metadata", async () => {
  setState(enabledSettings(), []);
  for (const url of [
    "https://example.com../profile",
    "https://.example.com/profile",
    "https://" + "a".repeat(64) + ".example/profile",
    "https://" + Array(4).fill("b".repeat(63)).join(".") + "/profile"
  ]) {
    await captureNavigation({ frameId: 0, tabId: 405, url, timeStamp: Date.now() });
  }
  assert.equal(mockStore[EVENTS_KEY].length, 0);
});

test("capture ignores subframes, private browsing and non-HTTP(S) URLs", async () => {
  setState(enabledSettings(), []);
  await captureNavigation({
    frameId: 1, tabId: 4, url: "https://example.com/frame", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY].length, 0);

  global.chrome.extension.inIncognitoContext = true;
  await captureNavigation({
    frameId: 0, tabId: 4, url: "https://example.com/private", timeStamp: Date.now()
  });
  global.chrome.extension.inIncognitoContext = false;
  await captureNavigation({
    frameId: 0, tabId: 4, url: "file:///Users/example/private.txt", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY].length, 0);
});

test("domain exclusions apply to subdomains and trailing-dot hosts", async () => {
  setState(enabledSettings({ excludeDomains: ["example.com"] }), []);
  await captureNavigation({
    frameId: 0, tabId: 5, url: "https://sub.example.com./home", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY].length, 0);
});

test("page and search capture options can be disabled independently", async () => {
  setState(enabledSettings({ capturePages: false, captureSearches: true }), []);
  await captureNavigation({
    frameId: 0, tabId: 6, url: "https://www.google.com/search?q=only+search", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY].length, 1);
  assert.equal(mockStore[EVENTS_KEY][0].event_type, "search_query");

  setState(enabledSettings({ capturePages: true, captureSearches: false }), []);
  await captureNavigation({
    frameId: 0, tabId: 7, url: "https://www.google.com/search?q=no+search+record", timeStamp: Date.now()
  });
  assert.equal(mockStore[EVENTS_KEY].length, 1);
  assert.equal(mockStore[EVENTS_KEY][0].event_type, "page_visit");
  assert.equal(mockStore[EVENTS_KEY][0].page_url, "https://www.google.com/search");
});

test("stored event retention and event limit are enforced when loading state", async () => {
  const now = Date.now();
  const old = { event_type: "page_visit", observed_at: new Date(now - 2 * 86400000).toISOString() };
  const freshEvents = Array.from({ length: MAX_EVENTS + 1 }, (_, i) => ({
    event_type: "page_visit",
    observed_at: new Date(now - i).toISOString(),
    page_url: "https://example.com/item/" + i,
    marker: i
  }));
  setState(enabledSettings({ retentionDays: 1 }), [old, ...freshEvents]);
  const state = await loadState();
  assert.equal(state.settings.retentionDays, 1);
  assert.equal(state.events.length, MAX_EVENTS);
  assert.equal(state.events.some(event => event === old), false);
});


test("concurrent navigation notifications are serialized without losing events", async () => {
  setState(enabledSettings(), []);
  const baseTime = Date.now();

  await Promise.all([
    enqueueNavigation({
      frameId: 0,
      tabId: 101,
      url: "https://example.com/first",
      timeStamp: baseTime
    }),
    enqueueNavigation({
      frameId: 0,
      tabId: 202,
      url: "https://example.net/second",
      timeStamp: baseTime + 1
    }),
    enqueueNavigation({
      frameId: 0,
      tabId: 303,
      url: "https://example.org/third",
      timeStamp: baseTime + 2
    })
  ]);

  const pages = mockStore[EVENTS_KEY].filter(event => event.event_type === "page_visit");
  assert.equal(pages.length, 3, "each distinct navigation must survive concurrent storage updates");
  assert.deepEqual(
    new Set(pages.map(event => event.page_url)),
    new Set([
      "https://example.com/first",
      "https://example.net/second",
      "https://example.org/third"
    ])
  );
});


test("event clearing shares the queue with navigation writes", async () => {
  setState(enabledSettings(), []);
  const baseTime = Date.now();

  await Promise.all([
    enqueueNavigation({
      frameId: 0,
      tabId: 401,
      url: "https://example.com/before-clear",
      timeStamp: baseTime
    }),
    clearStoredEvents(),
    enqueueNavigation({
      frameId: 0,
      tabId: 402,
      url: "https://example.net/after-clear",
      timeStamp: baseTime + 1
    })
  ]);

  const pages = mockStore[EVENTS_KEY].filter(event => event.event_type === "page_visit");
  assert.equal(pages.length, 1);
  assert.equal(pages[0].page_url, "https://example.net/after-clear");
});


test("corrupt or non-integer retention settings fall back instead of dropping saved events", async () => {
  const now = Date.now();
  const retainedEvent = {
    event_type: "page_visit",
    observed_at: new Date(now - 3 * 86400000).toISOString(),
    page_url: "https://example.com/retained"
  };

  for (const badValue of ["not-a-number", {}, true, 1.5]) {
    setState(enabledSettings({ retentionDays: badValue }), [retainedEvent]);
    const state = await loadState();
    assert.equal(state.settings.retentionDays, 7, "invalid setting should use the default");
    assert.equal(state.events.length, 1, "the event is inside the default retention window");
  }
});

test("retention normalization accepts integer values and clamps supported bounds", () => {
  assert.equal(normalizeRetentionDays(1), 1);
  assert.equal(normalizeRetentionDays("7"), 7);
  assert.equal(normalizeRetentionDays(90), 90);
  assert.equal(normalizeRetentionDays(0), 1);
  assert.equal(normalizeRetentionDays(120), 90);
  assert.equal(normalizeRetentionDays("bad"), 7);
  assert.equal(normalizeRetentionDays(true), 7);
  assert.equal(normalizeRetentionDays(1.5), 7);
});


test("loadState and navigation safely discard malformed stored event records", async () => {
  const now = Date.now();
  const retained = {
    event_type: "page_visit",
    observed_at: new Date(now - 3 * 86400000).toISOString(),
    page_url: "https://example.com/retained"
  };
  const malformed = [
    null,
    undefined,
    "not-an-event",
    [],
    { observed_at: "not-a-date", event_type: "page_visit" }
  ];
  setState(enabledSettings(), [...malformed, retained]);

  const state = await loadState();
  assert.equal(state.events.length, 1, "only valid, in-retention event objects should be returned");
  assert.equal(state.events[0].page_url, retained.page_url);
  assert.equal(state.events[0].domain, "example.com");
  assert.equal(state.events[0].app_name, "NetSentinel Browser Extension (Chromium)");

  await captureNavigation({
    frameId: 0,
    tabId: 707,
    url: "https://example.net/new-event",
    timeStamp: Date.now()
  });
  const persisted = mockStore[EVENTS_KEY];
  assert.equal(persisted.some(event => event === null || event === undefined), false);
  assert.deepEqual(
    persisted.map(event => event.page_url),
    ["https://example.com/retained", "https://example.net/new-event"]
  );
});


test("stored capture switches require booleans and fail closed on corrupted values", async () => {
  const activeEvent = {
    event_type: "page_visit",
    observed_at: new Date().toISOString(),
    page_url: "https://example.com/should-not-capture"
  };

  for (const invalidEnabled of ["false", "true", "0", 1, {}, []]) {
    setState(enabledSettings({ enabled: invalidEnabled }), [activeEvent]);
    const state = await loadState();
    assert.equal(state.settings.enabled, false, "malformed enabled flag must not turn tracking on");
    await captureNavigation({
      frameId: 0, tabId: 909, url: "https://example.net/private", timeStamp: Date.now()
    });
    assert.deepEqual(mockStore[EVENTS_KEY], [activeEvent], "navigation must not write while the opt-in flag is corrupt");
  }

  for (const flag of ["capturePages", "captureSearches"]) {
    for (const invalidValue of ["false", "true", 1, {}, []]) {
      setState(enabledSettings({ [flag]: invalidValue }), []);
      const state = await loadState();
      assert.equal(state.settings[flag], false, flag + " with corrupt storage must be disabled");
    }
  }
});

test("missing stored switches keep documented defaults and the boolean helper is strict", async () => {
  setState({});
  const state = await loadState();
  assert.equal(state.settings.enabled, false);
  assert.equal(state.settings.capturePages, true);
  assert.equal(state.settings.captureSearches, true);

  assert.equal(normalizeStoredBoolean({ enabled: true }, "enabled", false), true);
  assert.equal(normalizeStoredBoolean({ enabled: false }, "enabled", true), false);
  assert.equal(normalizeStoredBoolean({}, "enabled", false), false);
  assert.equal(normalizeStoredBoolean({ enabled: "true" }, "enabled", false), false);
  assert.equal(normalizeStoredBoolean({ enabled: "false" }, "enabled", true), false);
});
