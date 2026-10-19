(function (root) {
  "use strict";

  function ipv4ToNumber(value) {
    const parts = String(value || "").split(".");
    if (parts.length !== 4) return null;
    const octets = parts.map(part => {
      if (!/^\d{1,3}$/.test(part)) return -1;
      const number = Number(part);
      return number >= 0 && number <= 255 ? number : -1;
    });
    if (octets.some(part => part < 0)) return null;
    return (((octets[0] * 256 + octets[1]) * 256 + octets[2]) * 256 + octets[3]) >>> 0;
  }

  function isPrivateIPv4(number) {
    if (number === null) return false;
    const first = (number >>> 24) & 255;
    const second = (number >>> 16) & 255;
    return first === 10 ||
      (first === 172 && second >= 16 && second <= 31) ||
      (first === 192 && second === 168);
  }

  function ipv4FromNumber(value) {
    return [
      (value >>> 24) & 255,
      (value >>> 16) & 255,
      (value >>> 8) & 255,
      value & 255
    ].join(".");
  }

  function parsePrivateCidr(value) {
    const parts = String(value || "").trim().split("/");
    if (parts.length !== 2 || !/^\d{1,2}$/.test(parts[1])) return null;
    const address = ipv4ToNumber(parts[0]);
    const prefix = Number(parts[1]);
    if (address === null || prefix < 8 || prefix > 32 || !isPrivateIPv4(address)) return null;

    // Un CIDR solo es privado si el rango completo queda dentro de RFC 1918.
    // La primera IP no basta: 172.16.0.0/11 y 192.168.0.0/15 abarcan redes públicas.
    const first = (address >>> 24) & 255;
    const minimumPrefix = first === 10 ? 8 : first === 172 ? 12 : 16;
    if (prefix < minimumPrefix) return null;

    const mask = (0xffffffff << (32 - prefix)) >>> 0;
    const networkNumber = (address & mask) >>> 0;
    return {
      cidr: ipv4FromNumber(networkNumber) + "/" + prefix,
      prefix: prefix,
      mask: mask,
      networkNumber: networkNumber
    };
  }

  function timestamp(value) {
    if (!value) return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function orderedScans(scans) {
    return (Array.isArray(scans) ? scans.slice() : []).sort((a, b) => {
      const ta = timestamp(a && (a.started_at || a.finished_at));
      const tb = timestamp(b && (b.started_at || b.finished_at));
      if (ta !== null && tb !== null && ta !== tb) return tb - ta;
      return Number(b && b.id || 0) - Number(a && a.id || 0);
    });
  }

  function deviceAddresses(device) {
    const values = Array.isArray(device.addresses) ? device.addresses.slice() : [];
    if (!values.length && device.ip_address) {
      values.push({
        ip_address: device.ip_address,
        last_seen: device.last_seen,
        interface: device.interface,
        source: "inventario principal"
      });
    }
    return values;
  }

  function deviceLabel(device) {
    return String(
      device.display_name || device.observed_ip_address || device.ip_address || device.mac_address || "Dispositivo sin nombre"
    );
  }

  function latestNetworkScan(scans) {
    for (const scan of orderedScans(scans)) {
      const rawNetworks = Array.isArray(scan && scan.discovery && scan.discovery.networks)
        ? scan.discovery.networks : [];
      if (rawNetworks.some(raw => parsePrivateCidr(raw && raw.network))) return scan;
    }
    return null;
  }

  function buildTopologyModelFromApi(payload, allDevices, scans, selectedScanId) {
    const inventory = Array.isArray(allDevices) ? allDevices : [];
    const sortedScans = orderedScans(scans);
    const latestScan = sortedScans[0] || null;
    const selectedScan = payload && payload.scan_id != null
      ? sortedScans.find(scan => String(scan.id) === String(payload.scan_id)) || null
      : null;
    const historicalSelection = Boolean(
      selectedScanId != null &&
      latestNetworkScan(sortedScans) &&
      String(selectedScanId) !== String(latestNetworkScan(sortedScans).id)
    );
    const warnings = Array.isArray(payload && payload.warnings) ? payload.warnings.filter(Boolean) : [];
    const totalDevices = inventory.length;
    const evidenceAvailable = Boolean(payload && payload.evidence_available === true);
    const networkScopeAvailable = Boolean(payload && payload.network_scope_available === true);

    if (!payload || !selectedScan || !evidenceAvailable) {
      return {
        hasNetworkData: false,
        latestScan: latestScan,
        scan: selectedScan,
        networks: [],
        devices: [],
        unlinkedObserved: [],
        notObserved: [],
        stale: Boolean(latestScan),
        historicalSelection: historicalSelection,
        totalDevices: totalDevices,
        observedCount: null,
        scanObservedCount: null,
        networkScopeAvailable: networkScopeAvailable,
        warnings: warnings,
        reason: !selectedScan
          ? "Todavía no hay una lectura de red seleccionada para construir el mapa."
          : !evidenceAvailable
            ? "No se pudo recuperar la evidencia exacta de la lectura seleccionada. " +
              (warnings.join(" ") || "No se dibujan relaciones hasta recuperar sus observaciones.")
            : warnings.join(" ") || "La lectura no tiene datos suficientes para mostrar el grafo."
      };
    }

    const sourceNodes = Array.isArray(payload.nodes) ? payload.nodes : [];
    const sourceEdges = Array.isArray(payload.edges) ? payload.edges : [];
    const sourceDeviceNodes = sourceNodes.filter(node => node && node.kind === "device");
    const nodeById = new Map(sourceNodes.map(node => [String(node.id), node]));
    const sourceNetworks = sourceNodes.filter(node => node && node.kind === "subnet");
    const networks = sourceNetworks.map((node, index) => ({
      id: String(node.id),
      index: index,
      cidr: String(node.label || ""),
      interface: String(node.interface || "interfaz sin identificar"),
      localAddress: String(node.local_address || ""),
      rangeLimited: Boolean(node.range_limited),
      members: []
    }));
    const networkById = new Map(networks.map(network => [network.id, network]));
    const networkByIndex = new Map(networks.map(network => [network.index, network]));
    const relationsByDeviceId = new Map();

    for (const edge of sourceEdges) {
      if (!edge || edge.kind !== "observed-subnet-membership") continue;
      const sourceId = String(edge.source || "");
      const targetId = String(edge.target || "");
      const sourceNode = nodeById.get(sourceId);
      const targetNode = nodeById.get(targetId);
      const deviceNode = sourceNode && sourceNode.kind === "device"
        ? sourceNode
        : targetNode && targetNode.kind === "device" ? targetNode : null;
      const networkNode = sourceNode && sourceNode.kind === "subnet"
        ? sourceNode
        : targetNode && targetNode.kind === "subnet" ? targetNode : null;
      if (!deviceNode || !networkNode || !networkById.has(String(networkNode.id))) continue;

      const rawId = String(deviceNode.device_id || deviceNode.id || "");
      const deviceId = rawId.startsWith("device:") ? rawId.slice(7) : rawId;
      const network = networkById.get(String(networkNode.id));
      const sources = Array.isArray(edge.sources) ? edge.sources.filter(Boolean) : [];
      const times = Array.isArray(edge.observed_at) ? edge.observed_at.filter(Boolean) : [];
      const ipAddress = String(edge.ip_address || edge.label || "");
      if (!ipAddress) continue;

      // Una relación visual por dispositivo y subred. Varias IP del mismo
      // equipo se conservan como evidencia, pero no generan líneas superpuestas.
      const relations = relationsByDeviceId.get(deviceId) || new Map();
      let relation = relations.get(network.index);
      if (!relation) {
        relation = {
          networkIndex: network.index,
          cidr: network.cidr,
          interface: network.interface,
          addresses: [],
          sources: [],
          observedAt: []
        };
        relations.set(network.index, relation);
        relationsByDeviceId.set(deviceId, relations);
      }

      let addressEvidence = relation.addresses.find(item => item.ip_address === ipAddress);
      if (!addressEvidence) {
        addressEvidence = { ip_address: ipAddress, observed_at: [], sources: [] };
        relation.addresses.push(addressEvidence);
      }
      addressEvidence.sources = Array.from(new Set([...addressEvidence.sources, ...sources])).sort();
      addressEvidence.observed_at = Array.from(new Set([...addressEvidence.observed_at, ...times])).sort();
      relation.sources = Array.from(new Set([...relation.sources, ...sources])).sort();
      relation.observedAt = Array.from(new Set([...relation.observedAt, ...times])).sort();
    }

    const inventoryById = new Map(inventory
      .filter(device => device && device.id !== undefined && device.id !== null)
      .map(device => [String(device.id), device]));
    const observedEntries = [];
    const observedInventoryIds = new Set();

    for (const node of sourceDeviceNodes) {
      const rawId = String(node.device_id || node.id || "");
      const deviceId = rawId.startsWith("device:") ? rawId.slice(7) : rawId;
      const original = inventoryById.get(deviceId) || null;
      const device = original ? Object.assign({}, original) : {
        id: deviceId,
        ip_address: "",
        mac_address: node.mac_address || "",
        display_name: "",
        manufacturer: node.manufacturer || "",
        trusted: node.trusted === true,
        addresses: []
      };
      const candidateLabel = String(node.label || "");
      const labelLooksLikeAddress = ipv4ToNumber(candidateLabel) !== null ||
        candidateLabel.includes(":");
      if (!device.display_name && candidateLabel &&
          !labelLooksLikeAddress && !candidateLabel.startsWith("Dispositivo ")) {
        device.display_name = candidateLabel;
      }
      if (!device.mac_address && node.mac_address) device.mac_address = node.mac_address;
      if (!device.manufacturer && node.manufacturer) device.manufacturer = node.manufacturer;
      if (original && typeof original.trusted === "boolean") {
        device.trusted = original.trusted;
      } else if (typeof node.trusted === "boolean") {
        device.trusted = node.trusted;
      }

      const rawObservations = Array.isArray(node.observations) ? node.observations : [];
      let currentAddresses = rawObservations.map(observation => {
        const times = Array.isArray(observation.observed_at) ? observation.observed_at.filter(Boolean) : [];
        const sources = Array.isArray(observation.sources) ? observation.sources.filter(Boolean) : [];
        return {
          ip_address: String(observation.ip_address || ""),
          last_seen: times.length ? times[times.length - 1] : "",
          source: sources[0] || "fuente desconocida"
        };
      }).filter(address => address.ip_address);
      if (!currentAddresses.length) {
        currentAddresses = (Array.isArray(node.ip_addresses) ? node.ip_addresses : [])
          .filter(Boolean)
          .map(ip => ({ ip_address: String(ip), last_seen: "", source: "fuente desconocida" }));
      }
      currentAddresses.sort((left, right) => {
        const a = timestamp(left.last_seen), b = timestamp(right.last_seen);
        if (a !== null && b !== null && a !== b) return b - a;
        return left.ip_address.localeCompare(right.ip_address);
      });
      const firstObservedIp = currentAddresses.length ? currentAddresses[0].ip_address : "";
      device.observed_ip_address = firstObservedIp;
      const relations = Array.from((relationsByDeviceId.get(deviceId) || new Map()).values())
        .map(relation => {
          relation.addresses.sort((left, right) => left.ip_address.localeCompare(right.ip_address));
          const firstAddress = relation.addresses[0] || { ip_address: "", observed_at: [], sources: [] };
          const observedTimes = firstAddress.observed_at || [];
          const sources = firstAddress.sources || [];
          return {
            ...relation,
            address: {
              ip_address: firstAddress.ip_address,
              last_seen: observedTimes.length ? observedTimes[observedTimes.length - 1] : "",
              source: sources[0] || "fuente desconocida"
            },
            source: sources[0] || relation.sources[0] || "fuente desconocida"
          };
        })
        .sort((left, right) => left.networkIndex - right.networkIndex);
      const id = String(device.id);
      observedInventoryIds.add(id);
      observedEntries.push({
        id: id,
        device: device,
        addresses: deviceAddresses(device).concat(currentAddresses),
        currentAddresses: currentAddresses,
        observedInScan: true,
        relations: relations,
        primaryNetworkIndex: relations.length ? relations[0].networkIndex : null
      });
    }

    // Solo se puede evaluar "no visto en esta lectura" cuando se conoce el
    // alcance de la lectura. Si el informe de subredes está ausente o dañado,
    // la ausencia de una observación no permite clasificar el resto del inventario.
    if (networkScopeAvailable) {
      for (const original of inventory) {
        if (!original || original.id === undefined || original.id === null) continue;
        const id = String(original.id);
        if (observedInventoryIds.has(id)) continue;
        // Solo afirmar "no visto" si alguna dirección cae dentro de una
        // subred cuyo descubrimiento no se registró como limitado.
        // Los equipos fuera de ese alcance no pertenecen a esta comparación.
        const inCompleteScope = deviceAddresses(original).some(address => {
          const value = String(address && address.ip_address || "");
          const number = ipv4ToNumber(value);
          if (number === null) return false;
          return networks.some(network => {
            if (network.rangeLimited) return false;
            const subnet = parsePrivateCidr(network.cidr);
            return Boolean(subnet && (((number & subnet.mask) >>> 0) === subnet.networkNumber));
          });
        });
        if (!inCompleteScope) continue;
        observedEntries.push({
          id: id,
          device: original,
          addresses: deviceAddresses(original),
          currentAddresses: [],
          observedInScan: false,
          relations: [],
          primaryNetworkIndex: null
        });
      }
    }

    observedEntries.sort((left, right) =>
      deviceLabel(left.device).localeCompare(deviceLabel(right.device), "es")
    );
    const unlinkedObserved = observedEntries.filter(entry =>
      entry.observedInScan && entry.relations.length === 0
    );
    const notObserved = observedEntries.filter(entry => !entry.observedInScan);
    const linkedDeviceCount = observedEntries.filter(entry =>
      entry.observedInScan && entry.relations.length > 0
    ).length;
    const reportedObservedCount = payload.stats &&
      Number.isFinite(payload.stats.observed_devices) ? payload.stats.observed_devices :
      sourceNodes.filter(node => node.kind === "device").length;

    return {
      hasNetworkData: true,
      latestScan: latestScan,
      scan: selectedScan,
      networks: networks,
      devices: observedEntries,
      unlinkedObserved: unlinkedObserved,
      notObserved: notObserved,
      stale: Boolean(
        latestScan && latestNetworkScan(sortedScans) &&
        String(latestScan.id) !== String(latestNetworkScan(sortedScans).id) &&
        String(selectedScan.id) === String(latestNetworkScan(sortedScans).id)
      ),
      historicalSelection: historicalSelection,
      totalDevices: totalDevices,
      observedCount: linkedDeviceCount,
      scanObservedCount: reportedObservedCount,
      networkScopeAvailable: networkScopeAvailable,
      warnings: warnings,
      reason: networkScopeAvailable ? "" :
        (warnings.join(" ") ||
          (sourceDeviceNodes.length
            ? "La lectura contiene observaciones, pero no se pudo confirmar el alcance de las subredes. Se muestran los equipos observados sin inventar relaciones."
            : "No hay observaciones de dispositivos y tampoco se pudo confirmar el alcance de las subredes. No es posible interpretar ausencias en esta lectura."))
    };
  }

  function searchableText(entry) {
    const device = entry.device || {};
    const values = [
      device.display_name, device.observed_ip_address, device.ip_address, device.mac_address,
      device.manufacturer, device.notes, device.interface
    ];
    for (const address of (entry.addresses || [])) {
      values.push(address.ip_address, address.interface, address.source);
    }
    for (const relation of (entry.relations || [])) {
      values.push(relation.cidr, relation.interface, relation.address && relation.address.ip_address, relation.source);
    }
    return values.filter(Boolean).join(" ").toLocaleLowerCase();
  }

  const POSITION_PREF = "netsentinel-topology-positions-v1";
  let activeGraph = null, activeContainer = null, activeConfig = null, activeModel = null;
  let activeEntriesByGraphId = new Map(), activeNetworkByGraphId = new Map();
  let activeSelectedDeviceId = null, themeObserver = null;

  function graphNodeId(type, value) {
    return type + "-" + String(value == null ? "" : value).replace(/[^a-zA-Z0-9_-]/g, "_");
  }
  function validPosition(value) {
    return Boolean(value && Number.isFinite(Number(value.x)) && Number.isFinite(Number(value.y)) &&
      Math.abs(Number(value.x)) < 1000000 && Math.abs(Number(value.y)) < 1000000);
  }
  function readSavedPositions() {
    try {
      const raw = root.localStorage.getItem(POSITION_PREF);
      const parsed = raw ? JSON.parse(raw) : {};
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
      const result = {};
      Object.entries(parsed).slice(0, 1200).forEach(([id, position]) => {
        if (validPosition(position)) result[id] = { x: Number(position.x), y: Number(position.y) };
      });
      return result;
    } catch (_) { return {}; }
  }
  function saveGraphPositions() {
    if (!activeGraph) return;
    const positions = readSavedPositions();
    activeGraph.nodes().forEach(node => {
      const position = node.position();
      if (validPosition(position)) positions[node.id()] = { x: position.x, y: position.y };
    });
    try {
      root.localStorage.setItem(POSITION_PREF, JSON.stringify(Object.fromEntries(Object.entries(positions).slice(-1200))));
    } catch (_) {}
  }
  function themeValue(name, fallback) {
    try { return root.getComputedStyle(root.document.documentElement).getPropertyValue(name).trim() || fallback; }
    catch (_) { return fallback; }
  }
  function graphStyles() {
    const text = themeValue("--theme-text", "#e7edf7");
    const muted = themeValue("--theme-muted", "#9aabc3");
    const panel = themeValue("--theme-panel", "#121c2d");
    const panelAlt = themeValue("--theme-panel-alt", "#18253a");
    const line = themeValue("--theme-line", "#29374d");
    const accent = themeValue("--theme-accent", "#7dd3fc");
    const good = themeValue("--theme-good-text", "#86efac");
    const warn = themeValue("--theme-warn-text", "#fcd34d");
    return [
      { selector: "node", style: {
        "label":"data(label)", "font-family":"system-ui, -apple-system, sans-serif",
        "font-size":11, "font-weight":600, "color":text, "text-wrap":"wrap", "text-max-width":164,
        "text-valign":"center", "text-halign":"center", "text-outline-width":0,
        "background-color":panel, "border-color":line, "border-width":1.5,
        "width":186, "height":72, "shape":"round-rectangle", "padding":5, "overlay-opacity":0
      }},
      { selector: 'node[type = "network"]', style: {
        "background-color":panelAlt, "border-color":accent, "border-width":2,
        "width":192, "height":78, "font-size":12, "font-weight":750,
        "shape":"round-rectangle", "text-max-width":170
      }},
      { selector: 'node[type = "device"].trusted', style: { "border-color":good, "border-width":2 } },
      { selector: 'node[type = "device"].observed', style: { "border-color":accent, "border-width":2 } },
      { selector: 'node[type = "device"].unlinked', style: {
        "border-color":warn, "border-width":2, "border-style":"dashed"
      }},
      { selector: 'node[type = "device"].not-seen', style: {
        "border-color":muted, "background-color":panelAlt, "border-style":"dashed", "opacity":0.86, "color":muted
      }},
      { selector: "node.is-selected", style: {
        "border-color":accent, "border-width":4, "shadow-blur":16,
        "shadow-color":accent, "shadow-opacity":0.24, "shadow-offset-x":0, "shadow-offset-y":0
      }},
      { selector: "edge", style: {
        "curve-style":"bezier", "line-style":"dotted", "line-color":muted,
        "width":1.6, "opacity":0.72, "target-arrow-shape":"none", "source-arrow-shape":"none", "overlay-opacity":0
      }},
      { selector: "edge.highlighted", style: { "line-color":accent, "width":3, "opacity":1, "line-style":"solid" } },
      { selector: ".is-faded", style: { "opacity":0.14, "events":"no" } }
    ];
  }

  function buildGraphElements(model, options) {
    const config = options || {};
    const query = String(config.search || "").trim().toLocaleLowerCase();
    const filter = String(config.status || "all");
    const positions = config.positions || {};
    const entries = (Array.isArray(model.devices) ? model.devices : []).filter(entry => {
      if (query && !searchableText(entry).includes(query)) return false;
      if (filter === "observed" && !entry.observedInScan) return false;
      if (filter === "not-seen" && entry.observedInScan) return false;
      if (filter === "needs-review" && Boolean(entry.device && entry.device.trusted)) return false;
      return true;
    });
    const visibleNetworkIndexes = new Set();
    entries.forEach(entry => (entry.relations || []).forEach(relation => visibleNetworkIndexes.add(relation.networkIndex)));
    // Con filtros limpios, conservar la subred registrada aunque la lectura no
    // haya observado equipos. El nodo de red es evidencia de alcance, no de presencia.
    if (filter === "all" && !query) {
      (Array.isArray(model.networks) ? model.networks : []).forEach(network => {
        visibleNetworkIndexes.add(network.index);
      });
    }
    const elements = [], networkByGraphId = new Map(), entryByGraphId = new Map(), networkIdByIndex = new Map();

    (Array.isArray(model.networks) ? model.networks : []).forEach(network => {
      if (!visibleNetworkIndexes.has(network.index)) return;
      // La misma subred puede aparecer en interfaces distintas. Usamos la
      // identidad de la API para no colapsar nodos que tienen distinto contexto.
      const id = graphNodeId("network", network.id || (network.cidr + "@" + network.interface));
      const memberCount = entries.filter(entry => (entry.relations || []).some(relation => relation.networkIndex === network.index)).length;
      const data = {
        id, type:"network", cidr:network.cidr, networkIndex:network.index,
        label:network.cidr + "\n" + network.interface + "\n" + memberCount + " dispositivo(s) visto(s)",
        interface:network.interface, localAddress:network.localAddress || "", memberCount, rangeLimited:Boolean(network.rangeLimited)
      };
      const element = { data, classes:"network-node" };
      if (validPosition(positions[id])) element.position = positions[id];
      elements.push(element);
      networkByGraphId.set(id, network);
      networkIdByIndex.set(network.index, id);
    });

    entries.forEach(entry => {
      const device = entry.device || {};
      const id = graphNodeId("device", entry.id);
      const address = (entry.currentAddresses || [])[0] || {};
      const ip = address.ip_address || device.observed_ip_address || device.ip_address || "IP sin identificar";
      const status = entry.relations && entry.relations.length
        ? "Visto en la lectura" : entry.observedInScan ? "Visto · rango sin asociar" : "No visto en la lectura";
      const classes = ["device-node"];
      if (device.trusted) classes.push("trusted");
      if (entry.observedInScan && entry.relations && entry.relations.length) classes.push("observed");
      else if (entry.observedInScan) classes.push("unlinked");
      else classes.push("not-seen");
      const data = {
        id, type:"device", deviceId:String(entry.id),
        label:deviceLabel(device) + "\n" + ip + "\n" + status,
        name:deviceLabel(device), ipAddress:ip, macAddress:device.mac_address || "",
        trusted:Boolean(device.trusted), observed:Boolean(entry.observedInScan), status,
        relationCount:(entry.relations || []).length
      };
      const element = { data, classes:classes.join(" ") };
      if (validPosition(positions[id])) element.position = positions[id];
      elements.push(element);
      entryByGraphId.set(id, entry);
    });

    entries.forEach(entry => (entry.relations || []).forEach(relation => {
      const source = networkIdByIndex.get(relation.networkIndex);
      if (!source) return;
      elements.push({ data:{
        id:graphNodeId("edge", String(entry.id) + "-" + String(relation.networkIndex)),
        source, target:graphNodeId("device", entry.id),
        type:"observed-subnet-membership",
        label:"IP observada dentro del rango de la subred",
        ipAddress:relation.address && relation.address.ip_address || "",
        ipAddresses:(relation.addresses || []).map(item => item.ip_address),
        cidr:relation.cidr, sourceName:(relation.sources || [relation.source]).filter(Boolean).join(", ") || "fuente desconocida"
      }, classes:"membership-edge" });
    }));

    return { elements, entries, entryByGraphId, networkByGraphId, visibleDeviceIds:entries.map(entry=>String(entry.id)) };
  }

  function destroyGraph() {
    if (activeGraph) { try { activeGraph.destroy(); } catch (_) {} }
    activeGraph = null; activeContainer = null;
    activeEntriesByGraphId = new Map(); activeNetworkByGraphId = new Map(); activeSelectedDeviceId = null;
    if (themeObserver) { try { themeObserver.disconnect(); } catch (_) {} themeObserver = null; }
  }
  function formatTimestamp(value) {
    if (!value) return "Sin dato";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }
  function addDetailField(list, label, value) {
    const wrapper = root.document.createElement("div");
    wrapper.className = "topology-detail-field";
    const term = root.document.createElement("dt");
    term.textContent = label;
    const description = root.document.createElement("dd");
    description.textContent = value || "Sin dato";
    wrapper.append(term, description);
    list.appendChild(wrapper);
  }
  function renderSelection(container, entry, model, onOpenHistory) {
    container.replaceChildren();
    if (!entry) {
      const empty = root.document.createElement("p");
      empty.className = "topology-selection-empty";
      empty.textContent = "Elegí un dispositivo para ver sus identificadores, la última observación y la fuente.";
      container.appendChild(empty);
      return;
    }
    const device = entry.device || {};
    const heading = root.document.createElement("div");
    heading.className = "topology-inspector-heading";
    const title = root.document.createElement("h3");
    title.textContent = deviceLabel(device);
    const status = root.document.createElement("span");
    status.className = "topology-status-badge " + (entry.relations.length ? "is-observed" : entry.observedInScan ? "is-unlinked" : "is-not-seen");
    status.textContent = entry.relations.length ? "Visto en la lectura" : entry.observedInScan ? "Visto · rango sin asociar" : "No visto en la lectura";
    heading.append(title, status);
    container.appendChild(heading);

    const currentAddress = (entry.currentAddresses || [])[0] || {};
    const relation = (entry.relations || [])[0] || null;
    const details = root.document.createElement("dl");
    details.className = "topology-detail-grid";
    addDetailField(details, "IP observada", currentAddress.ip_address || device.ip_address || "");
    addDetailField(details, "MAC", device.mac_address || "");
    addDetailField(details, "Fabricante", device.manufacturer || "No identificado");
    addDetailField(details, "Última observación", formatTimestamp(currentAddress.last_seen || device.last_seen));
    addDetailField(details, "Direcciones observadas en esta subred", relation && relation.addresses
      ? relation.addresses.map(item => item.ip_address).join(", ")
      : currentAddress.ip_address || device.ip_address || "");
    addDetailField(details, "Fuente", (relation && relation.sources && relation.sources.join(", ")) ||
      (relation && relation.source) || currentAddress.source || (model.scan && model.scan.source) || "Sin información");
    addDetailField(details, "Confianza", device.trusted ? "Marcado como conocido" : "Pendiente de revisar");
    container.appendChild(details);

    const evidence = root.document.createElement("p");
    evidence.className = "topology-selection-evidence";
    if (relation) {
      const observedIps = relation.addresses
        ? relation.addresses.map(item => item.ip_address).join(", ")
        : relation.address.ip_address;
      const sourceNames = relation.sources && relation.sources.length
        ? relation.sources.join(", ")
        : relation.source;
      evidence.textContent = "La lectura #" + model.scan.id + " registró la(s) IP " + observedIps +
        " dentro del rango " + relation.cidr + " (interfaz " + relation.interface + "; fuente(s) " + sourceNames + "). " +
        "La línea agrupa direcciones observadas dentro de la misma subred; no representa tráfico, una conexión física ni acciones realizadas por el equipo.";
    } else if (entry.observedInScan) {
      evidence.textContent = "El equipo apareció en la lectura #" + model.scan.id +
        ", pero sus direcciones no se pudieron asociar a las subredes registradas. No se crea una relación para completar el dibujo.";
    } else {
      evidence.textContent = "El equipo sigue en el inventario, pero no apareció en la lectura #" + model.scan.id +
        ". Una ausencia en una lectura no demuestra que esté desconectado, apagado ni fuera de la red.";
    }
    container.appendChild(evidence);
    if (typeof onOpenHistory === "function") {
      const action = root.document.createElement("button");
      action.type = "button"; action.className = "quiet tiny topology-history-action";
      action.textContent = "Abrir historial completo";
      action.addEventListener("click", () => onOpenHistory(device));
      container.appendChild(action);
    }
  }
  function renderNetworkSelection(container, network, model) {
    container.replaceChildren();
    const heading = root.document.createElement("div");
    heading.className = "topology-inspector-heading";
    const title = root.document.createElement("h3");
    title.textContent = network.cidr;
    const status = root.document.createElement("span");
    status.className = "topology-status-badge is-observed";
    status.textContent = "Subred observada";
    heading.append(title, status);
    container.appendChild(heading);
    const details = root.document.createElement("dl");
    details.className = "topology-detail-grid";
    addDetailField(details, "Interfaz", network.interface);
    addDetailField(details, "Dirección local", network.localAddress || "");
    addDetailField(details, "Dispositivos asociados en esta vista", String(network.members.length));
    addDetailField(details, "Límite de exploración", network.rangeLimited ? "El descubrimiento se limitó a este rango; las ausencias no son concluyentes" : "No se registró ese límite");
    addDetailField(details, "Lectura utilizada", "#" + model.scan.id + " · " + formatTimestamp(model.scan.finished_at || model.scan.started_at));
    container.appendChild(details);
    const note = root.document.createElement("p");
    note.className = "topology-selection-evidence";
    note.textContent = "La subred agrupa las direcciones observadas en este rango. No confirma qué puerto, punto de acceso o enlace físico usa cada dispositivo.";
    container.appendChild(note);
  }
  function renderAccessibleList(container, entries, selectedId, select) {
    // Actualizar aria-pressed reconstruye los botones. Si la selección vino del
    // teclado, devolver el foco al mismo dispositivo para que Tab no se reinicie.
    const activeElement = root.document && root.document.activeElement;
    const focusedDeviceId = activeElement && container.contains(activeElement) &&
      activeElement.matches && activeElement.matches("button.topology-accessible-node")
      ? activeElement.dataset.deviceId : null;
    container.replaceChildren();
    if (!entries.length) {
      const empty = root.document.createElement("p");
      empty.className = "topology-selection-empty";
      empty.textContent = "No hay dispositivos que coincidan con el filtro.";
      container.appendChild(empty);
      return;
    }
    const list = root.document.createElement("ul");
    list.className = "topology-accessible-list";
    entries.forEach(entry => {
      const item = root.document.createElement("li");
      const button = root.document.createElement("button");
      button.type = "button"; button.className = "quiet tiny topology-accessible-node";
      button.dataset.deviceId = String(entry.id);
      button.setAttribute("aria-pressed", String(String(entry.id) === String(selectedId)));
      const device = entry.device || {};
      const address = (entry.currentAddresses || [])[0];
      const ip = address && address.ip_address || device.ip_address || device.mac_address || "Sin dirección";
      const status = entry.relations.length ? "observado" : entry.observedInScan ? "sin rango asociado" : "no visto en la lectura";
      button.textContent = deviceLabel(device) + " · " + ip + " · " + status;
      button.addEventListener("click", () => select(entry));
      item.appendChild(button); list.appendChild(item);
    });
    container.appendChild(list);

    if (focusedDeviceId !== null) {
      const nextButton = Array.from(container.querySelectorAll("button.topology-accessible-node"))
        .find(button => button.dataset.deviceId === focusedDeviceId);
      if (nextButton) {
        try { nextButton.focus({ preventScroll: true }); }
        catch (_) { nextButton.focus(); }
      }
    }
  }
  function chooseEntry(entry, shouldNotify) {
    if (!activeGraph || !activeConfig || !activeModel) return;
    activeSelectedDeviceId = entry ? String(entry.id) : null;
    activeGraph.elements().removeClass("is-faded is-selected highlighted");
    if (entry) {
      const node = activeGraph.getElementById(graphNodeId("device", entry.id));
      if (node && node.length) {
        node.addClass("is-selected");
        const neighborhood = node.closedNeighborhood();
        activeGraph.elements().not(neighborhood).addClass("is-faded");
        activeGraph.edges().intersection(neighborhood).addClass("highlighted");
      }
    }
    renderSelection(activeConfig.selection, entry, activeModel, activeConfig.onOpenHistory);
    renderAccessibleList(activeConfig.accessible, activeConfig.visibleEntries, activeSelectedDeviceId, next=>chooseEntry(next,true));
    if (shouldNotify !== false && typeof activeConfig.onSelect === "function") activeConfig.onSelect(entry ? entry.device : null);
  }
  function positionForNewNode(element, graphData, index) {
    if (validPosition(element.position)) return element.position;
    const id = element.data && element.data.id;
    const connection = graphData.elements.find(item=>item.data && item.data.source && (item.data.target===id || item.data.source===id));
    if (connection && activeGraph) {
      const otherId = connection.data.source === id ? connection.data.target : connection.data.source;
      const anchor = activeGraph.getElementById(otherId);
      if (anchor && anchor.length) {
        const base = anchor.position();
        const angle = (index * 137.507764 + 31) * Math.PI / 180;
        return { x:base.x + Math.cos(angle)*(125+(index%4)*22), y:base.y + Math.sin(angle)*(125+(index%4)*22) };
      }
    }
    let maxX=0,minX=0,maxY=0,minY=0;
    if (activeGraph && activeGraph.nodes().length) activeGraph.nodes().forEach(node=>{
      const point=node.position(); maxX=Math.max(maxX,point.x); minX=Math.min(minX,point.x); maxY=Math.max(maxY,point.y); minY=Math.min(minY,point.y);
    });
    return { x:(minX+maxX)/2+220, y:(minY+maxY)/2+((index%6)-2.5)*92 };
  }
  function syncGraphElements(graphData) {
    const wanted = new Map(graphData.elements.map(element=>[element.data.id,element]));
    activeGraph.elements().toArray().forEach(element=>{ if(!wanted.has(element.id())) element.remove(); });
    const ordered = graphData.elements.slice().sort((a,b)=>Number(Boolean(a.data&&a.data.source))-Number(Boolean(b.data&&b.data.source)));
    let newIndex = 0;
    ordered.forEach(element=>{
      const existing=activeGraph.getElementById(element.data.id);
      if(existing&&existing.length){
        existing.data(element.data); existing.classes(element.classes||"");
        if(element.position&&validPosition(element.position)) existing.position(element.position);
      } else {
        const next=Object.assign({},element);
        if(!next.data.source&&!validPosition(next.position)) next.position=positionForNewNode(next,graphData,newIndex++);
        activeGraph.add(next);
      }
    });
  }
  function graphLayoutOptions(name, fit) {
    let reduced=false;
    try { reduced=root.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (_) {}
    return { name, fit:Boolean(fit), padding:42, animate:!reduced&&name!=="preset",
      animationDuration:180, randomize:true, nodeRepulsion:6200, idealEdgeLength:145, nodeOverlap:22, componentSpacing:115, gravity:0.22 };
  }
  function updateZoomStatus() {
    const status=root.document.getElementById("topologyZoomStatus");
    if(status) status.textContent=activeGraph?Math.round(activeGraph.zoom()*100)+"%":"—";
  }
  function observeThemeChanges() {
    if(themeObserver||!root.MutationObserver||!root.document||!root.document.documentElement) return;
    themeObserver=new root.MutationObserver(()=>{
      if(activeGraph){ activeGraph.style(graphStyles()); activeGraph.style().update(); }
    });
    themeObserver.observe(root.document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
  }
  function initialiseGraph(config, graphData) {
    const canvas=config.canvas;
    if(!root.cytoscape){
      canvas.textContent="No se pudo cargar el motor local del mapa. Recargá NetSentinel y revisá los recursos instalados.";
      return false;
    }
    const positions=readSavedPositions();
    const nodeElements=graphData.elements.filter(element=>element.data&&!element.data.source);
    const allPositionsSaved=nodeElements.length>0&&nodeElements.every(element=>validPosition(positions[element.data.id]));
    const initialElements=graphData.elements.map(element=>{
      if(!element.data.source&&validPosition(positions[element.data.id])) return Object.assign({},element,{position:positions[element.data.id]});
      return element;
    });
    activeGraph=root.cytoscape({
      container:canvas,elements:initialElements,style:graphStyles(),
      layout:graphLayoutOptions(allPositionsSaved?"preset":"cose",true),
      minZoom:0.25,maxZoom:2.6,wheelSensitivity:0.18,boxSelectionEnabled:false,autograbify:true,autounselectify:true,motionBlur:false
    });
    activeContainer=canvas;
    activeGraph.on("tap","node",event=>{
      const node=event.target;
      if(node.data("type")==="network"){
        activeGraph.elements().removeClass("is-faded is-selected highlighted"); node.addClass("is-selected");
        const network=activeNetworkByGraphId.get(node.id());
        if(network&&activeConfig&&activeConfig.selection) renderNetworkSelection(activeConfig.selection,network,activeModel);
        activeSelectedDeviceId=null;
        if(activeConfig&&typeof activeConfig.onSelect==="function") activeConfig.onSelect(null);
        renderAccessibleList(activeConfig.accessible,activeConfig.visibleEntries,null,next=>chooseEntry(next,true));
        return;
      }
      const entry=activeEntriesByGraphId.get(node.id());
      if(entry) chooseEntry(entry,true);
    });
    activeGraph.on("dragfree","node",saveGraphPositions);
    activeGraph.on("layoutstop",()=>{ saveGraphPositions(); updateZoomStatus(); });
    activeGraph.on("zoom pan",updateZoomStatus);
    activeGraph.ready(()=>{ updateZoomStatus(); saveGraphPositions(); });
    observeThemeChanges();
    return true;
  }
  function renderTopology(options) {
    const config=options||{};
    const canvas=config.canvas, summary=config.summary, selection=config.selection, accessible=config.accessible;
    if(!canvas||!summary||!selection||!accessible) return null;
    activeConfig=config;
    // El navegador solo representa el contrato del servidor. No reconstruye
    // relaciones cuando la API no pudo recuperar una lectura histórica.
    const model = buildTopologyModelFromApi(
      config.topologyGraph,
      config.devices,
      config.scans,
      config.selectedScanId
    );
    const graphData=model.hasNetworkData?buildGraphElements(model,{
      search:config.search,status:config.status,positions:readSavedPositions()
    }):{elements:[],entries:[],entryByGraphId:new Map(),networkByGraphId:new Map(),visibleDeviceIds:[]};
    model.visibleDeviceIds=graphData.visibleDeviceIds;
    if(!model.hasNetworkData){
      summary.textContent=model.reason;
      const empty=root.document.createElement("div"); empty.className="empty topology-empty";
      const strong=root.document.createElement("strong"); strong.textContent="Todavía no hay relaciones de red para mostrar";
      const detail=root.document.createElement("p"); detail.textContent=model.reason; empty.append(strong,detail);
      // Evitamos destruir un renderer que podría tener notificaciones de dibujo pendientes.
      if(activeGraph && activeContainer===canvas){
        activeGraph.stop();
        activeGraph.elements().style("display","none");
        canvas.querySelectorAll(".topology-empty").forEach(node=>node.remove());
        canvas.appendChild(empty);
      } else {
        destroyGraph();
        canvas.replaceChildren(empty);
      }
      renderSelection(selection,null,model,config.onOpenHistory);
      renderAccessibleList(accessible,[],null,()=>{});
      return model;
    }
    const hasVisibleSubnet = graphData.elements.some(element =>
      element.data && element.data.type === "network"
    );
    if(!graphData.entries.length && !hasVisibleSubnet){
      const scopeUnknown = model.networkScopeAvailable === false &&
        !String(config.search || "").trim() &&
        (!config.status || config.status === "all");
      summary.textContent = scopeUnknown
        ? (model.reason || "No se pudo confirmar el alcance de esta lectura.")
        : "No hay dispositivos que coincidan con el filtro actual.";
      const empty=root.document.createElement("div"); empty.className="empty topology-empty";
      const strong=root.document.createElement("strong");
      strong.textContent = scopeUnknown ? "Alcance de red desconocido" : "Sin coincidencias";
      const detail=root.document.createElement("p");
      detail.textContent = scopeUnknown
        ? "No se muestran equipos como ausentes porque el informe de subredes no permite evaluar qué se pudo revisar."
        : "Probá con otro texto o cambiá el filtro de estado.";
      empty.append(strong,detail);
      // Mantener Cytoscape inicializado evita errores al alternar filtros rápidamente en móvil.
      if(activeGraph && activeContainer===canvas){
        activeGraph.stop();
        activeGraph.elements().style("display","none");
        canvas.querySelectorAll(".topology-empty").forEach(node=>node.remove());
        canvas.appendChild(empty);
      } else {
        canvas.replaceChildren(empty);
      }
      renderSelection(selection,null,model,config.onOpenHistory);
      renderAccessibleList(accessible,[],null,()=>{});
      return model;
    }
    if(activeContainer!==canvas||!activeGraph){
      destroyGraph(); canvas.replaceChildren();
      activeEntriesByGraphId=graphData.entryByGraphId; activeNetworkByGraphId=graphData.networkByGraphId; activeModel=model;
      if(!initialiseGraph(config,graphData)){ renderAccessibleList(accessible,graphData.entries,null,()=>{}); return model; }
    } else {
      canvas.querySelectorAll(".topology-empty").forEach(node=>node.remove());
      activeGraph.elements().style("display","element");
      activeEntriesByGraphId=graphData.entryByGraphId; activeNetworkByGraphId=graphData.networkByGraphId; activeModel=model;
      syncGraphElements(graphData); activeGraph.style(graphStyles()); activeGraph.style().update();
    }
    activeConfig=Object.assign({},config,{visibleEntries:graphData.entries});
    const selected=config.selectedId==null?null:graphData.entries.find(entry=>String(entry.id)===String(config.selectedId))||null;
    if(selected){
      activeSelectedDeviceId=String(selected.id);
      activeGraph.elements().removeClass("is-faded is-selected highlighted");
      const selectedNode=activeGraph.getElementById(graphNodeId("device",selected.id));
      if(selectedNode&&selectedNode.length){
        selectedNode.addClass("is-selected");
        const neighborhood=selectedNode.closedNeighborhood();
        activeGraph.elements().not(neighborhood).addClass("is-faded");
        activeGraph.edges().intersection(neighborhood).addClass("highlighted");
      }
      renderSelection(selection,selected,model,config.onOpenHistory);
    } else {
      const hadSelection=activeSelectedDeviceId!==null||config.selectedId!=null;
      activeSelectedDeviceId=null; activeGraph.elements().removeClass("is-faded is-selected highlighted");
      renderSelection(selection,null,model,config.onOpenHistory);
      if(hadSelection&&typeof config.onSelect==="function") config.onSelect(null);
    }
    renderAccessibleList(accessible,graphData.entries,activeSelectedDeviceId,next=>chooseEntry(next,true));
    const observedCount=graphData.entries.filter(entry=>entry.observedInScan).length;
    const trustedCount=graphData.entries.filter(entry=>entry.device&&entry.device.trusted).length;
    const notSeenCount=graphData.entries.filter(entry=>!entry.observedInScan).length;
    const staleMessage=model.stale?" La lectura más reciente no tiene una subred válida; se muestra la lectura #"+model.scan.id+".":"";
    const historicalMessage=model.historicalSelection?" Vista histórica elegida: lectura #"+model.scan.id+".":"";
    const queryMessage=String(config.search||"").trim()?" Filtro de texto: "+graphData.entries.length+" coincidencia(s).":"";
    const statusMessage=config.status&&config.status!=="all"?" Filtro de estado: "+config.status+".":"";
    const subnetSummary = model.networkScopeAvailable === false
      ? "subredes desconocidas"
      : model.networks.length + " subred(es)";
    const scopeMessage = model.networkScopeAvailable === false
      ? " No se pudieron confirmar las subredes de esta lectura; no se inventan relaciones."
      : "";
    const warningList = Array.isArray(model.warnings) ? model.warnings.slice(0, 2) : [];
    const warningMessage = warningList.length
      ? " Avisos: " + warningList.join(" ")
      : "";
    summary.textContent="Lectura #"+model.scan.id+" · "+formatTimestamp(model.scan.finished_at||model.scan.started_at)+
      " · "+subnetSummary+" · "+graphData.entries.length+" dispositivo(s) en esta vista ("+
      observedCount+" observado(s), "+notSeenCount+" no visto(s), "+trustedCount+" marcado(s) conocido(s))."+
      staleMessage+historicalMessage+queryMessage+statusMessage+scopeMessage+warningMessage+
      " Las líneas agrupan IP observadas con rangos de subred; no muestran tráfico ni conexiones físicas.";
    updateZoomStatus();
    return model;
  }
  function fitGraph(){ if(activeGraph&&activeGraph.elements().length) activeGraph.fit(activeGraph.elements(),42); updateZoomStatus(); }
  function zoomGraph(direction){
    if(!activeGraph)return;
    const level=Math.max(0.25,Math.min(2.6,activeGraph.zoom()*(direction>0?1.18:1/1.18)));
    activeGraph.zoom({level,renderedPosition:{x:activeGraph.width()/2,y:activeGraph.height()/2}});
    updateZoomStatus();
  }
  function relayoutGraph(){ if(activeGraph) activeGraph.layout(graphLayoutOptions("cose",true)).run(); }
  function getGraphStats(){
    const visible = collection => collection.filter(node => node.style("display") !== "none").length;
    return {nodeCount:activeGraph?visible(activeGraph.nodes()):0,
      deviceCount:activeGraph?visible(activeGraph.nodes('[type = "device"]')):0,
      edgeCount:activeGraph?visible(activeGraph.edges()):0,
      zoom:activeGraph?activeGraph.zoom():1};
  }
  const api={buildTopologyModelFromApi,buildGraphElements,renderTopology,latestNetworkScan,parsePrivateCidr,
    fit:fitGraph,zoomBy:zoomGraph,relayout:relayoutGraph,getGraphStats};
  if(typeof module!=="undefined"&&module.exports) module.exports=api;
  if(root&&typeof root==="object") root.NetSentinelTopology=api;
})(typeof globalThis!=="undefined"?globalThis:this);
