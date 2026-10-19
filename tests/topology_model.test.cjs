"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildTopologyModel,
  buildTopologyModelFromApi,
  buildGraphElements,
  latestNetworkScan,
  parsePrivateCidr
} = require("../src/netsentinel/static/topology.js");

function scan(id, network) {
  return {
    id,
    started_at: `2026-10-16T10:0${id}:00+00:00`,
    finished_at: `2026-10-16T10:0${id}:30+00:00`,
    source: "automatic-local-network",
    discovery: { networks: network ? [{ network, interface: "en0", local_address: "192.168.1.5" }] : [] }
  };
}

function device(id, ip, overrides = {}) {
  return {
    id,
    ip_address: ip,
    mac_address: "AA:BB:CC:DD:EE:" + String(id).padStart(2, "0"),
    display_name: "",
    manufacturer: "Fabricante de prueba",
    trusted: false,
    addresses: [],
    ...overrides
  };
}

test("solo admite redes privadas IPv4 válidas", () => {
  assert.equal(parsePrivateCidr("192.168.1.0/24").cidr, "192.168.1.0/24");
  assert.equal(parsePrivateCidr("10.0.0.0/8").cidr, "10.0.0.0/8");
  assert.equal(parsePrivateCidr("172.16.0.0/12").cidr, "172.16.0.0/12");
  assert.equal(parsePrivateCidr("8.8.8.0/24"), null);
  assert.equal(parsePrivateCidr("192.0.2.0/24"), null);
  assert.equal(parsePrivateCidr("192.168.1.0/33"), null);
  assert.equal(parsePrivateCidr("192.168.1.0/not-a-prefix"), null);
});

test("construye la relación a partir de observaciones del scan, no de last_seen", () => {
  const oldScan = scan(1, "192.168.1.0/24");
  const newestScan = scan(2, null);
  const observed = [{
    scan_id: 1,
    device_id: 1,
    ip_address: "192.168.1.20",
    observed_at: "2026-10-16T10:01:10+00:00",
    source: "fuente-historica",
    mac_address: device(1).mac_address,
    display_name: "Notebook",
    manufacturer: "Fabricante de prueba",
    trusted: false,
    primary_ip: "192.168.1.20"
  }];
  const devices = [device(1, "192.168.1.20", {
    last_seen: "2026-10-16T10:02:10+00:00",
    addresses: [{
      ip_address: "192.168.1.20",
      last_seen: "2026-10-16T10:02:10+00:00",
      source: "fuente-mas-reciente"
    }]
  })];

  assert.equal(latestNetworkScan([newestScan, oldScan]).id, 1);
  const model = buildTopologyModel(devices, [newestScan, oldScan], observed, 1, 1);

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.scan.id, 1);
  assert.equal(model.stale, true);
  assert.equal(model.observedCount, 1);
  assert.equal(model.devices[0].relations[0].address.source, "fuente-historica");
  assert.equal(model.devices[0].relations[0].address.ip_address, "192.168.1.20");
});

test("rechaza observaciones que no corresponden a la lectura seleccionada", () => {
  const scans = [scan(2, "192.168.1.0/24")];
  const model = buildTopologyModel([device(1, "192.168.1.20")], scans, [], 1);
  assert.equal(model.hasNetworkData, false);
  assert.match(model.reason, /evidencia exacta/i);
});

test("no crea relaciones con direcciones públicas ni inventa una conexión física", () => {
  const scans = [scan(1, "192.168.1.0/24")];
  const devices = [device(1, "8.8.8.8")];
  const observations = [{
    scan_id: 1,
    device_id: 1,
    ip_address: "8.8.8.8",
    observed_at: "2026-10-16T10:01:10+00:00",
    source: "fixture",
    mac_address: devices[0].mac_address
  }];
  const model = buildTopologyModel(devices, scans, observations, 1);

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.observedCount, 0);
  assert.equal(model.devices[0].observedInScan, true);
  assert.equal(model.devices[0].relations.length, 0);
  assert.equal(model.unlinkedObserved.length, 1);
});

