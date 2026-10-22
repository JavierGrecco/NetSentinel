/* Mapa mundial local: no consulta servicios externos ni infiere IP a partir del dominio. */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const svgNS = "http://www.w3.org/2000/svg";
  const state = { payload: null, worldReady: false, destinations: [], filtered: [], selectedIp: "" };
  const mapWidth = 1000;
  const mapHeight = 500;

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function svgElement(tag, attributes) {
    const node = document.createElementNS(svgNS, tag);
    Object.entries(attributes || {}).forEach(([key, value]) => node.setAttribute(key, String(value)));
    return node;
  }

  async function readJson(url) {
    const response = await fetch(url, { cache: "no-store", credentials: "same-origin" });
    if (!response.ok) throw new Error("La consulta local no terminó correctamente (" + response.status + ").");
    return response.json();
  }

  function project(longitude, latitude) {
    return {
      x: ((longitude + 180) / 360) * mapWidth,
      y: ((90 - latitude) / 180) * mapHeight
    };
  }

  function ringPath(ring) {
    let path = "";
    let previousLongitude = null;
    ring.forEach((pair, index) => {
      if (!Array.isArray(pair) || pair.length < 2) return;
      const longitude = Number(pair[0]);
      const latitude = Number(pair[1]);
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return;
      const point = project(longitude, latitude);
      const command = index === 0 || (
        previousLongitude !== null && Math.abs(longitude - previousLongitude) > 180
      ) ? "M" : "L";
      path += command + point.x.toFixed(2) + "," + point.y.toFixed(2) + " ";
      previousLongitude = longitude;
    });
    return path.trim();
  }

  function drawWorld(geojson) {
    const root = $("worldMap");
    root.replaceChildren();
    root.append(svgElement("title", {}));
    root.firstElementChild.textContent = "Mapa mundial interactivo con ubicaciones aproximadas de IP públicas observadas";
    const land = svgElement("g", { "aria-hidden": "true" });
    const features = Array.isArray(geojson && geojson.features) ? geojson.features : [];
    features.forEach((feature) => {
      const geometry = feature && feature.geometry;
      if (!geometry) return;
      let polygons = [];
      if (geometry.type === "Polygon" && Array.isArray(geometry.coordinates)) {
        polygons = [geometry.coordinates];
      } else if (geometry.type === "MultiPolygon" && Array.isArray(geometry.coordinates)) {
        polygons = geometry.coordinates;
      }
      const paths = [];
      polygons.forEach((polygon) => {
        if (!Array.isArray(polygon)) return;
        polygon.forEach((ring) => {
          if (Array.isArray(ring) && ring.length > 1) {
            const part = ringPath(ring);
            if (part) paths.push(part);
          }
        });
      });
      if (paths.length) land.append(svgElement("path", { d: paths.join(" "), class: "geo-country" }));
    });
    root.append(land);
    state.worldReady = true;
    drawMarkers();
  }

  function latestFirst(left, right) {
    return String(right.last_seen || "").localeCompare(String(left.last_seen || ""));
  }

  function locationLabel(item) {
    if (item.location_status === "located") return [item.city, item.country].filter(Boolean).join(", ") || item.country_iso || "Coordenadas disponibles";
    if (item.location_status === "no_coordinates") return "Sin coordenadas en la base";
    if (item.location_status === "not_found") return "IP no incluida en la base";
    return "Base GeoIP no disponible";
  }

  function when(value) {
    if (!value) return "No informado";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(date);
  }

  function updateSelected(item, context) {
    if (!item) {
      state.selectedIp = "";
      $("geoSelectedTitle").textContent = "Elegí un punto o una IP";
      $("geoDetailsEmpty").hidden = false;
      $("geoSelectedDetails").hidden = true;
      $("geoSelectedDetails").replaceChildren();
      return;
    }

    state.selectedIp = item.ip;
    $("geoSelectedTitle").textContent = item.ip;
    $("geoDetailsEmpty").hidden = true;
    const list = $("geoSelectedDetails");
    list.replaceChildren();
    list.hidden = false;

    const currentDns = context && context.kind === "current_dns";
    const values = currentDns ? [
      ["Origen del dato", "Resolución DNS actual; no es un evento histórico"],
      ["Dominio consultado", context.hostname],
      ["Hora de la consulta", when(context.queried_at)],
      ["Direcciones devueltas por DNS", Number(context.resolved_count || 0).toLocaleString("es-AR")],
      ["Estado GeoIP", locationLabel(item)],
      ["País", item.country || item.country_iso || "Sin dato"],
      ["Ciudad", item.city || "Sin dato"],
      ["ASN", item.asn ? "AS" + item.asn : "Sin dato"],
      ["Organización ASN", item.asn_organization || "Sin dato"]
    ] : [
      ["Origen del dato", "Evento guardado localmente"],
      ["Ubicación aproximada", locationLabel(item)],
      ["País", item.country || item.country_iso || "Sin dato"],
      ["Ciudad", item.city || "Sin dato"],
      ["ASN", item.asn ? "AS" + item.asn : "Sin dato"],
      ["Organización ASN", item.asn_organization || "Sin dato"],
      ["Eventos guardados", Number(item.event_count || 0).toLocaleString("es-AR")],
      ["Último evento", when(item.last_seen)],
      ["Dominio asociado", item.sample_domain || "No registrado en el evento"]
    ];

    values.forEach(([label, value]) => {
      list.append(element("dt", label));
      list.append(element("dd", value));
    });
  }

  function drawMarkers() {
    const root = $("worldMap");
    root.querySelectorAll(".geo-marker-layer").forEach((layer) => layer.remove());
    if (!state.worldReady) return;

    // Primero: IP sacadas de eventos guardados.
    const located = state.destinations.filter((item) =>
      item.location_status === "located" &&
      Number.isFinite(Number(item.latitude)) &&
      Number.isFinite(Number(item.longitude))
    );
    const groups = new Map();

    located.forEach((item) => {
      const key = Number(item.latitude).toFixed(1) + ":" +
        Number(item.longitude).toFixed(1) + ":" + (item.country_iso || "");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });

    const observedLayer = svgElement("g", { class: "geo-marker-layer geo-observed-marker-layer" });
    groups.forEach((items) => {
      const longitude = items.reduce((sum, item) => sum + Number(item.longitude), 0) / items.length;
      const latitude = items.reduce((sum, item) => sum + Number(item.latitude), 0) / items.length;
      const point = project(longitude, latitude);
      const radius = Math.min(12, 5 + Math.sqrt(items.length));
      const marker = svgElement("circle", {
        cx: point.x, cy: point.y, r: radius, class: "geo-marker",
        tabindex: 0, role: "button",
        "aria-label": items.length === 1
          ? "Seleccionar IP observada " + items[0].ip + ", " + locationLabel(items[0])
          : "Seleccionar grupo de " + items.length + " IP observadas, " +
            (items[0].country || "ubicación aproximada")
      });
      const title = svgElement("title", {});
      title.textContent = items.length + " IP observada(s) · " +
        (items[0].country || "País sin dato") + " · " +
        items.reduce((sum, item) => sum + Number(item.event_count || 0), 0) +
        " evento(s) guardado(s)";
      marker.append(title);

      const select = () => updateSelected(items[0], null);
      marker.addEventListener("click", select);
      marker.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
      observedLayer.append(marker);
    });
    root.append(observedLayer);

    // Segundo: IP de una resolución DNS manual actual, con estilo distinto.
    const lookup = state.currentDnsLookup;
    if (!lookup) return;
    const lookupLayer = svgElement("g", { class: "geo-marker-layer geo-current-dns-marker-layer" });
    const currentContext = {
      kind: "current_dns",
      hostname: lookup.hostname,
      queried_at: lookup.queried_at,
      resolved_count: lookup.dns_addresses.length
    };

    lookup.destinations
      .filter((item) => item.location_status === "located" &&
        Number.isFinite(Number(item.latitude)) &&
        Number.isFinite(Number(item.longitude)))
      .forEach((item) => {
        const point = project(Number(item.longitude), Number(item.latitude));
        const marker = svgElement("circle", {
          cx: point.x, cy: point.y, r: 6,
          class: "geo-marker geo-marker-current",
          tabindex: 0, role: "button",
          "aria-label": "IP " + item.ip + " de la resolución DNS actual de " +
            lookup.hostname + ", " + locationLabel(item)
        });
        const title = svgElement("title", {});
        title.textContent = item.ip + " · DNS actual de " + lookup.hostname +
          " · " + locationLabel(item);
        marker.append(title);

        const select = () => updateSelected(item, currentContext);
        marker.addEventListener("click", select);
        marker.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            select();
          }
        });
        lookupLayer.append(marker);
      });
    root.append(lookupLayer);
  }

  function renderTable() {
    const body = $("geoDestinationsBody");
    body.replaceChildren();
    const filter = $("geoDestinationFilter").value.trim().toLowerCase();
    state.filtered = state.destinations.filter((item) => [
      item.ip, item.country, item.country_iso, item.city, item.asn,
      item.asn_organization, item.sample_domain, locationLabel(item)
    ].some((value) => String(value || "").toLowerCase().includes(filter)));
    state.filtered.sort(latestFirst);

    if (!state.filtered.length) {
      const row = document.createElement("tr");
      const cell = element("td", filter ? "No hay destinos que coincidan con el filtro." : "Todavía no hay IP públicas registradas como destino en los eventos guardados.");
      cell.colSpan = 8;
      cell.className = "empty";
      row.append(cell);
      body.append(row);
      $("geoTableStatus").textContent = "";
      return;
    }
    state.filtered.forEach((item) => {
      const row = document.createElement("tr");
      const cells = [
        item.ip,
        locationLabel(item),
        item.asn ? "AS" + item.asn + (item.asn_organization ? " · " + item.asn_organization : "") : "Sin dato ASN",
        Number(item.event_count || 0).toLocaleString("es-AR"),
        when(item.last_seen),
        item.sample_domain || "—"
      ];
      cells.forEach((value, index) => {
        const cell = element("td");
        cell.textContent = value;
        if (index === 0) {
          const code = element("code", item.ip);
          cell.replaceChildren(code);
        }
        row.append(cell);
      });
      const stateCell = element("td");
      stateCell.append(element("span", item.location_status === "located" ? "Ubicada" : item.location_status === "no_coordinates" ? "Sin coordenadas" : item.location_status === "not_found" ? "Sin coincidencia" : "GeoIP no disponible",
        "geo-state-tag" + (item.location_status === "located" ? " is-located" : "")));
      row.append(stateCell);
      const actionCell = document.createElement("td");
      const button = element("button", "Ver detalle", "quiet tiny geo-select-ip");
      button.type = "button";
      button.addEventListener("click", () => {
        updateSelected(item);
        $("geoSelectedTitle").scrollIntoView({ block: "nearest", behavior: "auto" });
      });
      actionCell.append(button);
      row.append(actionCell);
      body.append(row);
    });
    $("geoTableStatus").textContent = state.filtered.length.toLocaleString("es-AR") + " IP en esta tabla.";
  }

  function updateMapLegend() {
    const observedCount = state.destinations.filter((item) => item.location_status === "located").length;
    const currentCount = state.currentDnsLookup
      ? state.currentDnsLookup.destinations.filter((item) => item.location_status === "located").length
      : 0;
    const labels = [];
    if (observedCount) labels.push(observedCount + " IP de eventos guardados");
    if (currentCount) labels.push(currentCount + " IP de una resolución DNS actual");
    $("geoMapLegend").textContent = labels.length
      ? labels.join(" · ")
      : "No hay coordenadas disponibles para los datos actuales";
  }

  function renderDomainLookup(lookup) {
    const container = $("geoDomainLookupResults");
    container.replaceChildren();
    container.hidden = false;
    container.append(element("h3", "Resolución actual de " + lookup.hostname));
    container.append(element(
      "p",
      lookup.dns_addresses.length + " dirección(es) devuelta(s) por DNS; " +
        lookup.destinations.length + " IP pública(s) consultada(s) en la base GeoIP local."
    ));
    container.append(element(
      "p",
      "Esta es una consulta actual. No confirma la IP que se usó en una visita anterior."
    ));
    if (!lookup.dns_addresses.length) {
      container.append(element("p", "El resolvedor no devolvió direcciones A/AAAA."));
      return;
    }

    const list = element("ul", undefined, "geo-dns-ip-list");
    const detailsContext = {
      kind: "current_dns",
      hostname: lookup.hostname,
      queried_at: lookup.queried_at,
      resolved_count: lookup.dns_addresses.length
    };
    lookup.dns_addresses.forEach((addressInfo) => {
      const address = addressInfo.ip;
      const item = lookup.destinations.find((entry) => entry.ip === address);
      const row = element("li", undefined, "geo-dns-ip-item");
      const info = document.createElement("div");
      info.append(element("strong", address, "geo-dns-ip-value"));
      info.append(element("span", addressInfo.family || "IP", "small"));
      info.append(element(
        "span",
        item ? locationLabel(item) : "Omitida: IP privada/especial o dato no geolocalizable",
        "small"
      ));
      if (item && item.country) {
        info.append(element("span", [item.city, item.country].filter(Boolean).join(", "), "small"));
      }
      if (item && item.asn) {
        info.append(element("span", "AS" + item.asn + (item.asn_organization ? " · " + item.asn_organization : ""), "small"));
      }
      row.append(info);
      if (item) {
        const button = element("button", "Ver en el mapa", "quiet tiny geo-select-ip");
        button.type = "button";
        button.addEventListener("click", () => {
          updateSelected(item, detailsContext);
          $("worldMap").scrollIntoView({ block: "center", behavior: "auto" });
        });
        row.append(button);
      }
      list.append(row);
    });
    container.append(list);
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    let body = {};
    try { body = await response.json(); } catch (_) { /* La respuesta puede no ser JSON. */ }
    if (!response.ok) {
      throw new Error(typeof body.detail === "string" ? body.detail : "La consulta local no terminó correctamente.");
    }
    return body;
  }

  function installDomainLookup() {
    const form = $("geoDomainLookupForm");
    const button = $("geoDomainLookupButton");
    const input = $("geoDomainInput");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (button.disabled) return;
      const hostname = input.value.trim();
      if (!hostname) return;
      button.disabled = true;
      state.currentDnsLookup = null;
      drawMarkers();
      updateMapLegend();
      $("geoDomainLookupResults").replaceChildren();
      $("geoDomainLookupResults").hidden = true;
      $("geoDomainLookupStatus").classList.remove("is-error");
      $("geoDomainLookupStatus").textContent = "Consultando el resolvedor DNS configurado…";
      try {
        const dns = await readJson("/api/tools/dns/lookup?hostname=" + encodeURIComponent(hostname));
        const addresses = Array.isArray(dns.addresses)
          ? dns.addresses
              .map((item) => typeof item === "string" ? { ip: item } : item)
              .filter((item) => item && typeof item.ip === "string")
          : [];
        if (!addresses.length) {
          $("geoDomainLookupStatus").textContent =
            "No se encontraron direcciones A/AAAA para " + (dns.hostname || hostname) + ".";
          return;
        }
        const geo = await postJson("/api/geolocation/lookup", {
          addresses: addresses.map((item) => item.ip).slice(0, 32)
        });
        state.currentDnsLookup = {
          ...geo,
          hostname: dns.hostname || hostname,
          dns_addresses: addresses.slice(0, 32).map((item) => ({
            ip: item.ip,
            family: item.family || (item.ip.includes(":") ? "IPv6" : "IPv4")
          })),
          destinations: Array.isArray(geo.destinations) ? geo.destinations : []
        };
        renderDomainLookup(state.currentDnsLookup);
        drawMarkers();
        updateMapLegend();
        const summary = geo.summary || {};
        $("geoDomainLookupStatus").textContent =
          "Consulta actual de " + state.currentDnsLookup.hostname + ": " +
          Number(summary.requested_ip_count || addresses.length) + " dirección(es), " +
          Number(summary.located_ip_count || 0) + " con coordenadas GeoIP locales. " +
          "No es evidencia de una IP histórica.";
      } catch (error) {
        $("geoDomainLookupStatus").classList.add("is-error");
        $("geoDomainLookupStatus").textContent =
          error && error.message ? error.message : "No se pudo consultar el dominio.";
      } finally {
        button.disabled = false;
      }
    });
  }

  function render(payload) {
    state.payload = payload;
    state.destinations = Array.isArray(payload.destinations) ? payload.destinations : [];
    const summary = payload.summary || {};
    $("geoStatEvents").textContent = Number(summary.total_events || 0).toLocaleString("es-AR");
    $("geoStatPublicIps").textContent = Number(summary.public_destination_ips_in_sample || 0).toLocaleString("es-AR");
    $("geoStatMapped").textContent = Number(summary.mapped_destination_ips || 0).toLocaleString("es-AR");
    $("geoStatNoIp").textContent = Number(summary.events_without_destination_ip || 0).toLocaleString("es-AR");

    const databases = payload.databases || {};
    const needSetup = !databases.geoip_library_available || !databases.city_configured;
    $("geoSetup").hidden = !needSetup;
    $("geoSetupDependency").textContent = databases.geoip_library_available
      ? "La biblioteca local de lectura GeoIP está instalada."
      : 'Falta la dependencia opcional. En el entorno de NetSentinel, ejecutá: python -m pip install -e ".[geoip]".';
    const cityStatus = databases.city_status || "database_missing";
    $("geoSetupDatabase").textContent = databases.city_configured
      ? "La base GeoLite2-City está disponible para consultas locales."
      : cityStatus === "database_invalid"
        ? "El archivo GeoLite2-City existe, pero no se pudo leer. Comprobá que sea una base MMDB válida y actualizada."
        : "Todavía no hay una base GeoLite2-City local disponible. Sin esa base, no se dibujan puntos sin coordenadas.";
    $("geoAsnStatus").textContent = databases.asn_configured
      ? "Base ASN local disponible."
      : 'La base ASN es opcional. Si la instalás, guardá GeoLite2-ASN.mmdb en el directorio de datos o definí NETSENTINEL_GEOIP_ASN_DB.';

    if (summary.limited) {
      $("geoMapLimitNotice").hidden = false;
      $("geoMapLimitNotice").textContent = "Hay más IP únicas guardadas que las incluidas en esta vista. Se muestran las direcciones con eventos más recientes; cambiá el límite de consulta en una futura versión para revisar lotes adicionales.";
    } else {
      $("geoMapLimitNotice").hidden = true;
      $("geoMapLimitNotice").textContent = "";
    }
    const located = Number(summary.mapped_destination_ips || 0);
    updateMapLegend();
    const sourceEvents = Number(summary.events_with_destination_ip || 0);
    $("geoMapStatus").classList.remove("is-error");
    $("geoMapStatus").textContent = sourceEvents
      ? "Resumen de " + sourceEvents.toLocaleString("es-AR") +
        " evento(s) con IP destino; " + located.toLocaleString("es-AR") +
        " dirección(es) tienen coordenadas. No es captura en vivo."
      : "No hay eventos guardados con una IP de destino. Importá registros autorizados que incluyan destination_ip para poblar el mapa.";
    renderTable();
    drawMarkers();
  }

  async function loadMap() {
    const refreshButtons = document.querySelectorAll(".js-refresh-world-map");
    refreshButtons.forEach((button) => { button.disabled = true; });
    $("geoMapStatus").classList.remove("is-error");
    $("geoMapStatus").textContent = "Leyendo eventos locales y cartografía incluida…";
    const jobs = await Promise.allSettled([
      readJson("/api/geolocation/map?limit=250"),
      readJson("/static/world_110m.geojson")
    ]);
    const payloadResult = jobs[0];
    const worldResult = jobs[1];

    if (worldResult.status === "fulfilled") {
      drawWorld(worldResult.value);
    } else {
      $("geoMapStatus").classList.add("is-error");
      $("geoMapStatus").textContent = "No se pudo cargar el mapa base local. La lista de IP seguirá disponible si la API responde.";
    }

    if (payloadResult.status === "fulfilled") {
      render(payloadResult.value);
    } else {
      $("geoMapStatus").classList.add("is-error");
      $("geoMapStatus").textContent = payloadResult.reason && payloadResult.reason.message
        ? payloadResult.reason.message : "No se pudo leer la actividad local.";
      $("geoDestinationsBody").replaceChildren();
      const row = document.createElement("tr");
      const cell = element("td", "No se pudo consultar el registro local de actividad.");
      cell.colSpan = 8;
      cell.className = "empty";
      row.append(cell);
      $("geoDestinationsBody").append(row);
    }
    refreshButtons.forEach((button) => { button.disabled = false; });
  }

  installDomainLookup();
  document.querySelectorAll(".js-refresh-world-map").forEach((button) => {
    button.addEventListener("click", loadMap);
  });
  $("geoDestinationFilter").addEventListener("input", renderTable);
  loadMap();
})();
