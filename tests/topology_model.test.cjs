"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
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

test("rejects CIDR ranges that extend beyond private IPv4 space and normalizes valid ranges", () => {
  assert.equal(parsePrivateCidr("172.16.0.0/11"), null);
  assert.equal(parsePrivateCidr("172.31.255.255/11"), null);
  assert.equal(parsePrivateCidr("192.168.0.0/15"), null);
  assert.equal(parsePrivateCidr("192.168.1.1/15"), null);
  assert.equal(parsePrivateCidr("172.31.255.255/12").cidr, "172.16.0.0/12");
  assert.equal(parsePrivateCidr("192.168.1.42/24").cidr, "192.168.1.0/24");
});

test("el selector inicial elige la lectura más reciente con una subred válida", () => {
  const newestWithoutNetwork = scan(3, null);
  const olderWithNetwork = scan(2, "192.168.1.0/24");
  const oldestWithNetwork = scan(1, "10.0.0.0/24");

  assert.equal(
    latestNetworkScan([newestWithoutNetwork, oldestWithNetwork, olderWithNetwork]).id,
    2
  );
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
        observations: [
          {
            ip_address: "192.168.1.20",
            sources: ["fixture-history"],
            observed_at: ["2026-10-16T10:01:10+00:00"]
          },
          {
            ip_address: "192.168.1.21",
            sources: ["fixture-second-address"],
            observed_at: ["2026-10-16T10:01:11+00:00"]
          }
        ],
        mac_address: currentDevice.mac_address,
        manufacturer: "Fabricante de prueba",
        trusted: false
      }
    ],
    edges: [
      {
        id: "membership:device%3A9:subnet:192.168.1.0%2F24%40en0:192.168.1.20",
        source: "device:9",
        target: "subnet:192.168.1.0%2F24%40en0",
        kind: "observed-subnet-membership",
        label: "192.168.1.20",
        ip_address: "192.168.1.20",
        sources: ["fixture-history"],
        observed_at: ["2026-10-16T10:01:10+00:00"]
      },
      {
        id: "membership:device%3A9:subnet:192.168.1.0%2F24%40en0:192.168.1.21",
        source: "device:9",
        target: "subnet:192.168.1.0%2F24%40en0",
        kind: "observed-subnet-membership",
        label: "192.168.1.21",
        ip_address: "192.168.1.21",
        sources: ["fixture-second-address"],
        observed_at: ["2026-10-16T10:01:11+00:00"]
      }
    ],
    stats: {
      observed_devices: 1,
      known_subnets: 1,
      observed_memberships: 2,
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
  assert.deepEqual(
    notebook.currentAddresses.map(item => [item.ip_address, item.source]),
    [
      ["192.168.1.21", "fixture-second-address"],
      ["192.168.1.20", "fixture-history"]
    ]
  );
  assert.equal(notebook.relations[0].cidr, "192.168.1.0/24");
  assert.deepEqual(notebook.relations[0].addresses.map(item => item.ip_address), ["192.168.1.20", "192.168.1.21"]);
  assert.deepEqual(notebook.relations[0].sources, ["fixture-history", "fixture-second-address"]);
  assert.equal(model.devices.find(entry => entry.id === "10").observedInScan, false);
  assert.equal(graph.elements.filter(item => item.data.type === "network").length, 1);
  const visualEdges = graph.elements.filter(item => item.data.type === "observed-subnet-membership");
  assert.equal(visualEdges.length, 1);
  assert.deepEqual(visualEdges[0].data.ipAddresses, ["192.168.1.20", "192.168.1.21"]);
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
      { id: subnetEn0, kind: "subnet", label: "192.168.1.0/24", network_id: subnetEn0, interface: "en0", local_address: "192.168.1.10", range_limited: true },
      { id: subnetEn1, kind: "subnet", label: "192.168.1.0/24", network_id: subnetEn1, interface: "en1", local_address: "192.168.1.11", range_limited: false },
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
  assert.equal(subnetNodes.find(item => item.data.interface === "en0").data.rangeLimited, true);
  assert.equal(subnetNodes.find(item => item.data.interface === "en1").data.rangeLimited, false);
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


test("unknown network scope never classifies inventory devices as absent when no observations exist", () => {
  const currentScan = scan(1, null);
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: false,
    nodes: [],
    edges: [],
    stats: {
      observed_devices: 0,
      known_subnets: null,
      observed_memberships: null,
      unlinked_devices: null
    },
    warnings: ["No se pudo interpretar el informe de descubrimiento guardado."]
  };
  const inventory = [device(13, "192.168.1.30"), device(14, "192.168.1.31")];
  const model = buildTopologyModelFromApi(payload, inventory, [currentScan], "1");
  const graph = buildGraphElements(model, { status: "all" });

  assert.equal(model.hasNetworkData, true);
  assert.equal(model.networkScopeAvailable, false);
  assert.equal(model.scanObservedCount, 0);
  assert.equal(model.devices.length, 0);
  assert.equal(graph.elements.length, 0);
  assert.match(model.reason, /no se pudo interpretar/i);
});


test("inventory devices outside the selected scan's subnet scope are not classified as absent", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: true,
    nodes: [{
      id: "subnet:192.168.1.0%2F24%40en0",
      kind: "subnet",
      label: "192.168.1.0/24",
      network_id: "subnet:192.168.1.0%2F24%40en0",
      interface: "en0",
      local_address: "192.168.1.5",
      range_limited: false
    }],
    edges: [],
    stats: { observed_devices: 0, known_subnets: 1, observed_memberships: 0, unlinked_devices: 0 },
    warnings: []
  };
  const inventory = [
    device(21, "192.168.1.21"),
    device(22, "10.12.0.22")
  ];
  const model = buildTopologyModelFromApi(payload, inventory, [currentScan], "1");
  const graph = buildGraphElements(model, { status: "all" });

  assert.deepEqual(model.devices.map(entry => entry.id), ["21"]);
  assert.equal(model.devices[0].observedInScan, false);
  assert.equal(graph.entries.length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "network").length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "observed-subnet-membership").length, 0);
});


test("inventory devices within a limited range are not marked absent", () => {
  const currentScan = scan(1, "192.168.1.0/24");
  const payload = {
    scan_id: "1",
    captured_at: currentScan.finished_at,
    evidence_available: true,
    network_scope_available: true,
    nodes: [{
      id: "subnet:192.168.1.0%2F24%40en0",
      kind: "subnet",
      label: "192.168.1.0/24",
      network_id: "subnet:192.168.1.0%2F24%40en0",
      interface: "en0",
      local_address: "192.168.1.5",
      range_limited: true
    }],
    edges: [],
    stats: { observed_devices: 0, known_subnets: 1, observed_memberships: 0, unlinked_devices: 0 },
    warnings: ["El alcance de descubrimiento estuvo limitado."]
  };
  const inventory = [device(23, "192.168.1.23")];
  const model = buildTopologyModelFromApi(payload, inventory, [currentScan], "1");
  const graph = buildGraphElements(model, { status: "all" });

  assert.deepEqual(model.devices, []);
  assert.equal(model.networkScopeAvailable, true);
  assert.equal(graph.elements.filter(item => item.data.type === "network").length, 1);
  assert.equal(graph.elements.filter(item => item.data.type === "device").length, 0);
  assert.equal(graph.elements.filter(item => item.data.type === "observed-subnet-membership").length, 0);
});
