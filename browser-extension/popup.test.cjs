const test = require("node:test");
const assert = require("node:assert/strict");
const manifest = require("./manifest.json");
const { DEFAULTS, normalizeRetentionDays, escapeCsv, buildCsv, getState, render, saveSettings } = require("./popup.js");

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


test("popup retention normalization handles invalid persisted values", () => {
  assert.equal(normalizeRetentionDays(1), 1);
  assert.equal(normalizeRetentionDays("7"), 7);
  assert.equal(normalizeRetentionDays(90), 90);
  assert.equal(normalizeRetentionDays(0), 1);
  assert.equal(normalizeRetentionDays(120), 90);
  assert.equal(normalizeRetentionDays("not-a-number"), 7);
  assert.equal(normalizeRetentionDays({}), 7);
  assert.equal(normalizeRetentionDays(true), 7);
  assert.equal(normalizeRetentionDays(1.5), 7);
});

test("popup preserves still-retained events when stored retention setting is malformed", async () => {
  const previousChrome = global.chrome;
  const settingsKey = "netsentinelSettings";
  const eventsKey = "netsentinelEvents";
  const retained = {
    observed_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    event_type: "page_visit",
    page_url: "https://example.com/retained"
  };
  global.chrome = {
    storage: {
      local: {
        async get() {
          return {
            [settingsKey]: { enabled: true, retentionDays: "invalid" },
            [eventsKey]: [retained]
          };
        },
        async set() { throw new Error("getState must stay read-only"); }
      }
    }
  };
  try {
    const state = await getState();
    assert.equal(state.settings.retentionDays, 7);
    assert.equal(state.events.length, 1);
    assert.equal(state.events[0].page_url, "https://example.com/retained");
  } finally {
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});


test("popup ignores malformed stored event records and preserves valid retained events", async () => {
  const previousChrome = global.chrome;
  const settingsKey = "netsentinelSettings";
  const eventsKey = "netsentinelEvents";
  const retained = {
    observed_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    event_type: "page_visit",
    page_url: "https://example.com/retained"
  };
  let writes = 0;
  global.chrome = {
    storage: {
      local: {
        async get() {
          return {
            [settingsKey]: { enabled: true, retentionDays: 7 },
            [eventsKey]: [
              null,
              undefined,
              "not-an-event",
              [],
              { observed_at: "not-a-date", event_type: "page_visit" },
              retained
            ]
          };
        },
        async set() { writes += 1; }
      }
    }
  };
  try {
    const state = await getState();
    assert.deepEqual(state.events, [retained]);
    assert.equal(writes, 0, "cleaning the in-memory view must not cause a stale storage write");
  } finally {
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});


function makeElement() {
  const classes = new Set();
  const attrs = {};
  return {
    checked: false, value: "", textContent: "", disabled: false, className: "",
    children: [], listeners: {},
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); }
    },
    attributes: attrs,
    setAttribute(name, value) { attrs[name] = value; },
    addEventListener(name, callback) { this.listeners[name] = callback; },
    replaceChildren(...children) { this.children = [...children]; },
    append(...children) { this.children.push(...children); },
    click() { if (this.listeners.click) return this.listeners.click(); }
  };
}

function installPopupDom() {
  const ids = [
    "enabled", "capturePages", "captureSearches", "retention", "excludeDomains",
    "count", "statusText", "recent", "export", "saveSettings", "clear"
  ];
  const elements = Object.fromEntries(ids.map(id => [id, makeElement()]));
  const previousDocument = global.document;
  global.document = {
    getElementById(id) { return elements[id] || null; },
    createElement() { return makeElement(); }
  };
  return {
    elements,
    restore() {
      if (previousDocument === undefined) delete global.document;
      else global.document = previousDocument;
    }
  };
}

test("popup load failure gives an actionable message and logs no raw storage error", async () => {
  const previousChrome = global.chrome;
  const dom = installPopupDom();
  const previousConsoleError = console.error;
  const logged = [];
  console.error = (...args) => logged.push(args.join(" "));
  global.chrome = {
    storage: { local: { async get() { throw new Error("sensitive stored URL must not be logged"); } } }
  };
  try {
    const rendered = await render();
    assert.equal(rendered, false);
    assert.match(dom.elements.statusText.textContent, /No se pudieron cargar/);
    assert.equal(dom.elements.statusText.classList.contains("error"), true);
    assert.equal(dom.elements.statusText.attributes.role, "alert");
    assert.equal(dom.elements.export.disabled, true);
    assert.equal(logged.length, 1);
    assert.match(logged[0], /cargar el estado local \(Error\)/);
    assert.doesNotMatch(logged[0], /sensitive stored URL/);
  } finally {
    console.error = previousConsoleError;
    dom.restore();
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});

test("saving an invalid retention control value uses the validated default", async () => {
  const previousChrome = global.chrome;
  const dom = installPopupDom();
  const settingsKey = "netsentinelSettings";
  const eventsKey = "netsentinelEvents";
  const store = {
    [settingsKey]: { enabled: false, capturePages: true, captureSearches: true, retentionDays: 7, excludeDomains: [] },
    [eventsKey]: []
  };
  let writes = 0;
  global.chrome = {
    storage: {
      local: {
        async get() { return { [settingsKey]: store[settingsKey], [eventsKey]: store[eventsKey] }; },
        async set(values) { writes += 1; Object.assign(store, values); }
      }
    }
  };
  dom.elements.retention.value = "NaN";
  dom.elements.excludeDomains.value = "";
  try {
    const saved = await saveSettings();
    assert.equal(saved, true);
    assert.equal(writes, 1);
    assert.equal(store[settingsKey].retentionDays, DEFAULTS.retentionDays);
    assert.equal(Number.isNaN(store[settingsKey].retentionDays), false);
    assert.equal(dom.elements.statusText.classList.contains("error"), false);
  } finally {
    dom.restore();
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});

test("popup reports settings-write failures without leaking exception details", async () => {
  const previousChrome = global.chrome;
  const dom = installPopupDom();
  const previousConsoleError = console.error;
  const logged = [];
  console.error = (...args) => logged.push(args.join(" "));
  global.chrome = {
    storage: {
      local: {
        async get() { return { netsentinelSettings: {}, netsentinelEvents: [] }; },
        async set() { throw new Error("private browsing URL in backend exception"); }
      }
    }
  };
  dom.elements.retention.value = "7";
  dom.elements.excludeDomains.value = "";
  try {
    const saved = await saveSettings();
    assert.equal(saved, false);
    assert.match(dom.elements.statusText.textContent, /No se pudo guardar la configuración/);
    assert.equal(dom.elements.statusText.classList.contains("error"), true);
    assert.match(logged[0], /guardar la configuración \(Error\)/);
    assert.doesNotMatch(logged[0], /private browsing URL/);
  } finally {
    console.error = previousConsoleError;
    dom.restore();
    if (previousChrome === undefined) delete global.chrome;
    else global.chrome = previousChrome;
  }
});
