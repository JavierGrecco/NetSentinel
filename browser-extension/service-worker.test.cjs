const test = require("node:test");
const assert = require("node:assert/strict");

function listenerSlot() {
  return { addListener() {} };
}

// The service worker uses only listener registration at module load. These minimal
// mocks let the real sanitizer functions run under Node without a browser profile.
global.chrome = {
  storage: { local: { async get() { return {}; }, async set() {} } },
  webNavigation: { onCompleted: listenerSlot(), onHistoryStateUpdated: listenerSlot() },
  runtime: { onStartup: listenerSlot(), onInstalled: listenerSlot() },
  extension: { inIncognitoContext: false }
};

const {
  cleanUrl,
  isExcluded,
  privateOrLocalHost,
  searchInfo
} = require("./service-worker.js");

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
