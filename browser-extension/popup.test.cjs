const test = require("node:test");
const assert = require("node:assert/strict");
const manifest = require("./manifest.json");
const { DEFAULTS, escapeCsv, buildCsv } = require("./popup.js");

test("popup remains opt-in and manifest uses the narrow MV3 permission set", () => {
  assert.equal(manifest.manifest_version, 3);
  assert.equal(DEFAULTS.enabled, false);
  assert.equal(manifest.background.service_worker, "service-worker.js");
  assert.deepEqual([...manifest.permissions].sort(), ["storage", "webNavigation"].sort());
  assert.equal(Object.hasOwn(manifest, "host_permissions"), false);
  assert.equal(Object.hasOwn(manifest, "optional_host_permissions"), false);
  assert.equal(Object.hasOwn(manifest, "incognito"), false);
  assert.ok(!manifest.permissions.includes("cookies"));
  assert.ok(!manifest.permissions.includes("history"));
});

test("CSV fields are always quoted and embedded quotes are doubled", () => {
  assert.equal(escapeCsv("simple"), '"simple"');
  assert.equal(escapeCsv("with,comma"), '"with,comma"');
  assert.equal(escapeCsv('say "hello"'), '"say ""hello"""');
  assert.equal(escapeCsv("first\r\nsecond"), '"first\r\nsecond"');
  assert.equal(escapeCsv(null), '""');
});

test("CSV neutralizes formula-like content after whitespace/control prefixes", () => {
  for (const value of ["=1+1", "+SUM(1,1)", "-1+1", "@cmd", " \t=1+1"]) {
    assert.equal(escapeCsv(value), '"' + "'" + value + '"');
  }
});

test("CSV builder returns UTF-8 BOM, CRLF rows and only approved browser metadata columns", () => {
  const csv = buildCsv([{
    observed_at: "2026-10-12T00:00:00+00:00",
    event_type: "search_query",
    domain: "www.google.com",
    page_url: "https://www.google.com/search",
    search_engine: "Google",
    search_terms: "=1+1",
    app_name: 'browser, "extension"\r\nnext',
    email_subject: "should not be exported"
  }]);

  assert.ok(csv.startsWith("\ufeff"));
  assert.ok(csv.endsWith("\r\n"));
  assert.ok(csv.includes('"\'=1+1"'));
  assert.ok(csv.includes('"browser, ""extension""\r\nnext"'));
  assert.ok(csv.includes('"search_terms"'));
  assert.ok(!csv.includes("email_subject"));
  assert.ok(!csv.includes("should not be exported"));
  // Quoted fields may contain CRLF; count rows using a record without embedded newlines.
  const simpleCsv = buildCsv([{ observed_at: "2026-10-12T00:00:00+00:00", event_type: "page_visit" }]);
  const lines = simpleCsv.slice(1).split("\r\n").filter(Boolean);
  assert.equal(lines.length, 2, "the export contains one header and one record");
});

test("CSV builder emits only the header for an empty event list", () => {
  const csv = buildCsv([]);
  assert.ok(csv.startsWith("\ufeff"));
  assert.ok(csv.endsWith("\r\n"));
  assert.equal(csv.slice(1).split("\r\n").filter(Boolean).length, 1);
});


test("popup state reads do not write an old events snapshot back to storage", async () => {
  const previousChrome = global.chrome;
  let writes = 0;
  const settingsKey = "netsentinelSettings";
  const eventsKey = "netsentinelEvents";
  const events = [{
    observed_at: new Date().toISOString(),
    event_type: "page_visit",
    page_url: "https://example.com/"
  }];
  global.chrome = {
    storage: {
      local: {
        async get() {
          return { [settingsKey]: { enabled: true, retentionDays: 7 }, [eventsKey]: events };
        },
        async set() { writes += 1; }
      }
    }
  };
  try {
    const state = await getState();
    assert.equal(state.events.length, 1);
    assert.equal(writes, 0, "reading popup state must not overwrite events concurrently captured by the service worker");
  } finally {
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});
