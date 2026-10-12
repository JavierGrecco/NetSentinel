const test = require("node:test");
const assert = require("node:assert/strict");

function listenerSlot() {
  return { addListener() {} };
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
  runtime: { onStartup: listenerSlot(), onInstalled: listenerSlot() },
  extension: { inIncognitoContext: false }
};

const {
  SETTINGS_KEY,
  EVENTS_KEY,
  MAX_EVENTS,
  captureNavigation,
  cleanUrl,
  isExcluded,
  loadState,
  enqueueNavigation,
  privateOrLocalHost,
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

test("rejects non-HTTP schemes and URLs with embedded credentials", () => {
  assert.equal(cleanUrl("javascript:alert(1)"), null);
  assert.equal(cleanUrl("file:///Users/example/private.txt"), null);
  assert.equal(cleanUrl("https://alice:password@example.com/profile"), null);
});

test("excludes local/private hosts and applies domain exclusions to trailing-dot hostnames", () => {
  assert.equal(privateOrLocalHost("router.local."), true);
  assert.equal(privateOrLocalHost("[::1]"), true);
  assert.equal(privateOrLocalHost("fd12::1"), true);
  assert.equal(isExcluded("sub.example.com.", ["example.com"]), true);
  assert.equal(isExcluded("public.example.net", ["example.com"]), false);
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
