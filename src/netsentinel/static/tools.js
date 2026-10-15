(() => {
  const configStatus = document.getElementById("config-status");
  const configServers = document.getElementById("config-servers");
  fetch("/api/tools/dns/configuration", { headers: { "Accept": "application/json" }, cache: "no-store" })
    .then(async response => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo leer la configuración DNS.");
      configStatus.textContent = data.detected
        ? data.count + " servidor(es) detectado(s) · Fuente: " + data.source + " · Sistema: " + data.platform
        : "No se detectaron servidores DNS en la fuente consultada. Sistema: " + data.platform;
      for (const server of data.servers) {
        const row = document.createElement("div");
        row.className = "address";
        const value = document.createElement("strong");
        value.textContent = server;
        row.append(value);
        configServers.append(row);
      }
      const note = document.createElement("p");
      note.className = "muted";
      note.textContent = data.note;
      configServers.append(note);
    })
    .catch(error => { configStatus.textContent = error instanceof Error ? error.message : "No se pudo leer la configuración DNS."; });

  const form = document.getElementById("dns-form");
  const input = document.getElementById("hostname");
  const button = document.getElementById("submit");
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const hostname = input.value.trim();
    if (!hostname) return;
    button.disabled = true;
    status.textContent = "Consultando el resolvedor del sistema…";
    results.replaceChildren();
    try {
      const response = await fetch("/api/tools/dns/lookup?hostname=" + encodeURIComponent(hostname), {
        headers: { "Accept": "application/json" },
        cache: "no-store"
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo completar la consulta.");
      status.textContent = data.count
        ? "Se encontraron " + data.count + " dirección(es) para " + data.hostname + "."
        : "El resolvedor no devolvió direcciones para ese nombre.";
      for (const item of data.addresses) {
        const row = document.createElement("div");
        row.className = "address";
        const address = document.createElement("strong");
        address.textContent = item.ip;
        const family = document.createElement("span");
        family.className = "tag";
        family.textContent = item.family;
        row.append(address, family);
        results.append(row);
      }
    } catch (error) {
      status.textContent = error instanceof Error ? error.message : "Error inesperado en la consulta.";
    } finally {
      button.disabled = false;
    }
  });

  const ptrForm = document.getElementById("ptr-form");
  const addressInput = document.getElementById("address");
  const ptrButton = document.getElementById("ptr-submit");
  const ptrStatus = document.getElementById("ptr-status");
  ptrForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const address = addressInput.value.trim();
    if (!address) return;
    ptrButton.disabled = true;
    ptrStatus.textContent = "Consultando DNS inverso…";
    try {
      const response = await fetch("/api/tools/dns/reverse?address=" + encodeURIComponent(address), {
        headers: { "Accept": "application/json" },
        cache: "no-store"
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo completar la consulta PTR.");
      ptrStatus.textContent = data.ip + " → " + data.hostname + " (registro PTR) · " + (data.cache_hit ? "resultado en caché" : "consulta nueva") + (data.resolved_at ? " · resuelto: " + data.resolved_at : "");
    } catch (error) {
      ptrStatus.textContent = error instanceof Error ? error.message : "Error inesperado en la consulta PTR.";
    } finally {
      ptrButton.disabled = false;
    }
  });
  const tlsForm = document.getElementById("tls-form");
  const tlsHost = document.getElementById("tls-host");
  const tlsPort = document.getElementById("tls-port");
  const tlsButton = document.getElementById("tls-submit");
  const tlsStatus = document.getElementById("tls-status");
  const tlsResults = document.getElementById("tls-results");

  function appendTLSValue(label, value) {
    if (value === null || value === undefined || value === "") return;
    const row = document.createElement("div");
    row.className = "address";
    const key = document.createElement("strong");
    key.textContent = label;
    const text = document.createElement("span");
    text.className = "tag";
    text.textContent = String(value);
    row.append(key, text);
    tlsResults.append(row);
  }

  tlsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const host = tlsHost.value.trim();
    const port = Number(tlsPort.value);
    if (!host || !Number.isInteger(port) || port < 1 || port > 65535) return;
    tlsButton.disabled = true;
    tlsStatus.textContent = "Conectando al endpoint y validando el certificado…";
    tlsResults.replaceChildren();
    try {
      const response = await fetch("/api/tools/tls/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify({ host, port }),
        cache: "no-store"
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo inspeccionar el endpoint TLS.");
      tlsStatus.textContent = data.summary || "Inspección TLS completada.";
      appendTLSValue("Endpoint", data.host + ":" + data.port);
      appendTLSValue("Estado", data.status);
      if (data.certificate) {
        appendTLSValue("Sujeto", data.certificate.subject);
        appendTLSValue("Emisor", data.certificate.issuer);
        appendTLSValue("Válido desde", data.certificate.valid_from);
        appendTLSValue("Vence", data.certificate.valid_until);
        appendTLSValue("Días hasta el vencimiento", data.certificate.days_remaining);
        if (data.certificate.dns_names && data.certificate.dns_names.length) {
          appendTLSValue("Nombres del certificado", data.certificate.dns_names.join(", "));
        }
      }
      if (data.tls) {
        appendTLSValue("Versión TLS", data.tls.version);
        appendTLSValue("Cifrado negociado", data.tls.cipher);
        appendTLSValue("Tamaño de clave del cifrado (bits)", data.tls.cipher_bits);
      }
      for (const finding of data.findings || []) {
        const row = document.createElement("div");
        row.className = "address";
        const content = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = finding.title || finding.code || "Hallazgo";
        const detail = document.createElement("div");
        detail.className = "tag";
        detail.textContent = finding.detail || "";
        content.append(title, detail);
        const severity = document.createElement("span");
        severity.className = "tag";
        severity.textContent = finding.severity || "info";
        row.append(content, severity);
        tlsResults.append(row);
      }
      if (data.notice) {
        const note = document.createElement("p");
        note.className = "muted";
        note.textContent = data.notice;
        tlsResults.append(note);
      }
    } catch (error) {
      tlsStatus.textContent = error instanceof Error ? error.message : "No se pudo completar la inspección TLS.";
    } finally {
      tlsButton.disabled = false;
    }
  });
})();