test("un activo observado en dos rangos produce dos relaciones, no dos nodos", () => {
  const multiScan = {
    id: 1,
    started_at: "2026-10-16T10:01:00+00:00",
    finished_at: "2026-10-16T10:01:30+00:00",
    source: "automatic-local-network",
    discovery: {
      networks: [
        { network: "192.168.1.0/24", interface: "en0" },
        { network: "10.0.0.0/24", interface: "en1" }
      ]
    }
  };
  const oneDevice = device(5, "192.168.1.20");
  const common = {
    scan_id: 1,
    device_id: 5,
    observed_at: "2026-10-16T10:01:10+00:00",
    source: "fixture",
    mac_address: oneDevice.mac_address
  };
  const model = buildTopologyModel([oneDevice], [multiScan], [
    { ...common, ip_address: "192.168.1.20" },
    { ...common, ip_address: "10.0.0.20" }
  ], 1);

  assert.equal(model.devices.length, 1);
  assert.equal(model.observedCount, 1);
  assert.deepEqual(model.devices[0].relations.map(relation => relation.cidr), [
    "192.168.1.0/24",
    "10.0.0.0/24"
  ]);
});


test("genera nodos y enlaces de subred con significado explícito", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const currentDevice = device(9, "192.168.1.20", { display_name: "Notebook" });
  const observations = [{
    scan_id: 1, device_id: 9, ip_address: "192.168.1.20",
    observed_at: "2026-10-16T10:01:10+00:00", source: "fixture-local",
    mac_address: currentDevice.mac_address, display_name: "Notebook",
    manufacturer: "Fabricante de prueba", trusted: false, primary_ip: "192.168.1.20"
  }];
  const model = buildTopologyModel([currentDevice], [currentScan], observations, 1);
  const graph = buildGraphElements(model, { search: "", status: "all", positions: {} });
  const networkNode = graph.elements.find(item => item.data.type === "network");
  const deviceNode = graph.elements.find(item => item.data.type === "device");
  const edge = graph.elements.find(item => item.data.source);
  assert.ok(networkNode);
  assert.ok(deviceNode);
  assert.ok(edge);
  assert.match(networkNode.data.label, /192\.168\.1\.0\/24/);
  assert.match(deviceNode.data.label, /192\.168\.1\.20/);
  assert.equal(edge.data.type, "observed-subnet-membership");
  assert.deepEqual(graph.visibleDeviceIds, ["9"]);
});

test("el filtro del grafo diferencia equipos vistos de los no vistos", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const currentDevice = device(1, "192.168.1.20");
  const oldDevice = device(2, "192.168.1.30", { last_seen: "2026-10-15T10:00:00+00:00" });
  const observations = [{
    scan_id: 1, device_id: 1, ip_address: "192.168.1.20",
    observed_at: "2026-10-16T10:01:10+00:00", source: "fixture",
    mac_address: currentDevice.mac_address, primary_ip: "192.168.1.20"
  }];
  const model = buildTopologyModel([currentDevice, oldDevice], [currentScan], observations, 1);
  const observed = buildGraphElements(model, { status: "observed" });
  const notSeen = buildGraphElements(model, { status: "not-seen" });
  assert.deepEqual(observed.visibleDeviceIds, ["1"]);
  assert.deepEqual(notSeen.visibleDeviceIds, ["2"]);
  assert.equal(notSeen.elements.filter(item => item.data.type === "device").length, 1);
  assert.equal(notSeen.elements.some(item => item.data.source), false);
});


