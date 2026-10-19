"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildTopologyModel,
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
  const model = buildTopologyModel(devices, [newestScan, oldScan], observed, 1);

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
