(function (root) {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const MAX_VISIBLE_DEVICES = 72;
  const MAX_OBSERVED_DEVICES = 60;
  const DEVICE_COLUMNS = 3;
  const CANVAS_WIDTH = 930;
  const DEVICE_WIDTH = 185;
  const DEVICE_HEIGHT = 54;
  const DEVICE_X = [300, 510, 720];
  const ROW_GAP = 78;

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

  function parsePrivateCidr(value) {
    const parts = String(value || "").trim().split("/");
    if (parts.length !== 2 || !/^\d{1,2}$/.test(parts[1])) return null;
    const address = ipv4ToNumber(parts[0]);
    const prefix = Number(parts[1]);
    if (address === null || prefix < 8 || prefix > 32 || !isPrivateIPv4(address)) return null;
    const mask = (0xffffffff << (32 - prefix)) >>> 0;
    return {
      cidr: parts[0] + "/" + prefix,
      prefix: prefix,
      mask: mask,
      networkNumber: (address & mask) >>> 0
    };
  }

  function isAddressInNetwork(address, network) {
    const parsed = ipv4ToNumber(address);
    return parsed !== null && ((parsed & network.mask) >>> 0) === network.networkNumber;
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

  function wasSeenDuringScan(address, scan) {
    const seenAt = timestamp(address && address.last_seen);
    const startedAt = timestamp(scan && scan.started_at);
    const finishedAt = timestamp(scan && scan.finished_at);
    if (seenAt === null || startedAt === null || finishedAt === null) return false;
    return seenAt >= startedAt - 1000 && seenAt <= finishedAt + 1000;
  }

  function deviceLabel(device) {
    return String(
      device.display_name || device.observed_ip_address || device.ip_address || device.mac_address || "Dispositivo sin nombre"
    );
  }

  function compareNewestFirst(left, right) {
    const leftAt = timestamp(left.device.last_seen);
    const rightAt = timestamp(right.device.last_seen);
    if (leftAt !== null && rightAt !== null && leftAt !== rightAt) return rightAt - leftAt;
    return deviceLabel(left.device).localeCompare(deviceLabel(right.device), "es");
  }

  function latestNetworkScan(scans) {
    for (const scan of orderedScans(scans)) {
      const rawNetworks = Array.isArray(scan && scan.discovery && scan.discovery.networks)
        ? scan.discovery.networks : [];
      if (rawNetworks.some(raw => parsePrivateCidr(raw && raw.network))) return scan;
    }
    return null;
  }

  function buildTopologyModel(devices, scans, observations, observationsScanId) {
    const allDevices = Array.isArray(devices) ? devices : [];
    const sortedScans = orderedScans(scans);
    const latestScan = sortedScans[0] || null;
    const selectedScan = latestNetworkScan(sortedScans);
    let selectedNetworks = [];

    if (selectedScan) {
      const rawNetworks = Array.isArray(selectedScan.discovery && selectedScan.discovery.networks)
        ? selectedScan.discovery.networks : [];
      const seenCidrs = new Set();
      for (const raw of rawNetworks) {
        const parsed = parsePrivateCidr(raw && raw.network);
        if (!parsed || seenCidrs.has(parsed.cidr)) continue;
        seenCidrs.add(parsed.cidr);
        selectedNetworks.push({
          index: selectedNetworks.length,
          cidr: parsed.cidr,
          parsed: parsed,
          interface: String(raw.interface || "interfaz sin identificar"),
          localAddress: String(raw.local_address || ""),
          rangeLimited: Boolean(raw.range_limited),
          members: []
        });
      }
    }

    if (!selectedScan || !selectedNetworks.length) {
      return {
        hasNetworkData: false,
        latestScan: latestScan,
        scan: null,
        networks: [],
        devices: [],
        unlinkedObserved: [],
        notObserved: [],
        stale: Boolean(latestScan),
        totalDevices: allDevices.length,
        observedCount: 0,
        reason: latestScan
          ? "Las lecturas disponibles no contienen una subred IPv4 privada válida. Ejecutá un nuevo descubrimiento local para construir el mapa."
          : "Todavía no hay lecturas de red. Ejecutá un descubrimiento local para construir la primera vista."
      };
    }

    const requestedScanId = observationsScanId == null
      ? (Array.isArray(observations) && observations.length ? observations[0].scan_id : null)
      : observationsScanId;
    if (requestedScanId == null || String(requestedScanId) !== String(selectedScan.id) || !Array.isArray(observations)) {
      return {
        hasNetworkData: false,
        latestScan: latestScan,
        scan: selectedScan,
        networks: selectedNetworks,
        devices: [],
        unlinkedObserved: [],
        notObserved: [],
        stale: Boolean(latestScan && String(latestScan.id) !== String(selectedScan.id)),
        totalDevices: allDevices.length,
        observedCount: 0,
        reason: "No se pudo recuperar la evidencia exacta de la lectura seleccionada. No se dibujan relaciones hasta disponer de sus observaciones históricas."
      };
    }

    const deviceById = new Map();
    for (const device of allDevices) {
      if (!device || device.id === undefined || device.id === null) continue;
      deviceById.set(String(device.id), device);
    }

    // Las observaciones están vinculadas por scan_id. No se infiere presencia
    // usando last_seen, porque ese valor puede haber cambiado en lecturas posteriores.
    const observationsByDevice = new Map();
    for (const row of observations) {
      if (!row || String(row.scan_id) !== String(selectedScan.id) ||
          row.device_id === undefined || row.device_id === null || !row.ip_address) continue;
      const id = String(row.device_id);
      const address = {
        ip_address: String(row.ip_address),
        last_seen: row.observed_at || "",
        source: String(row.source || selectedScan.source || "fuente desconocida")
      };
      const list = observationsByDevice.get(id) || [];
      list.push(address);
      observationsByDevice.set(id, list);

      if (!deviceById.has(id)) {
        deviceById.set(id, {
          id: row.device_id,
          ip_address: row.primary_ip || row.ip_address,
          mac_address: row.mac_address || "",
          display_name: row.display_name || "",
          manufacturer: row.manufacturer || "",
          trusted: Boolean(row.trusted),
          last_seen: row.observed_at || ""
        });
      }
    }

    const modeledDevices = [];
    for (const [id, device] of deviceById) {
      const addresses = deviceAddresses(device);
      const currentAddresses = observationsByDevice.get(id) || [];
      const relationsByNetwork = new Map();

      for (const address of currentAddresses) {
        for (const network of selectedNetworks) {
          if (!isAddressInNetwork(address.ip_address, network.parsed)) continue;
          const existing = relationsByNetwork.get(network.index);
          const nextSeen = timestamp(address.last_seen) || 0;
          const oldSeen = existing ? (timestamp(existing.address.last_seen) || 0) : -1;
          if (!existing || nextSeen >= oldSeen) {
            relationsByNetwork.set(network.index, {
              networkIndex: network.index,
              cidr: network.cidr,
              interface: network.interface,
              address: address,
              source: String(address.source || selectedScan.source || "fuente desconocida")
            });
          }
        }
      }

      const relations = Array.from(relationsByNetwork.values())
        .sort((a, b) => a.networkIndex - b.networkIndex);
      const graphDevice = {
        ...device,
        // Preferimos una dirección que pertenezca a esta lectura, sin alterar el inventario actual.
        observed_ip_address: currentAddresses.length ? currentAddresses[0].ip_address : ""
      };
      const entry = {
        id: id,
        device: graphDevice,
        addresses: addresses.concat(currentAddresses),
        currentAddresses: currentAddresses,
        observedInScan: observationsByDevice.has(id),
        relations: relations,
        primaryNetworkIndex: relations.length ? relations[0].networkIndex : null
      };
      modeledDevices.push(entry);
    }

    for (const network of selectedNetworks) {
      network.members = modeledDevices.filter(device =>
        device.relations.some(relation => relation.networkIndex === network.index)
      );
    }

    const observedCount = modeledDevices.filter(device => device.relations.length > 0).length;
    const unlinkedObserved = modeledDevices
      .filter(device => device.observedInScan && device.relations.length === 0)
      .sort(compareNewestFirst);
    const notObserved = modeledDevices
      .filter(device => !device.observedInScan)
      .sort(compareNewestFirst);

    return {
      hasNetworkData: true,
      latestScan: latestScan,
      scan: selectedScan,
      networks: selectedNetworks,
      devices: modeledDevices,
      unlinkedObserved: unlinkedObserved,
      notObserved: notObserved,
      stale: Boolean(latestScan && String(latestScan.id) !== String(selectedScan.id)),
      totalDevices: allDevices.length,
      observedCount: observedCount,
      scanObservedCount: modeledDevices.filter(device => device.observedInScan).length,
      reason: ""
    };
  }

  function searchableText(entry) {
    const device = entry.device;
    const values = [
      device.display_name, device.observed_ip_address, device.ip_address, device.mac_address,
      device.manufacturer, device.notes, device.interface
    ];
    for (const address of entry.addresses) values.push(address.ip_address, address.interface, address.source);
    for (const relation of entry.relations) {
      values.push(relation.cidr, relation.interface, relation.address.ip_address, relation.source);
    }
    return values.filter(Boolean).join(" ").toLocaleLowerCase();
  }

  function makeSvgElement(name, className, attributes) {
    const element = document.createElementNS(SVG_NS, name);
    if (className) element.setAttribute("class", className);
    Object.entries(attributes || {}).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
  }

  function svgText(parent, x, y, value, className) {
    const element = makeSvgElement("text", className, { x: x, y: y });
    element.textContent = String(value == null ? "" : value);
    parent.appendChild(element);
    return element;
  }

  function truncate(value, maxLength) {
    const text = String(value == null ? "" : value);
    return text.length <= maxLength ? text : text.slice(0, maxLength - 1) + "…";
  }

  function createDeviceNode(entry, x, y, selectedId, select) {
    const device = entry.device;
    const group = makeSvgElement("g", "topology-device-node", {
      transform: "translate(" + x + " " + y + ")",
      tabindex: "0",
      role: "button",
      "aria-pressed": entry.id === selectedId ? "true" : "false",
      "aria-label": "Seleccionar " + deviceLabel(device) + ", " +
        (entry.currentAddresses[0]?.ip_address || device.ip_address || device.mac_address || "dirección desconocida")
    });
    group.dataset.deviceId = entry.id;
    if (entry.id === selectedId) group.classList.add("is-selected");
    if (device.trusted) group.classList.add("is-trusted");

    const rect = makeSvgElement("rect", "topology-device-card", {
      width: DEVICE_WIDTH, height: DEVICE_HEIGHT, rx: 9, ry: 9
    });
    group.appendChild(rect);
    svgText(group, 11, 21, truncate(deviceLabel(device), 25), "topology-node-label");
    const subtitle = entry.currentAddresses.length
      ? entry.currentAddresses.map(address => address.ip_address).join(", ")
      : (device.ip_address || device.mac_address || "Dirección sin identificar");
    svgText(group, 11, 41, truncate(subtitle, 29), "topology-node-subtitle");

    const title = makeSvgElement("title", "", {});
    title.textContent = deviceLabel(device) + " · " + subtitle +
      (device.trusted ? " · marcado de confianza" : " · pendiente de revisar");
    group.appendChild(title);

    const activate = function (event) {
      if (event && event.type === "keydown" && event.key !== "Enter" && event.key !== " ") return;
      if (event && event.type === "keydown") event.preventDefault();
      select(entry);
    };
    group.addEventListener("click", activate);
    group.addEventListener("keydown", activate);
    return group;
  }

  function renderSelection(container, entry, model) {
    container.replaceChildren();
    if (!entry) {
      const text = document.createElement("p");
      text.className = "topology-selection-empty";
      text.textContent = "Seleccioná un dispositivo del mapa para consultar la evidencia y su procedencia.";
      container.appendChild(text);
      return;
    }

    const device = entry.device;
    const heading = document.createElement("strong");
    heading.textContent = deviceLabel(device);
    container.appendChild(heading);

    const meta = document.createElement("p");
    meta.className = "topology-selection-meta";
    meta.textContent = "IP principal: " + (device.ip_address || "—") +
      " · IP de la lectura: " + (entry.currentAddresses.map(address => address.ip_address).join(", ") || "sin observación") +
      " · MAC: " + (device.mac_address || "—") +
      " · Fabricante: " + (device.manufacturer || "sin identificar") +
      " · Confianza: " + (device.trusted ? "marcado como de confianza" : "pendiente de revisar");
    container.appendChild(meta);

    const evidence = document.createElement("p");
    evidence.className = "topology-selection-evidence";
    if (entry.relations.length) {
      evidence.textContent = "Evidencia de la lectura #" + model.scan.id + ": " +
        entry.relations.map(relation =>
          relation.address.ip_address + " pertenece al rango " + relation.cidr +
          " (interfaz " + relation.interface + "; fuente " + relation.source + ")"
        ).join("; ") +
        ". Esto no demuestra un enlace físico directo ni que el dispositivo responda a otros protocolos.";
    } else if (entry.observedInScan) {
      evidence.textContent = "El equipo apareció en la lectura #" + model.scan.id +
        ", pero sus direcciones observadas (" +
        entry.currentAddresses.map(address => address.ip_address + " · fuente " + address.source).join(", ") +
        ") no se pudieron asociar a las subredes registradas. No se dibuja una relación inferida.";
    } else {
      evidence.textContent = "El equipo permanece en el inventario, pero no apareció en la lectura #" +
        model.scan.id + ". La ausencia en una lectura no demuestra que esté desconectado.";
    }
    container.appendChild(evidence);
  }

  function renderAccessibleList(container, entries, selectedId, select) {
    container.replaceChildren();
    if (!entries.length) {
      const empty = document.createElement("p");
      empty.className = "topology-selection-empty";
      empty.textContent = "No hay dispositivos que coincidan con el filtro.";
      container.appendChild(empty);
      return;
    }
    const list = document.createElement("ul");
    list.className = "topology-accessible-list";
    for (const entry of entries) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quiet tiny";
      button.dataset.deviceId = entry.id;
      button.setAttribute("aria-pressed", entry.id === selectedId ? "true" : "false");
      button.textContent = deviceLabel(entry.device) + " · " +
        (entry.currentAddresses[0]?.ip_address || entry.device.ip_address || entry.device.mac_address || "sin dirección") +
        (entry.relations.length ? " · relación observada" : entry.observedInScan ? " · sin subred asociable" : " · no observado en la lectura");
      button.addEventListener("click", () => select(entry));
      item.appendChild(button);
      list.appendChild(item);
    }
    container.appendChild(list);
  }

  function renderTopology(options) {
    const config = options || {};
    const canvas = config.canvas;
    const summary = config.summary;
    const selection = config.selection;
    const accessible = config.accessible;
    if (!canvas || !summary || !selection || !accessible) return null;

    const model = buildTopologyModel(config.devices, config.scans, config.observations, config.observationsScanId);
    const query = String(config.search || "").trim().toLocaleLowerCase();
    const matching = model.devices.filter(entry => !query || searchableText(entry).includes(query));

    canvas.replaceChildren();
    accessible.replaceChildren();

    if (!model.hasNetworkData) {
      summary.textContent = model.reason;
      const empty = document.createElement("div");
      empty.className = "empty topology-empty";
      const strong = document.createElement("strong");
      strong.textContent = "Todavía no hay relaciones de red para mostrar";
      const detail = document.createElement("p");
      detail.textContent = model.reason;
      empty.append(strong, detail);
      canvas.appendChild(empty);
      renderSelection(selection, null, model);
      renderAccessibleList(accessible, [], null, () => {});
      return model;
    }

    const observed = matching.filter(entry => entry.relations.length > 0).sort(compareNewestFirst);
    const otherObserved = matching.filter(entry => entry.observedInScan && entry.relations.length === 0).sort(compareNewestFirst);
    const oldInventory = matching.filter(entry => !entry.observedInScan).sort(compareNewestFirst);
    const chosen = observed.slice(0, MAX_OBSERVED_DEVICES);
    const selectedIds = new Set(chosen.map(entry => entry.id));
    for (const entry of otherObserved.concat(oldInventory)) {
      if (selectedIds.size >= MAX_VISIBLE_DEVICES || selectedIds.has(entry.id)) continue;
      if (selectedIds.size < MAX_OBSERVED_DEVICES && entry.relations.length) continue;
      selectedIds.add(entry.id);
      chosen.push(entry);
    }

    const visibleById = new Map(chosen.map(entry => [entry.id, entry]));
    const networks = model.networks.map(network => ({
      type: "network",
      network: network,
      devices: chosen.filter(entry => entry.primaryNetworkIndex === network.index)
    }));
    const noRelationVisible = chosen.filter(entry => entry.observedInScan && entry.relations.length === 0);
    const notSeenVisible = chosen.filter(entry => !entry.observedInScan);
    if (noRelationVisible.length) {
      networks.push({ type: "unlinked-observed", title: "Observado sin subred asociable", description: "Sin línea inferida", devices: noRelationVisible });
    }
    if (notSeenVisible.length) {
      networks.push({ type: "not-observed", title: "Inventario no observado en la lectura", description: "No equivale a estar desconectado", devices: notSeenVisible });
    }

    const groups = [];
    let top = 18;
    for (const group of networks) {
      const rows = Math.max(1, Math.ceil(group.devices.length / DEVICE_COLUMNS));
      const height = group.devices.length ? 136 + (rows - 1) * ROW_GAP : 118;
      const layout = { group: group, top: top, height: height, nodePositions: [] };
      group.devices.forEach((entry, index) => {
        const column = index % DEVICE_COLUMNS;
        const row = Math.floor(index / DEVICE_COLUMNS);
        layout.nodePositions.push({
          entry: entry,
          x: DEVICE_X[column],
          y: top + 42 + row * ROW_GAP
        });
      });
      groups.push(layout);
      top += height + 18;
    }

    const svgHeight = Math.max(160, top + 8);
    const svg = makeSvgElement("svg", "topology-svg", {
      viewBox: "0 0 " + CANVAS_WIDTH + " " + svgHeight,
      role: "group",
      "aria-label": "Mapa de relaciones de inventario. Las líneas conectan direcciones observadas con el rango de una subred registrada; no indican enlaces físicos."
    });
    const positionsById = new Map();
    for (const layout of groups) {
      for (const position of layout.nodePositions) {
        positionsById.set(position.entry.id, position);
      }
    }

    const networkLayouts = new Map(
      groups
        .filter(layout => layout.group.type === "network")
        .map(layout => [layout.group.network.index, layout])
    );
    // Un dispositivo puede tener direcciones observadas en más de una subred.
    // Dibujamos todas las relaciones con una sola tarjeta por dispositivo.
    for (const entry of chosen) {
      const position = positionsById.get(entry.id);
      if (!position) continue;
      for (const relation of entry.relations) {
        const layout = networkLayouts.get(relation.networkIndex);
        if (!layout) continue;
        const networkY = layout.top + (layout.height - 62) / 2;
        const path = makeSvgElement("path", "topology-edge", {
          d: "M 240 " + (networkY + 31) +
            " C 265 " + (networkY + 31) + ", 270 " + (position.y + 27) +
            ", " + position.x + " " + (position.y + 27),
          fill: "none"
        });
        const title = makeSvgElement("title", "", {});
        title.textContent = "Dirección " + relation.address.ip_address +
          " observada dentro de " + relation.cidr + " en la lectura #" + model.scan.id +
          " (fuente: " + relation.source + "). No demuestra conexión física directa.";
        path.appendChild(title);
        svg.appendChild(path);
      }
    }

    const entryById = new Map(model.devices.map(entry => [entry.id, entry]));
    let selectedEntry = entryById.get(String(config.selectedId)) || null;
    if (selectedEntry && !visibleById.has(selectedEntry.id)) selectedEntry = null;

    function choose(entry) {
      selectedEntry = entry;
      svg.querySelectorAll(".topology-device-node").forEach(node => {
        const isSelected = node.dataset.deviceId === entry.id;
        node.classList.toggle("is-selected", isSelected);
        node.setAttribute("aria-pressed", isSelected ? "true" : "false");
      });
      accessible.querySelectorAll("button").forEach(button => {
        const isSelected = button.dataset.deviceId === entry.id;
        button.setAttribute("aria-pressed", isSelected ? "true" : "false");
      });
      renderSelection(selection, entry, model);
      if (typeof config.onSelect === "function") config.onSelect(entry.device);
    }

    for (const layout of groups) {
      const group = layout.group;
      const leftX = 25;
      const leftW = 215;
      const centerY = layout.top + (layout.height - 62) / 2;
      const card = makeSvgElement("g", group.type === "network" ? "topology-network-node" : "topology-unlinked-node", {});
      card.appendChild(makeSvgElement("rect", "", {
        x: leftX, y: centerY, width: leftW, height: 62, rx: 9, ry: 9
      }));
      if (group.type === "network") {
        svgText(card, leftX + 12, centerY + 22, truncate(group.network.cidr, 26), "topology-network-label");
        svgText(card, leftX + 12, centerY + 42,
          truncate(group.network.interface + " · " + group.network.members.length + " relación(es)", 28),
          "topology-node-subtitle");
        const title = makeSvgElement("title", "", {});
        title.textContent = "Rango de red detectado: " + group.network.cidr +
          ". Interfaz: " + group.network.interface +
          (group.network.rangeLimited ? ". El rango de exploración se limitó a /24." : "");
        card.appendChild(title);
      } else {
        svgText(card, leftX + 12, centerY + 22, truncate(group.title, 25), "topology-network-label");
        svgText(card, leftX + 12, centerY + 42, truncate(group.description, 28), "topology-node-subtitle");
      }
      svg.appendChild(card);

      for (const position of layout.nodePositions) {
        const entry = position.entry;
        const groupNode = createDeviceNode(entry, position.x, position.y, selectedEntry ? selectedEntry.id : null, choose);
        svg.appendChild(groupNode);
      }
    }

    canvas.appendChild(svg);
    const omitted = Math.max(0, matching.length - chosen.length);
    const staleMessage = model.stale
      ? " La lectura más reciente no tiene una subred válida; se usa la lectura #" + model.scan.id + "."
      : "";
    const filterMessage = query ? " Filtro aplicado: " + matching.length + " coincidencia(s)." : "";
    const capMessage = omitted ? " Se muestran " + chosen.length + " de " + matching.length + " activos coincidentes para conservar la legibilidad." : "";
    summary.textContent = "Lectura #" + model.scan.id + " · " + (model.scan.finished_at || model.scan.started_at || "fecha desconocida") +
      " · " + model.observedCount + " activo(s) con relación basada en dirección observada · " +
      model.networks.length + " subred(es) · " + model.totalDevices + " activo(s) en inventario." +
      staleMessage + filterMessage + capMessage +
      " Las líneas indican pertenencia de una IP al rango registrado; no prueban enlaces físicos.";

    renderAccessibleList(accessible, chosen, selectedEntry ? selectedEntry.id : null, choose);
    renderSelection(selection, selectedEntry, model);
    return model;
  }

  const api = {
    buildTopologyModel: buildTopologyModel,
    renderTopology: renderTopology,
    latestNetworkScan: latestNetworkScan,
    parsePrivateCidr: parsePrivateCidr
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root && typeof root === "object") root.NetSentinelTopology = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