test("permite reconstruir una captura histórica elegida explícitamente", () => {
  const olderScan = scan(1, "192.168.1.0/24");
  const newestScan = scan(2, "192.168.1.0/24");
  const currentDevice = device(3, "192.168.1.21");
  const observations = [{
    scan_id: 1,
    device_id: 3,
    ip_address: "192.168.1.20",
    observed_at: "2026-10-16T10:01:10+00:00",
    source: "fixture-anterior",
    mac_address: currentDevice.mac_address
  }];
  const model = buildTopologyModel(
    [currentDevice],
    [newestScan, olderScan],
    observations,
    1,
    1
  );

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.scan.id, 1);
  assert.equal(model.historicalSelection, true);
  assert.equal(model.stale, false);
  assert.equal(model.devices[0].observedInScan, true);
  assert.equal(model.devices[0].currentAddresses[0].ip_address, "192.168.1.20");
  assert.equal(model.devices[0].relations[0].address.source, "fixture-anterior");
});


test("the explorer adapts the server graph without rebuilding network relations", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const currentDevice = device(9, "192.168.1.99", { display_name: "Notebook" });
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: true,
    nodes: [
      {
        id: "subnet:192.168.1.0%2F24%40en0",
        kind: "subnet",
        label: "192.168.1.0/24",
        network_id: "subnet:192.168.1.0%2F24%40en0",
        interface: "en0",
        detail: "Interfaz en0"
      },
      {
        id: "device:9",
        kind: "device",
        label: "Notebook",
        device_id: "device:9",
        ip_addresses: ["192.168.1.20"],
        observations: [{
          ip_address: "192.168.1.20",
          sources: ["fixture-history"],
          observed_at: ["2026-10-16T10:01:10+00:00"]
        }],
        mac_address: currentDevice.mac_address,
        manufacturer: "Fabricante de prueba",
        trusted: false
      }
    ],
    edges: [{
      id: "membership:device%3A9:subnet:192.168.1.0%2F24%40en0:192.168.1.20",
      source: "device:9",
      target: "subnet:192.168.1.0%2F24%40en0",
      kind: "observed-subnet-membership",
      label: "192.168.1.20",
      ip_address: "192.168.1.20",
      sources: ["fixture-history"],
      observed_at: ["2026-10-16T10:01:10+00:00"]
    }],
    stats: {
      observed_devices: 1,
      known_subnets: 1,
      observed_memberships: 1,
      unlinked_devices: 0
    },
    warnings: []
  };

  const model = buildTopologyModelFromApi(
    payload,
    [currentDevice, device(10, "192.168.1.30")],
    [currentScan],
    "1"
  );
  const notebook = model.devices.find(entry => entry.id === "9");
  const graph = buildGraphElements(model, { status: "all" });

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.networkScopeAvailable, true);
  assert.equal(model.scanObservedCount, 1);
  assert.equal(model.observedCount, 1);
  assert.equal(notebook.observedInScan, true);
  assert.equal(notebook.currentAddresses[0].ip_address, "192.168.1.20");
  assert.equal(notebook.currentAddresses[0].source, "fixture-history");
  assert.equal(notebook.relations[0].cidr, "192.168.1.0/24");
  assert.equal(notebook.relations[0].address.ip_address, "192.168.1.20");
  assert.equal(model.devices.find(entry => entry.id === "10").observedInScan, false);
  assert.equal(graph.elements.filter(item => item.data.type === "network").length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "observed-subnet-membership").length, 1);
});


test("the explorer keeps observations visible but does not invent links when network scope is unknown", () => {
  const currentScan = scan(1, null);
  const currentDevice = device(11, "192.168.1.20");
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: false,
    nodes: [{
      id: "device:11",
      kind: "device",
      label: "AA:BB:CC:DD:EE:11",
      device_id: "device:11",
      ip_addresses: ["192.168.1.20"],
      observations: [{
        ip_address: "192.168.1.20",
        sources: ["fixture-neighbor"],
        observed_at: ["2026-10-16T10:01:10+00:00"]
      }],
      mac_address: currentDevice.mac_address,
      manufacturer: null,
      trusted: false
    }],
    edges: [],
    stats: {
      observed_devices: 1,
      known_subnets: null,
      observed_memberships: null,
      unlinked_devices: null
    },
    warnings: ["No se pudo interpretar el informe de descubrimiento guardado."]
  };

  const model = buildTopologyModelFromApi(payload, [currentDevice], [currentScan], "1");
  const entry = model.devices[0];

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.networkScopeAvailable, false);
  assert.equal(model.scanObservedCount, 1);
  assert.equal(model.observedCount, 0);
  assert.equal(entry.observedInScan, true);
  assert.equal(entry.relations.length, 0);
  assert.equal(entry.currentAddresses[0].ip_address, "192.168.1.20");
  assert.equal(entry.currentAddresses[0].source, "fixture-neighbor");
  assert.match(model.reason, /no se pudo interpretar/i);
  assert.equal(buildGraphElements(model, { status: "all" }).elements.some(item => item.data.source), false);
});


test("the visual adapter keeps equal CIDRs distinct when they belong to different interfaces", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const currentDevice = device(12, "192.168.1.20");
  const subnetEn0 = "subnet:192.168.1.0/24@en0";
  const subnetEn1 = "subnet:192.168.1.0/24@en1";
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: true,
    nodes: [
      { id: subnetEn0, kind: "subnet", label: "192.168.1.0/24", network_id: subnetEn0, interface: "en0", local_address: "192.168.1.10" },
      { id: subnetEn1, kind: "subnet", label: "192.168.1.0/24", network_id: subnetEn1, interface: "en1", local_address: "192.168.1.11" },
      {
        id: "device:12", kind: "device", label: currentDevice.mac_address, device_id: "device:12",
        ip_addresses: ["192.168.1.20"],
        observations: [{ ip_address: "192.168.1.20", sources: ["fixture"], observed_at: ["2026-10-16T10:01:10+00:00"] }],
        mac_address: currentDevice.mac_address, manufacturer: null, trusted: false
      }
    ],
    edges: [
      { id: "e0", source: "device:12", target: subnetEn0, kind: "observed-subnet-membership", label: "192.168.1.20", ip_address: "192.168.1.20", sources: ["fixture"], observed_at: ["2026-10-16T10:01:10+00:00"] },
      { id: "e1", source: "device:12", target: subnetEn1, kind: "observed-subnet-membership", label: "192.168.1.20", ip_address: "192.168.1.20", sources: ["fixture"], observed_at: ["2026-10-16T10:01:10+00:00"] }
    ],
    stats: { observed_devices: 1, known_subnets: 2, observed_memberships: 2, unlinked_devices: 0 },
    warnings: []
  };
  const model = buildTopologyModelFromApi(payload, [currentDevice], [currentScan], "1");
  const graph = buildGraphElements(model, { status: "all" });
  const subnetNodes = graph.elements.filter(item => item.data.type === "network");

  assert.equal(subnetNodes.length, 2);
  assert.equal(new Set(subnetNodes.map(item => item.data.id)).size, 2);
  assert.deepEqual(new Set(subnetNodes.map(item => item.data.interface)), new Set(["en0", "en1"]));
  assert.equal(subnetNodes.find(item => item.data.interface === "en0").data.cidr, "192.168.1.0/24");
  assert.equal(graph.elements.filter(item => item.data.type === "observed-subnet-membership").length, 2);
});


test("the explorer retains registered subnet nodes when a valid reading has no devices", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const subnetId = "subnet:192.168.1.0/24@en0";
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: true,
    nodes: [{
      id: subnetId,
      kind: "subnet",
      label: "192.168.1.0/24",
      network_id: subnetId,
      interface: "en0",
      local_address: "192.168.1.10"
    }],
    edges: [],
    stats: {
      observed_devices: 0,
      known_subnets: 1,
      observed_memberships: 0,
      unlinked_devices: 0
    },
    warnings: []
  };
  const model = buildTopologyModelFromApi(payload, [], [currentScan], "1");
  const graph = buildGraphElements(model, { status: "all" });

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.scanObservedCount, 0);
  assert.equal(model.networks.length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "network").length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "device").length, 0);
  assert.equal(graph.elements.some(item => item.data.source), false);
});
