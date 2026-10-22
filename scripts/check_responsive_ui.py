#!/usr/bin/env python3
"""Comprueba la interfaz web de NetSentinel en varios tamaños de ventana.

Por defecto inicia una instancia local temporal con una base SQLite nueva.
No inicia descubrimientos ni ejecuta diagnósticos de red.
"""

from __future__ import annotations

import argparse
import hashlib
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
from urllib.parse import urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIEWPORTS_TEXT = (
    "320x640,360x800,390x844,430x932,560x800,620x900,760x900,"
    "768x1024,900x900,1024x768,1080x800,1081x900,1280x720,"
    "1440x900,1920x1080"
)
PAGE_CASES = (
    ("/", "Inventario de red", "inventario"),
    ("/network", "Explorador de red", "mapa-de-red"),
    ("/findings", "Hallazgos con evidencia", "hallazgos"),
    ("/monitors", "Monitorización", "monitorizacion"),
    ("/tools", "Herramientas de red", "herramientas"),
    ("/activity", "Actividad y telemetría", "actividad"),
    ("/forensics", "Área de análisis forense", "forensics"),
    ("/world-map", "Mapa mundial de IP", "geolocation"),
    ("/guided-test", "Asistente de pruebas", "guided-test"),
)


@dataclass(frozen=True)
class Viewport:
    """Ancho y alto CSS de una ventana de prueba."""

    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


def parse_viewports(value: str) -> tuple[Viewport, ...]:
    """Convierte 'ancho x alto' en una lista validada de tamaños de ventana."""
    viewports: list[Viewport] = []
    seen: set[tuple[int, int]] = set()

    for raw_item in value.split(","):
        item = raw_item.strip().lower().replace(" ", "")
        match = re.fullmatch(r"(\d{2,4})x(\d{2,4})", item)
        if not match:
            raise ValueError(
                f"Tamaño inválido: {raw_item!r}. Usá el formato 390x844 y separá tamaños con comas."
            )

        width, height = (int(match.group(1)), int(match.group(2)))
        if not 280 <= width <= 3840:
            raise ValueError(f"El ancho {width} está fuera del rango permitido (280 a 3840).")
        if not 320 <= height <= 2160:
            raise ValueError(f"El alto {height} está fuera del rango permitido (320 a 2160).")
        pair = (width, height)
        if pair in seen:
            raise ValueError(f"El tamaño {width}x{height} está repetido.")
        seen.add(pair)
        viewports.append(Viewport(width, height))

    if not viewports:
        raise ValueError("Indicá al menos un tamaño de ventana.")
    return tuple(viewports)


DEFAULT_VIEWPORTS = parse_viewports(DEFAULT_VIEWPORTS_TEXT)


def _free_local_port() -> int:
    """Busca un puerto local libre para la instancia temporal."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])



def _seed_topology_fixture(data_dir: Path) -> None:
    """Crea datos sintéticos de inventario y monitorización, sin sondear una red real."""
    import os

    from netsentinel import database
    from netsentinel.discovery import Neighbor

    database_file = data_dir / "netsentinel.sqlite3"
    previous_data_dir = os.environ.get("NETSENTINEL_DATA_DIR")
    os.environ["NETSENTINEL_DATA_DIR"] = str(data_dir)
    try:
        database.initialize(database_file)
        database.record_scan(
            [
                Neighbor(
                    "192.168.56.20",
                    "02:00:00:00:00:20",
                    "fixture0",
                    "responsive-ui-fixture",
                ),
                Neighbor(
                    "192.168.56.21",
                    "02:00:00:00:00:20",
                    "fixture0",
                    "responsive-ui-fixture",
                ),
            ],
            path=database_file,
            discovery={
                "networks": [{
                    "network": "192.168.56.0/24",
                    "interface": "fixture0",
                    "local_address": "192.168.56.10",
                    "range_limited": False,
                }],
                "addresses_checked": 1,
                "ping_responses": 1,
                "duration_seconds": 0.01,
                "scope": "Fixture sintético para pruebas del navegador; no representa una red real.",
            },
        )
        # Una segunda captura sintética permite comprobar la comparación sin tocar la red.
        database.record_scan(
            [Neighbor(
                "192.168.56.20",
                "02:00:00:00:00:20",
                "fixture0",
                "responsive-ui-fixture",
            )],
            path=database_file,
            discovery={
                "networks": [{
                    "network": "192.168.56.0/24",
                    "interface": "fixture0",
                    "local_address": "192.168.56.10",
                    "range_limited": False,
                }],
                "addresses_checked": 1,
                "ping_responses": 1,
                "duration_seconds": 0.01,
                "scope": "Fixture sintético para pruebas del navegador; no representa una red real.",
            },
        )

        # Marca explícitamente el origen de la lectura generada por esta suite.
        # El asistente prueba la procedencia, no debe confundir esta fixture con un escaneo real.
        # La UI de monitorización y el asistente usan intervalos históricos ficticios.
        from datetime import datetime, timedelta, timezone

        synthetic_first_seen = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        with database.connect(database_file) as db:
            db.execute(
                "UPDATE scans SET source = 'synthetic-test-fixture' WHERE source LIKE '%responsive-ui-fixture%'"
            )
            db.execute(
                "UPDATE device_addresses SET source = 'synthetic-test-fixture', first_seen = ?, last_seen = ? "
                "WHERE interface = 'fixture0' AND ip_address LIKE '192.168.56.%'",
                (synthetic_first_seen, datetime.now(timezone.utc).isoformat()),
            )
            db.execute(
                "UPDATE devices SET first_seen = ?, last_seen = ? WHERE ip_address LIKE '192.168.56.%'",
                (synthetic_first_seen, datetime.now(timezone.utc).isoformat()),
            )
            db.execute(
                "UPDATE observations SET source = 'synthetic-test-fixture' "
                "WHERE scan_id IN (SELECT id FROM scans WHERE source = 'synthetic-test-fixture')"
            )

        monitor = database.create_monitor(
            "Monitor de prueba accesible",
            "tcp",
            "127.0.0.1:443",
            60,
            3,
            path=database_file,
        )
        database.record_monitor_check(
            monitor["id"], "up", 12.5, "Respuesta simulada", path=database_file
        )
        database.record_monitor_check(
            monitor["id"], "down", None, "Fallo simulado sin latencia", path=database_file
        )
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        with database.connect(database_file) as db:
            check_ids = [
                int(row["id"])
                for row in db.execute(
                    "SELECT id FROM monitor_checks WHERE monitor_id = ? ORDER BY id",
                    (monitor["id"],),
                )
            ]
            db.execute(
                "UPDATE monitor_checks SET checked_at = ? WHERE id = ?",
                (now.isoformat(), check_ids[0]),
            )
            db.execute(
                "UPDATE monitor_checks SET checked_at = ? WHERE id = ?",
                ((now - timedelta(hours=2)).isoformat(), check_ids[1]),
            )

        # Caso forense sintético para probar el registro visible de un intento fallido.
        # El archivo NO se crea: Chromium debe ver el error y el historial actualizado.
        from netsentinel import forensics_service

        forensic_case = forensics_service.create_case(
            case_number="UI-FORENSICS-001",
            title="Caso sintético de navegador",
            authority_reference="AUTORIZACION-SINTETICA-001",
            objective="Comprobar el registro visible de errores de lectura.",
            scope="Solo datos sintéticos de la prueba Chromium.",
            examiner="Examinador sintético",
            actor="Prueba automatizada",
        )
        forensics_service.add_evidence(
            case_id=forensic_case["id"],
            label="Archivo sintético no creado",
            source_type="file_copy",
            original_name="missing-synthetic-evidence.bin",
            source_description="Elemento sintético para probar un error de lectura.",
            received_from="Fuente sintética",
            received_by="Examinador sintético UI",
            received_at_original=datetime.now(timezone.utc).isoformat(),
            received_timezone="UTC",
            size_bytes=None,
            reported_sha256=hashlib.sha256(b"synthetic evidence reference").hexdigest(),
            hash_source="Fixture automática de Chromium",
            actor="Prueba automatizada",
        )
    finally:
        if previous_data_dir is None:
            os.environ.pop("NETSENTINEL_DATA_DIR", None)
        else:
            os.environ["NETSENTINEL_DATA_DIR"] = previous_data_dir


def _read_recent_log(log_stream) -> str:
    log_stream.flush()
    log_stream.seek(0)
    return log_stream.read()[-4000:]


def _wait_for_server(base_url: str, process: subprocess.Popen, log_stream) -> None:
    """Espera a que la app temporal responda o informa por qué no arrancó."""
    deadline = time.monotonic() + 25
    last_error = "todavía no responde"

    while time.monotonic() < deadline:
        if process.poll() is not None:
            details = _read_recent_log(log_stream)
            raise RuntimeError(
                "NetSentinel terminó antes de estar disponible.\n"
                f"Salida reciente del servidor:\n{details or '(sin mensajes)'}"
            )
        try:
            with urlopen(f"{base_url}/", timeout=1) as response:
                if response.status == 200:
                    return
                last_error = f"respondió con HTTP {response.status}"
        except (URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)
        time.sleep(0.25)

    details = _read_recent_log(log_stream)
    raise RuntimeError(
        f"NetSentinel no estuvo listo en 25 segundos ({last_error}).\n"
        f"Salida reciente del servidor:\n{details or '(sin mensajes)'}"
    )


def _stop_server(process: subprocess.Popen) -> None:
    """Cierra solo el proceso que abrió esta comprobación."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _validate_local_url(value: str) -> str:
    """Permite probar una instancia existente, siempre en loopback."""
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "http" or host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("--base-url debe ser una URL HTTP local, como http://127.0.0.1:8765.")
    if parsed.username or parsed.password:
        raise ValueError("--base-url no debe incluir usuario ni contraseña.")
    return value.rstrip("/")


def _page_metrics(page) -> dict:
    return page.evaluate(
        """() => ({
          viewportWidth: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          documentHeight: document.documentElement.scrollHeight
        })"""
    )


def _inventory_layout_failures(page, viewport: Viewport) -> list[str]:
    """Comprueba que el inventario cambie de cuadrícula sin solapar paneles."""
    boxes = page.evaluate(
        """() => Object.fromEntries(
          [
            "inventory-panel",
            "activity-panel",
            "diagnostics-panel",
            "scans-panel"
          ].map((name) => {
            const element = document.querySelector("." + name);
            if (!element) return [name, null];
            const rect = element.getBoundingClientRect();
            return [name, {
              left: rect.left,
              top: rect.top,
              right: rect.right,
              bottom: rect.bottom,
              width: rect.width,
              height: rect.height
            }];
          })
        )"""
    )
    failures: list[str] = []
    if any(boxes.get(name) is None for name in (
        "inventory-panel", "activity-panel", "diagnostics-panel", "scans-panel"
    )):
        return ["falta uno o más paneles de la cuadrícula del Inventario"]

    inventory = boxes["inventory-panel"]
    activity = boxes["activity-panel"]
    diagnostics = boxes["diagnostics-panel"]
    scans = boxes["scans-panel"]
    tolerance = 3

    if min(box["width"] for box in boxes.values()) < 1:
        failures.append("uno o más paneles del Inventario no tienen ancho visible")

    if viewport.width > 1080:
        if abs(inventory["left"] - diagnostics["left"]) > tolerance:
            failures.append("Diagnóstico no queda debajo del Inventario")
        if abs(activity["left"] - scans["left"]) > tolerance:
            failures.append("Historial no queda debajo de Actividad reciente")
        if diagnostics["top"] < inventory["bottom"] - tolerance:
            failures.append("Diagnóstico invade verticalmente el Inventario")
        if scans["top"] < activity["bottom"] - tolerance:
            failures.append("Historial invade verticalmente Actividad reciente")
        for upper, lower, label in (
            (inventory, diagnostics, "Inventario y Diagnóstico"),
            (activity, scans, "Actividad reciente e Historial"),
        ):
            gap = lower["top"] - upper["bottom"]
            if gap > 36:
                failures.append(f"{label} dejan un hueco vertical innecesario ({gap:.0f}px)")
    else:
        # En móvil se sigue el orden de lectura por columnas: Inventario,
        # Diagnóstico y luego Actividad reciente e Historial.
        ordered = [inventory, diagnostics, activity, scans]
        if any(
            ordered[index + 1]["top"] < ordered[index]["bottom"] - tolerance
            for index in range(len(ordered) - 1)
        ):
            failures.append("los paneles no se apilan en el orden de columnas en una ventana estrecha")
        if any(abs(box["left"] - inventory["left"]) > tolerance for box in ordered):
            failures.append("los paneles estrechos no comparten el mismo margen izquierdo")

    return failures




def _topology_panel_failures(page, check_missing_evidence: bool = False) -> list[str]:
    """Comprueba el explorador de red con una fixture sintética y controles reales."""
    failures: list[str] = []
    panel = page.locator("#topologyPanel")
    if panel.count() != 1:
        return ["no aparece un único explorador de topología"]

    try:
        page.wait_for_function(
            """() => {
              const canvas = document.querySelector("#topologyCanvas canvas");
              const graph = window.NetSentinelTopology;
              const stats = graph && graph.getGraphStats ? graph.getGraphStats() : null;
              return canvas && stats && stats.deviceCount > 0;
            }""",
            timeout=5000,
        )
    except Exception as exc:
        return [f"el mapa no terminó de dibujar la fixture de prueba: {exc}"]

    if page.locator("#networkObservedMetric").inner_text().strip() != "1":
        failures.append("el resumen no cuenta el dispositivo observado en la lectura sintética")
    if page.locator("#networkSubnetMetric").inner_text().strip() != "1":
        failures.append("el resumen no cuenta la subred registrada en la lectura sintética")

    accessible_details = panel.locator("details.topology-accessible")
    if accessible_details.count() != 1:
        failures.append("falta la alternativa textual del mapa")
    elif accessible_details.get_attribute("open") is None:
        accessible_details.locator("summary").click()

    for selector, description in (
        ("#topologyScanSelect", "el selector de lectura del mapa"),
        ("#topologySearch", "el filtro de dispositivos"),
        ("#topologyStatusFilter", "el filtro de estado"),
        ("#topologyResetSearch", "el botón para limpiar filtros"),
        ("#topologyZoomIn", "el botón para acercar"),
        ("#topologyZoomOut", "el botón para alejar"),
        ("#topologyFit", "el botón para ajustar el mapa"),
        ("#topologyRelayout", "el botón para reorganizar el mapa"),
        ("#topologyCanvas", "el área del grafo"),
        ("#topologySelection", "el panel de detalle"),
        ("#topologyHistory", "el historial de observaciones"),
        ("#topologyEvents", "los cambios registrados"),
        ("#topologyAccessibleList", "la alternativa textual"),
    ):
        element = panel.locator(selector)
        if element.count() != 1:
            failures.append(f"falta {description}")
        elif not element.is_visible():
            failures.append(f"no está visible {description}")

    try:
        node = panel.locator("#topologyAccessibleList .topology-accessible-node").first
        keyboard_device_id = node.get_attribute("data-device-id")
        node.focus()
        node.press("Enter")
        try:
            page.wait_for_function(
                """(deviceId) => {
                  const focused = document.activeElement;
                  return focused && focused.matches("button.topology-accessible-node") &&
                    focused.dataset.deviceId === deviceId &&
                    focused.getAttribute("aria-pressed") === "true";
                }""",
                arg=keyboard_device_id,
                timeout=2500,
            )
        except Exception:
            failures.append("la selección por teclado perdió el foco del dispositivo después de actualizar aria-pressed")
        # Space también debe activar la selección sin sacar el foco de la lista.
        node.press("Space")
        try:
            page.wait_for_function(
                """(deviceId) => {
                  const focused = document.activeElement;
                  return focused && focused.matches("button.topology-accessible-node") &&
                    focused.dataset.deviceId === deviceId &&
                    focused.getAttribute("aria-pressed") === "true";
                }""",
                arg=keyboard_device_id,
                timeout=2500,
            )
        except Exception:
            failures.append("la selección con Espacio no conservó el foco del dispositivo")
        detail = panel.locator("#topologySelection")
        page.wait_for_function(
            "() => document.querySelector('#topologySelection')?.textContent.toLocaleLowerCase().includes('lectura #')",
            timeout=4000,
        )
        if "192.168.56.20" not in detail.inner_text():
            failures.append("el detalle no muestra la dirección observada en la fixture")
        if "Historial de observaciones" not in panel.inner_text():
            failures.append("el panel no explica que la línea temporal es de observaciones")
        if "Cambios registrados" not in panel.inner_text():
            failures.append("falta la sección que explica los eventos de inventario")
        phase = "cargar eventos del dispositivo seleccionado"
        page.wait_for_function(
            "() => document.querySelectorAll('#topologyEvents .topology-history-entry').length > 0",
            timeout=7000,
        )
        if "Dispositivo detectado por primera vez" not in panel.locator("#topologyEvents").inner_text():
            failures.append("el detalle no muestra un evento del inventario asociado al dispositivo seleccionado")
        if check_missing_evidence:
            try:
                device_id = node.get_attribute("data-device-id")
                update = page.evaluate(
                    """async (id) => {
                      const response = await fetch('/api/devices/' + encodeURIComponent(id), {
                        method: 'PATCH',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({trusted: true})
                      });
                      return {status: response.status, body: await response.json()};
                    }""",
                    device_id,
                )
                if update["status"] != 200:
                    failures.append("no se pudo generar el cambio sintético de confianza para probar la actualización")
                else:
                    page.locator("#refreshBtn").click()
                    page.wait_for_function(
                        "() => document.querySelector('#topologyEvents')?.textContent.includes('Cambio en el estado de confianza')",
                        timeout=4000,
                    )
            except Exception as exc:
                failures.append(f"el botón de actualización no refrescó el contexto del equipo seleccionado: {exc}")


        if check_missing_evidence:
            scan_select = page.locator("#topologyScanSelect")
            options = scan_select.locator("option").evaluate_all("(items) => items.map(item => item.value).filter(Boolean)")
            if len(options) < 2:
                failures.append("la fixture no ofrece dos lecturas para seleccionar")
            else:
                latest_id = scan_select.input_value()
                previous_id = next((value for value in options if value != latest_id), None)
                if previous_id is None:
                    failures.append("no se encontró una captura anterior diferente")
                else:
                    scan_select.select_option(value=previous_id)
                    page.wait_for_function(
                        "() => document.querySelector('#topologySummary')?.textContent.includes('Vista histórica elegida')",
                        timeout=4000,
                    )
                    if scan_select.input_value() != previous_id:
                        failures.append("el explorador no conservó la captura histórica elegida")
                    scan_select.select_option(value=latest_id)
                    page.wait_for_function(
                        "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats().deviceCount > 0",
                        timeout=4000,
                    )

        page.locator("#topologyZoomIn").click()
        page.locator("#topologyFit").click()
        search = panel.locator("#topologySearch")
        reset = panel.locator("#topologyResetSearch")
        phase = "aplicar un filtro sin coincidencias"
        search.fill("filtro-sin-coincidencias")
        page.wait_for_function(
            "() => window.NetSentinelTopology.getGraphStats().deviceCount === 0",
            timeout=5000,
        )
        phase = "restablecer los filtros y recuperar los nodos"
        reset.click()
        page.wait_for_function(
            "() => window.NetSentinelTopology.getGraphStats().deviceCount > 0",
            timeout=5000,
        )
    except Exception as exc:
        failures.append(f"no se pudo {locals().get('phase', 'seleccionar o filtrar un nodo del mapa')}: {exc}")

    metrics = _page_metrics(page)
    if metrics["documentWidth"] > metrics["viewportWidth"] + 1:
        failures.append(
            "el mapa abierto produce desplazamiento horizontal global "
            f"(documento {metrics['documentWidth']} px, ventana {metrics['viewportWidth']} px)"
        )
    if check_missing_evidence:
        # Cambiar tema debe actualizar los estilos del mapa sin romper la vista.
        theme_group = page.locator('input[name="themeSelect"]')
        if theme_group.count() != 3:
            failures.append("el selector no ofrece exactamente los tres temas documentados")
        selected_theme = page.locator('input[name="themeSelect"]:checked').input_value()
        for theme in ("dark", "medium", "light"):
            # Los radios están visualmente ocultos para mantener el diseño accesible.
            # Hacer clic en la tarjeta visible activa el control asociado de forma real.
            page.locator(f'input[name="themeSelect"][value="{theme}"] + .theme-option-card').click()
            try:
                page.wait_for_function(
                    "(expected) => document.documentElement.dataset.theme === expected",
                    arg=theme,
                    timeout=2500,
                )
                theme_tokens = page.evaluate(
                    "() => getComputedStyle(document.documentElement).getPropertyValue('--theme-text').trim()"
                )
                if not theme_tokens:
                    failures.append(f"el tema {theme!r} no proporciona el color de texto del mapa")
            except Exception as exc:
                failures.append(f"no se pudo aplicar el tema {theme!r} al explorador: {exc}")
        page.locator(f'input[name="themeSelect"][value="{selected_theme}"] + .theme-option-card').click()

        # Comprueba que el mapa se recupera de preferencias locales corruptas,
        # vuelve a guardar posiciones válidas y mantiene el límite de entradas.
        position_key = "netsentinel-topology-positions-v1"
        previous_positions = page.evaluate("(key) => localStorage.getItem(key)", position_key)
        try:
            page.evaluate("(key) => localStorage.setItem(key, '{malformed')", position_key)
            page.reload(wait_until="load", timeout=20000)
            page.wait_for_function(
                "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats().deviceCount > 0",
                timeout=5000,
            )
            # El grafo guarda posiciones cuando el layout termina; no leer
            # localStorage inmediatamente después del primer nodo visible.
            page.wait_for_function(
                """(key) => {
                  try {
                    const value = JSON.parse(localStorage.getItem(key) || "null");
                    return value && typeof value === "object" && !Array.isArray(value) &&
                      Object.entries(value).length > 0;
                  } catch (_) {
                    return false;
                  }
                }""",
                arg=position_key,
                timeout=5000,
            )
            position_report = page.evaluate(
                """(key) => {
                  try {
                    const raw = localStorage.getItem(key);
                    const value = JSON.parse(raw || "null");
                    if (!value || typeof value !== "object" || Array.isArray(value)) {
                      return {valid: false, count: 0, positionsValid: false};
                    }
                    const entries = Object.entries(value);
                    return {
                      valid: true,
                      count: entries.length,
                      positionsValid: entries.every(([, position]) =>
                        position && Number.isFinite(Number(position.x)) &&
                        Number.isFinite(Number(position.y)) &&
                        Math.abs(Number(position.x)) < 1000000 &&
                        Math.abs(Number(position.y)) < 1000000
                      )
                    };
                  } catch (_) {
                    return {valid: false, count: 0, positionsValid: false};
                  }
                }""",
                position_key,
            )
            if not position_report.get("valid") or position_report.get("count", 0) == 0:
                failures.append("el mapa no recupera ni vuelve a guardar posiciones después de preferencias corruptas")
            if position_report.get("count", 0) > 1200:
                failures.append("las posiciones guardadas superan el límite de 1200 nodos")
            if not position_report.get("positionsValid"):
                failures.append("el mapa guardó coordenadas de nodos inválidas o fuera de rango")
        except Exception as exc:
            failures.append(f"no se pudo verificar la recuperación de las posiciones guardadas: {exc}")
        finally:
            try:
                if previous_positions is None:
                    page.evaluate("(key) => localStorage.removeItem(key)", position_key)
                else:
                    page.evaluate("(args) => localStorage.setItem(args.key, args.value)", {
                        "key": position_key,
                        "value": previous_positions,
                    })
                page.reload(wait_until="load", timeout=20000)
                page.wait_for_function(
                    "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats().deviceCount > 0",
                    timeout=5000,
                )
            except Exception as exc:
                failures.append(f"no se pudo restaurar la preferencia de posiciones tras la prueba: {exc}")

    if check_missing_evidence:
        pattern = "**/api/scans/*/topology"
        try:
            # Comprueba el caso de una lectura válida con subred registrada y
            # sin dispositivos observados. El mapa debe dibujar solo la subred.
            selected_scan_id = page.locator("#topologyScanSelect").input_value()
            subnet_only_payload = {
                "scan_id": selected_scan_id,
                "captured_at": "2026-10-19T10:00:00+00:00",
                "evidence_available": True,
                "network_scope_available": True,
                "nodes": [{
                    "id": "subnet:fixture-empty@fixture0",
                    "kind": "subnet",
                    "label": "192.168.56.0/24",
                    "network_id": "subnet:fixture-empty@fixture0",
                    "interface": "fixture0",
                    "local_address": "192.168.56.10",
                    "range_limited": False,
                    "detail": "Interfaz fixture0",
                }],
                "edges": [],
                "stats": {
                    "observed_devices": 0,
                    "known_subnets": 1,
                    "observed_memberships": 0,
                    "unlinked_devices": 0,
                },
                "warnings": [],
            }
            def _serve_subnet_only_topology(route):
                requested_scan_id = urlsplit(route.request.url).path.rstrip("/").rsplit("/", 2)[-2]
                payload = {**subnet_only_payload, "scan_id": requested_scan_id}
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps(payload),
                )

            page.route(pattern, _serve_subnet_only_topology)
            page.reload(wait_until="load", timeout=20000)
            page.wait_for_function(
                "() => { const graph = window.NetSentinelTopology; const stats = graph && graph.getGraphStats ? graph.getGraphStats() : null; return stats && stats.nodeCount >= 1 && stats.edgeCount === 0; }",
                timeout=5000,
            )
            if page.locator("#networkSubnetMetric").inner_text().strip() != "1":
                failures.append("la lectura sin equipos no conserva el recuento de la subred registrada")
        except Exception as exc:
            failures.append(f"la lectura válida sin dispositivos no conserva su nodo de subred: {exc}")
        finally:
            try:
                page.unroute(pattern)
                page.reload(wait_until="load", timeout=20000)
                page.wait_for_function(
                    "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats().deviceCount > 0",
                    timeout=5000,
                )
            except Exception as exc:
                failures.append(f"no se pudo restaurar el mapa con dispositivos después de la prueba de subred vacía: {exc}")

    if check_missing_evidence:
        pattern = "**/api/scans/*/topology"
        try:
            # Simula que la API del grafo no puede recuperar una lectura. La vista
            # no debe inventar líneas ni traducir la falta de datos en un cero confirmado.
            page.route(
                pattern,
                lambda route: route.fulfill(
                    status=503,
                    content_type="application/json",
                    body='{"detail":"Fallo sintético de lectura histórica"}',
                ),
            )
            page.reload(wait_until="load", timeout=20000)
            page.wait_for_function(
                "() => document.querySelector('#topologySummary')?.textContent.includes('No se pudo recuperar la evidencia exacta')",
                timeout=5000,
            )
            if page.locator("#networkObservedMetric").inner_text().strip() != "—":
                failures.append("la falta de evidencia se muestra como un cero confirmado en lugar de dato desconocido")
            graph_stats = page.evaluate(
                "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats()"
            )
            if graph_stats and graph_stats.get("edgeCount") != 0:
                failures.append("el explorador dibuja relaciones cuando no se recuperó la evidencia histórica")
            if graph_stats and graph_stats.get("deviceCount") != 0:
                failures.append("el explorador muestra equipos como confirmados cuando la lectura no se recuperó")
        except Exception as exc:
            failures.append(f"no se pudo comprobar el estado de evidencia no disponible: {exc}")
        finally:
            try:
                page.unroute(pattern)
                page.reload(wait_until="load", timeout=20000)
                page.wait_for_function(
                    "() => window.NetSentinelTopology && window.NetSentinelTopology.getGraphStats().deviceCount > 0",
                    timeout=5000,
                )
            except Exception as exc:
                failures.append(f"no se pudo restaurar la vista con evidencia tras la prueba: {exc}")

    return failures


def _scan_comparison_failures(page) -> list[str]:
    """Comprueba la comparación con dos capturas sintéticas de la misma subred."""
    failures: list[str] = []
    first = page.locator("#scanCompareFirst")
    second = page.locator("#scanCompareSecond")
    button = page.locator("#scanCompareButton")
    result = page.locator("#scanComparisonResult")
    if first.count() != 1 or second.count() != 1 or button.count() != 1 or result.count() != 1:
        return ["falta uno de los controles de comparación de lecturas"]

    # La navegación histórica debe poder encontrarse y leerse en ambas páginas.
    history_button = page.locator("#loadMoreScansButton")
    history_status = page.locator("#scanHistoryLoadStatus")
    if history_button.count() != 1 or history_status.count() != 1:
        failures.append("falta el control accesible para continuar el historial de capturas")
    else:
        if not history_button.is_visible():
            failures.append("el control para cargar capturas anteriores no está visible")
        if not history_status.is_visible() or not history_status.inner_text().strip():
            failures.append("el estado de carga del historial no está visible o no tiene texto")
        if not history_button.inner_text().strip():
            failures.append("el control para cargar capturas anteriores no tiene una etiqueta")

    try:
        page.wait_for_function(
            """() => {
              const first = document.querySelector("#scanCompareFirst");
              const second = document.querySelector("#scanCompareSecond");
              const button = document.querySelector("#scanCompareButton");
              return first && second && button && first.value && second.value &&
                first.value !== second.value && !button.disabled;
            }""",
            timeout=5000,
        )
        button.click()
        page.wait_for_function(
            """() => {
              const result = document.querySelector("#scanComparisonResult");
              return result && result.textContent.includes("Cambió el conjunto de direcciones observadas") &&
                result.textContent.includes("192.168.56.21") &&
                result.textContent.includes("synthetic-test-fixture") &&
                result.textContent.includes("No demuestra");
            }""",
            timeout=5000,
        )
    except Exception as exc:
        return [f"la comparación entre capturas sintéticas no terminó correctamente: {exc}"]

    rendered = result.inner_text()
    evidence_note = page.locator("#scanComparisonEvidenceNote")
    if evidence_note.count() != 1:
        failures.append("falta la nota que distingue la identidad actual de la evidencia histórica")
    else:
        note_text = evidence_note.inner_text()
        if "ficha actual del inventario" not in note_text or "captura guardada" not in note_text:
            failures.append("la comparación no aclara qué datos son históricos y cuáles vienen del inventario actual")
    if "192.168.56.0/24" not in rendered:
        failures.append("la comparación no informa la subred compartida")
    if "192.168.56.21" not in rendered or "synthetic-test-fixture" not in rendered:
        failures.append("la comparación no vincula las IP modificadas con su fuente histórica")
    evidence_rows = page.locator(".scan-compare-evidence .scan-compare-item-meta")
    if evidence_rows.count() < 3:
        failures.append("la comparación no muestra hora, dirección y fuente para cada evidencia")
    elif any("Fuente: synthetic-test-fixture" not in value for value in evidence_rows.all_inner_texts()):
        failures.append("alguna observación del cambio perdió su fuente original")
    if "No demuestra que esté desconectado" not in rendered:
        failures.append("la comparación no explica el límite de interpretar ausencias")

    scan_select = page.locator("#topologyScanSelect")
    if scan_select.count() == 1:
        baseline_id = first.input_value()
        change = result.locator(".scan-compare-item").first
        device_id = change.get_attribute("data-device-id")
        action = page.get_by_role(
            "button",
            name=f"Ver equipo #{device_id} en la captura anterior #{baseline_id} en el mapa",
        )
        if action.count() != 1:
            failures.append("la diferencia no ofrece una acción accesible para abrir y seleccionar el equipo")
        else:
            try:
                action.click()
                page.wait_for_function(
                    """(expected) => {
                      const scanSelect = document.querySelector('#topologyScanSelect');
                      const selected = document.querySelector('#topologyAccessibleList .topology-accessible-node[aria-pressed=' + JSON.stringify('true') + ']');
                      return scanSelect?.value === expected.scanId &&
                        selected?.dataset.deviceId === expected.deviceId;
                    }""",
                    arg={"scanId": baseline_id, "deviceId": device_id},
                    timeout=7000,
                )
                selected_text = page.locator("#topologySelection").inner_text()
                if "192.168.56.21" not in selected_text:
                    failures.append("el detalle del dispositivo no muestra la IP histórica que motivó la diferencia")
            except Exception as exc:
                failures.append(f"no se pudo abrir la captura y seleccionar el equipo que sustenta la diferencia: {exc}")
    return failures



def _zeek_import_ui_failures(page, base_url: str, viewport: Viewport) -> list[str]:
    """Comprueba vista previa sin escritura e importación explícita de Zeek en Chromium."""
    failures: list[str] = []
    source_event_id = f"zeek:CZeekUI{viewport.width}x{viewport.height}"
    tab = page.get_by_role("tab", name="Importar")
    if tab.count() != 1:
        return ["no se encontró la pestaña Importar de Actividad"]

    try:
        tab.click()
        device_select = page.locator("#zeekDevice")
        page.wait_for_function(
            "() => { const select = document.querySelector('#zeekDevice'); "
            "return !!select && Array.from(select.options).some(option => option.value); }",
            timeout=5000,
        )
        options = device_select.locator("option").evaluate_all(
            "(items) => items.filter(item => item.value).map(item => item.value)"
        )
        if not options:
            return ["la importación Zeek no recibió dispositivos del inventario"]
        device_id = options[0]

        addresses_response = page.request.get(
            f"{base_url}/api/devices/{device_id}/addresses",
            timeout=5000,
        )
        if addresses_response.status != 200:
            return [f"no se pudo preparar la prueba Zeek: la consulta de direcciones respondió HTTP {addresses_response.status}"]
        addresses = addresses_response.json()
        address = next(
            (
                item for item in addresses
                if item.get("ip_address") and item.get("first_seen") and item.get("last_seen")
            ),
            None,
        )
        if address is None:
            return ["la fixture de navegador no tiene una dirección IP con historial temporal"]
        observed_at = datetime.fromisoformat(
            str(address["last_seen"]).replace("Z", "+00:00")
        ).timestamp()
        record = {
            "ts": observed_at,
            "uid": source_event_id.removeprefix("zeek:"),
            "id.orig_h": address["ip_address"],
            "id.orig_p": 51514,
            "id.resp_h": "198.51.100.53",
            "id.resp_p": 53,
            "proto": "udp",
            "orig_bytes": 62,
            "resp_bytes": 141,
            "orig_ip_bytes": 118,
            "resp_ip_bytes": 197,
            "orig_pkts": 2,
            "resp_pkts": 3,
        }
        import json

        jsonl_data = json.dumps(record, separators=(",", ":")) + "\n"
        device_select.select_option(device_id)
        page.locator("#zeekFile").set_input_files({
            "name": "synthetic-conn.jsonl",
            "mimeType": "application/x-ndjson",
            "buffer": jsonl_data.encode("utf-8"),
        })
        page.locator("#previewZeekImport").click()
        page.wait_for_function(
            """() => {
              const panel = document.querySelector('#zeekPreviewPanel');
              const summary = document.querySelector('#zeekPreviewSummary')?.textContent || '';
              return !!panel && !panel.hidden && summary.includes('1 registro(s) válidos');
            }""",
            timeout=7000,
        )
        preview_text = page.locator("#zeekPreviewSummary").inner_text()
        if "1 atribuibles por IP y fecha" not in preview_text:
            failures.append("la vista previa Zeek no informa el registro atribuible al equipo seleccionado")
        if "1 nuevo(s)" not in preview_text:
            failures.append("la vista previa Zeek no distingue el registro nuevo")
        if "no se guardó" not in preview_text.lower():
            failures.append("la vista previa Zeek no aclara que no se guardaron eventos")

        displayed_time = page.locator("#zeekPreviewRows tr td").first.inner_text()
        expected_utc_time = page.evaluate(
            """(timestamp) => new Intl.DateTimeFormat(undefined, {
              dateStyle: "short", timeStyle: "medium", timeZone: "UTC"
            }).format(new Date(timestamp * 1000)) + " UTC" """,
            observed_at,
        )
        if displayed_time != expected_utc_time:
            failures.append(
                "la hora de la vista previa Zeek no coincide con UTC "
                f"(mostrada: {displayed_time}; esperada: {expected_utc_time})"
            )

        before = page.request.get(
            f"{base_url}/api/activity?device_id={device_id}",
            timeout=5000,
        )
        if before.status != 200:
            failures.append("no se pudo comprobar que la vista previa Zeek fuera de solo lectura")
        elif any(item.get("source_event_id") == source_event_id for item in before.json().get("events", [])):
            failures.append("la vista previa Zeek escribió el evento actual antes de confirmar la importación")

        page.locator("#importZeek").click()
        page.wait_for_function(
            """() => (document.querySelector('#zeekImportStatus')?.textContent || '')
              .includes('1 registro(s) importados')""",
            timeout=7000,
        )
        after = page.request.get(
            f"{base_url}/api/activity?device_id={device_id}",
            timeout=5000,
        )
        if after.status != 200:
            failures.append("no se pudo consultar el resultado de la importación Zeek")
        else:
            events = after.json().get("events", [])
            imported = [item for item in events if item.get("source_event_id") == source_event_id]
            if len(imported) != 1:
                failures.append("la importación desde la interfaz no guardó exactamente un evento sintético")
            elif imported[0].get("bytes_sent") != 118 or imported[0].get("bytes_received") != 197:
                failures.append("la interfaz Zeek no conservó los contadores IP del registro sintético")

        metrics = _page_metrics(page)
        if metrics["documentWidth"] > metrics["viewportWidth"] + 1:
            offenders = page.evaluate(
                """() => Array.from(document.querySelectorAll("body *"))
                  .map(element => {
                    const rect = element.getBoundingClientRect();
                    const style = getComputedStyle(element);
                    return {
                      tag: element.tagName.toLowerCase(),
                      id: element.id || "",
                      className: typeof element.className === "string" ? element.className : "",
                      left: Math.round(rect.left),
                      right: Math.round(rect.right),
                      width: Math.round(rect.width),
                      scrollWidth: element.scrollWidth,
                      clientWidth: element.clientWidth,
                      overflowX: style.overflowX,
                      display: style.display
                    };
                  })
                  .filter(item => item.display !== "none" && item.width > 0 &&
                    (item.right > window.innerWidth + 1 || item.width > window.innerWidth + 1))
                  .sort((a, b) => Math.max(b.right, b.width) - Math.max(a.right, a.width))
                  .slice(0, 12)"""
            )
            failures.append(
                f"la pestaña Importar presenta desplazamiento horizontal a {viewport.width} px "
                f"(documento {metrics['documentWidth']} px, ventana {metrics['viewportWidth']} px); "
                f"elementos fuera de ancho: {json.dumps(offenders, ensure_ascii=False)}"
            )

    except Exception as exc:
        failures.append(f"no se pudo completar el recorrido de importación Zeek en Chromium: {exc}")
    return failures


def _monitor_history_accessibility_failures(page) -> list[str]:
    """Prueba el detalle textual de monitorización mediante teclado en Chromium."""
    failures: list[str] = []
    # Los monitores están en una pestaña propia; abrirla reproduce el recorrido real.
    monitor_tab = page.get_by_role("tab", name="Monitores")
    if monitor_tab.count() != 1:
        return ["no se encontró la pestaña Monitores"]
    monitor_tab.click()
    try:
        page.wait_for_function(
            "() => { const p = document.querySelector('#monitor-config'); return !!p && !p.hidden; }",
            timeout=5000,
        )
    except Exception as exc:
        return [f"no se pudo abrir la pestaña Monitores: {exc}"]

    cards = page.locator("#monitor-config .monitor")
    if cards.count() != 1:
        return [f"se esperaba un monitor sintético en la prueba, se encontraron {cards.count()}"]

    card = cards.first
    if "Monitor de prueba accesible" not in card.inner_text():
        return ["no se encontró el monitor sintético esperado"]
    history_button = card.get_by_role("button", name="Historial")
    if history_button.count() != 1:
        return ["no se encontró el botón Historial del monitor sintético"]

    try:
        history_button.click()
        summary = page.locator(".latency-history-details summary")
        summary.wait_for(state="visible", timeout=5000)
        summary.focus()
        summary.press("Enter")
        page.wait_for_function(
            "() => { const d = document.querySelector('.latency-history-details'); return !!d && d.open; }",
            timeout=5000,
        )
    except Exception as exc:
        return [f"no se pudo abrir el detalle textual con teclado: {exc}"]

    entries = page.locator(".latency-history-entries li")
    if entries.count() != 25:
        failures.append(
            f"el detalle debe mostrar 25 intervalos horarios, se encontraron {entries.count()}"
        )
    text_content = entries.all_inner_texts()
    all_text = "\n".join(text_content)
    if not any("Latencia media" in item for item in text_content):
        failures.append("el detalle textual no describe la latencia medida")
    if "Sin latencia válida" not in all_text:
        failures.append("el detalle textual no diferencia el fallo sin latencia")
    if "Sin comprobaciones registradas; disponibilidad desconocida." not in all_text:
        failures.append("el detalle textual no explica los intervalos vacíos")
    return failures


def _forensics_hash_failure_refresh_failures(page) -> list[str]:
    """Comprueba que un fallo de lectura aparezca en la ficha y el historial."""
    failures: list[str] = []
    operator = page.locator("#forensicOperator")
    source_name = page.locator("#forensicEvidenceList .forensic-verify-form input[name='source_name']")
    confirmation = page.locator("#forensicEvidenceList .forensic-verify-form input[name='confirm_working_copy']")
    submit = page.locator("#forensicEvidenceList .forensic-verify-form button[type='submit']")
    if any(locator.count() != 1 for locator in (operator, source_name, confirmation, submit)):
        return ["no se preparó el formulario forense sintético para la prueba de error"]

    try:
        verify_panel = page.locator("#forensicEvidenceList details.forensic-verify-panel")
        if verify_panel.count() != 1:
            return ["no se encontró el panel de comparación de hash sintético"]
        if verify_panel.get_attribute("open") is None:
            verify_panel.locator("summary").click()

        operator.fill("Operador sintético")
        source_name.fill("missing-synthetic-evidence.bin")
        confirmation.check()
        submit.click()
        page.wait_for_function(
            """() => {
              const status = document.querySelector("#forensicWorkspaceStatus");
              const evidence = document.querySelector("#forensicEvidenceList");
              const audit = document.querySelector("#forensicAuditList");
              return status && status.textContent.includes("NS-FORENSIC-INT-002") &&
                evidence && evidence.textContent.includes("Última comprobación: no se pudo leer") &&
                audit && audit.textContent.includes("Falló la comparación del hash");
            }""",
            timeout=8000,
        )
    except Exception as exc:
        return [f"el fallo forense no actualizó el estado y el historial en Chromium: {exc}"]

    if "forensics-working-copies" in page.locator("#forensicAuditList").inner_text():
        return ["el historial forense mostró la ubicación local de las copias de trabajo"]

    # Registra un traspaso sintético desde la UI y confirma que se encadena a la auditoría.
    try:
        transfer_panel = page.locator("#forensicEvidenceList details.forensic-transfer-panel")
        if transfer_panel.count() != 1:
            return ["no se encontró el formulario para registrar transferencia de custodia"]
        if transfer_panel.get_attribute("open") is None:
            transfer_panel.locator("summary").click()
        transfer_panel.locator("input[name='from_custodian']").fill("Examinador sintético UI")
        transfer_panel.locator("input[name='to_custodian']").fill("Custodio sintético UI")
        transfer_panel.locator("input[name='transferred_at_original']").fill("2026-10-22T11:00:00-03:00")
        transfer_panel.locator("textarea[name='purpose']").fill("Entrega sintética para examen de laboratorio.")
        transfer_panel.locator("input[name='delivery_method']").fill("Entrega presencial simulada")
        transfer_panel.locator("textarea[name='condition_notes']").fill("Embalaje sintético íntegro.")
        transfer_panel.locator("input[name='seal_identifier']").fill("SELLO-UI-001")
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/custody-transfers"),
            timeout=10000,
        ) as response_info:
            transfer_panel.locator("button[type='submit']").click()
        transfer_response = response_info.value
        if transfer_response.status != 201:
            failures.append(f"la transferencia desde la interfaz respondió HTTP {transfer_response.status}")
        transfer_payload = transfer_response.json()
        if transfer_payload.get("action") != "evidence_custody_transferred":
            failures.append("la respuesta no identifica el evento de transferencia de custodia")
        if transfer_payload.get("integrity_status") != "valid":
            failures.append("la nueva transferencia no quedó en una cadena de auditoría válida")
        page.wait_for_function(
            """() => {
              const audit = document.querySelector("#forensicAuditList");
              return audit &&
                audit.textContent.includes("Transferencia de custodia registrada") &&
                audit.textContent.includes("Examinador sintético UI") &&
                audit.textContent.includes("Integridad del evento: válida");
            }""",
            timeout=8000,
        )
    except Exception as exc:
        return [f"la transferencia de custodia no funcionó desde Chromium: {exc}"]

    # Crea un informe desde la pantalla y verifica que ambas exportaciones correspondan
    # al mismo borrador íntegro y a la captura del expediente con la custodia sintética.
    try:
        report_details = page.locator("#newForensicReportDetails")
        if report_details.count() != 1:
            return ["falta el formulario para crear el borrador de informe forense"]
        if report_details.get_attribute("open") is None:
            report_details.locator("summary").click()
        page.locator("#forensicReportTitle").fill("Informe de examen desde Chromium")
        page.locator("#forensicReportOrganization").fill("Laboratorio sintético Chromium")
        page.locator("#forensicReportRequestDate").fill("2026-10-22")
        page.locator("#forensicReportRequester").fill("Solicitante sintético Chromium")
        page.locator("#forensicReportRequesterOrganization").fill("Unidad sintética de pruebas")
        page.locator("#forensicReportPurpose").fill("Verificar la generación del informe desde la interfaz.")
        page.locator("#forensicReportScope").fill("Solo metadatos y artefactos sintéticos de Chromium.")
        page.locator("#forensicReportProcesses").fill(
            "Se generó una muestra ficticia, se registró una transferencia y se comprobó el expediente."
        )
        page.locator("#forensicReportResults").fill(
            "La prueba confirmó que el borrador se guarda con un expediente base verificable."
        )
        page.locator("#forensicReportConclusions").fill(
            "No se formula conclusión alguna sobre evidencia real."
        )
        page.locator("#forensicReportConclusionBasis").fill(
            "Respuesta HTTP, digest y campos obtenidos de la prueba automatizada."
        )
        page.locator("#forensicReportLimitations").fill(
            "No se adquirió ni examinó evidencia real; solo se usaron datos sintéticos."
        )
        page.locator("#forensicReportDeviations").fill("Ninguna desviación en esta prueba.")
        page.locator("#forensicReportSupportingMaterial").fill("Informe generado por la prueba Chromium.")
        page.locator("#forensicReportOriginalDisposition").fill(
            "No hay original real; se utilizó un elemento ficticio."
        )
        page.locator("#forensicReportDerivativeDisposition").fill(
            "Los artefactos sintéticos se conservan en el directorio temporal del test."
        )
        page.locator("#forensicReportAuthor").fill("Autor sintético Chromium")
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/reports"),
            timeout=10000,
        ) as report_response_info:
            page.locator("#forensicReportForm button[type='submit']").click()
        report_response = report_response_info.value
        if report_response.status != 201:
            failures.append(f"la creación del informe respondió HTTP {report_response.status}")
            return failures
        saved_report = report_response.json()
        if saved_report.get("version") != 1 or saved_report.get("status") != "draft_unsigned":
            failures.append("el informe no se guardó como primera versión borrador sin firma")
        if not saved_report.get("integrity_valid"):
            failures.append("el informe recién creado no superó la verificación de integridad")
        report_payload = saved_report.get("report", {})
        from netsentinel.forensics_report import verify_examination_report

        if not verify_examination_report(report_payload):
            failures.append("el JSON del informe no superó el verificador local")
        if report_payload.get("integrity", {}).get("source_audit_chain_status") != "valid":
            failures.append("el informe no conserva el estado válido de la cadena base")
        snapshot_events = report_payload.get("source_case_manifest", {}).get("audit_manifest", {}).get("events", [])
        snapshot_transfers = [
            event for event in snapshot_events
            if event.get("action") == "evidence_custody_transferred"
        ]
        if len(snapshot_transfers) != 1:
            failures.append("el informe no incorpora la transferencia sintética en su captura de expediente")
        page.wait_for_function(
            """() => {
              const list = document.querySelector("#forensicReportsList");
              return list && list.textContent.includes("Informe de examen desde Chromium") &&
                list.textContent.includes("Borrador sin firma");
            }""",
            timeout=8000,
        )
        links = page.locator("#forensicReportsList .forensic-report-actions a")
        if links.count() != 2:
            failures.append("la interfaz no muestra las dos exportaciones del informe")
        else:
            with page.expect_download(timeout=8000) as report_json_download_info:
                links.nth(0).click()
            report_json_download = report_json_download_info.value
            if report_json_download.suggested_filename != "netsentinel-examination-report-v001.json":
                failures.append("el informe JSON produjo un nombre de descarga inesperado")
            report_json_path = report_json_download.path()
            if not report_json_path:
                failures.append("Chromium no proporcionó el JSON del informe para verificar")
            else:
                exported_report = json.loads(Path(report_json_path).read_text(encoding="utf-8"))
                if not verify_examination_report(exported_report):
                    failures.append("el informe JSON descargado no superó la verificación local")
                if exported_report.get("report_sha256") != saved_report.get("report_sha256"):
                    failures.append("el digest del informe descargado no coincide con el documento guardado")
                if "forensics-working-copies" in Path(report_json_path).read_text(encoding="utf-8"):
                    failures.append("el JSON del informe expone la ubicación local de las copias")
            with page.expect_download(timeout=8000) as report_md_download_info:
                links.nth(1).click()
            report_md_download = report_md_download_info.value
            if report_md_download.suggested_filename != "netsentinel-examination-report-v001.md":
                failures.append("el informe Markdown produjo un nombre de descarga inesperado")
            report_md_path = report_md_download.path()
            if not report_md_path:
                failures.append("Chromium no proporcionó el Markdown del informe")
            else:
                report_markdown = Path(report_md_path).read_text(encoding="utf-8")
                if "BORRADOR SIN FIRMA" not in report_markdown or "No hay firma digital" not in report_markdown:
                    failures.append("el informe legible no advierte que sigue sin firma")
    except Exception as exc:
        return [f"el informe no se pudo crear y exportar desde Chromium: {exc}"]

    # Comprueba el recorrido real de los dos formatos de exportación del expediente.
    export_button = page.locator("#exportForensicCaseManifest")
    if export_button.count() != 1:
        failures.append("falta el botón para exportar el expediente consolidado")
        return failures
    if export_button.is_disabled():
        failures.append("el botón para exportar el expediente no se habilitó para el caso seleccionado")
        return failures

    try:
        with page.expect_download(timeout=8000) as download_info:
            export_button.click()
        download = download_info.value
        if download.suggested_filename != "netsentinel-forensic-case-manifest.json":
            failures.append("la exportación del expediente produjo un nombre de archivo inesperado")
        download_path = download.path()
        if not download_path:
            failures.append("Chromium no proporcionó una descarga local para verificar")
            return failures
        manifest = json.loads(Path(download_path).read_text(encoding="utf-8"))
        from netsentinel.forensics_case_manifest import verify_case_manifest

        if not verify_case_manifest(manifest):
            failures.append("el expediente descargado no superó la verificación de sus digests")
        if manifest.get("format") != "netsentinel-forensic-case-manifest":
            failures.append("la descarga no contiene el formato de expediente esperado")
        summary = manifest.get("summary", {})
        if summary.get("audit_chain_status") != "valid":
            failures.append("la exportación no conserva una cadena de auditoría sintética válida")
        if summary.get("failed_check_count", 0) < 1:
            failures.append("el expediente no incluye la comprobación sintética fallida")
        if summary.get("report_count") != 1:
            failures.append("el expediente no incluye el índice del borrador de informe guardado")
        report_refs = manifest.get("reports", [])
        if len(report_refs) != 1 or report_refs[0].get("report_sha256") != saved_report.get("report_sha256"):
            failures.append("el expediente no conserva la referencia al digest del informe guardado")
        audit_events = manifest.get("audit_manifest", {}).get("events", [])
        transfer_events = [event for event in audit_events if event.get("action") == "evidence_custody_transferred"]
        if len(transfer_events) != 1:
            failures.append("el expediente no incluye exactamente el traspaso sintético recién registrado")
        elif transfer_events[0].get("details", {}).get("to_custodian") != "Custodio sintético UI":
            failures.append("el expediente no conserva a la persona que recibe el traspaso")
        exported_text = Path(download_path).read_text(encoding="utf-8")
        if "forensics-working-copies" in exported_text:
            failures.append("el expediente descargado revela la carpeta de copias de trabajo")


        audit_button = page.locator("#exportForensicAuditManifest")
        try:
            with page.expect_download(timeout=8000) as audit_download_info:
                audit_button.click()
            audit_download = audit_download_info.value
            if audit_download.suggested_filename != "netsentinel-forensic-audit-manifest.json":
                failures.append("la exportación de auditoría produjo un nombre de archivo inesperado")
            audit_path = audit_download.path()
            if not audit_path:
                failures.append("Chromium no proporcionó la descarga de auditoría para verificar")
            else:
                audit_manifest = json.loads(Path(audit_path).read_text(encoding="utf-8"))
                from netsentinel.forensics_audit_manifest import verify_audit_manifest

                if not verify_audit_manifest(audit_manifest):
                    failures.append("el manifiesto de auditoría descargado no superó la verificación de integridad")
                if audit_manifest.get("format") != "netsentinel-forensic-audit-manifest":
                    failures.append("la descarga de auditoría no contiene el formato esperado")
                integrity = audit_manifest.get("integrity", {})
                if integrity.get("status") != "valid":
                    failures.append("la auditoría exportada no informa una cadena íntegra para el caso sintético")
                exported_transfers = [
                    event for event in audit_manifest.get("events", [])
                    if event.get("action") == "evidence_custody_transferred"
                ]
                if len(exported_transfers) != 1:
                    failures.append("el manifiesto de auditoría no contiene el traspaso sintético")
                if not any(
                    event.get("action") == "report_draft_created"
                    for event in audit_manifest.get("events", [])
                ):
                    failures.append("el manifiesto de auditoría no contiene la creación del informe")
                audit_text = Path(audit_path).read_text(encoding="utf-8")
                if "forensics-working-copies" in audit_text:
                    failures.append("el manifiesto de auditoría revela la carpeta de copias de trabajo")
        except Exception as exc:
            failures.append(f"no se pudo descargar y verificar la auditoría forense en Chromium: {exc}")
    except Exception as exc:
        failures.append(f"no se pudo descargar y verificar el expediente consolidado en Chromium: {exc}")

    # Verifica desde la pantalla que se puedan crear un caso y una ficha de
    # evidencia, no solo leer los registros que preparó el fixture automático.
    try:
        case_details = page.locator("#newForensicCaseDetails")
        case_details.locator("summary").click()
        page.locator("#forensicOperator").fill("Operador sintético Chromium")
        page.locator("#forensicCaseNumber").fill("UI-FORENSICS-CREATE-002")
        page.locator("#forensicCaseTitle").fill("Alta sintética desde la interfaz")
        page.locator("#forensicAuthority").fill("AUTORIZACION-SINTETICA-002")
        page.locator("#forensicObjective").fill("Verificar el alta de caso desde Chromium.")
        page.locator("#forensicScope").fill("Solo registros sintéticos; ninguna evidencia real.")
        page.locator("#forensicExaminer").fill("Examinador sintético Chromium")

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.rstrip("/").endswith("/api/forensics/cases"),
            timeout=10000,
        ) as response_info:
            page.locator("#forensicCaseForm button[type='submit']").click()
        created_case_response = response_info.value
        if created_case_response.status != 201:
            failures.append(f"el alta de caso desde la interfaz respondió HTTP {created_case_response.status}")

        page.wait_for_function(
            """() => (document.querySelector("#forensicSelectedCaseNumber")?.textContent || "")
              .includes("UI-FORENSICS-CREATE-002")""",
            timeout=10000,
        )
        page.locator("#newForensicEvidenceDetails summary").click()
        page.locator("#forensicEvidenceLabel").fill("Muestra creada en Chromium")
        page.locator("#forensicEvidenceType").select_option("file_copy")
        page.locator("#forensicOriginalName").fill("netsentinel-ui-sample.bin")
        page.locator("#forensicSourceDescription").fill(
            "Metadatos ficticios para comprobar el formulario; no hay contenido real adjunto."
        )
        page.locator("#forensicReceivedFrom").fill("Fixture automática de Chromium")
        page.locator("#forensicReceivedBy").fill("Examinador sintético Chromium")
        page.locator("#forensicReportedHash").fill("a" * 64)
        page.locator("#forensicHashSource").fill("Hash fijo sintético de la prueba UI")

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and "/api/forensics/cases/" in response.url
            and response.url.endswith("/evidence"),
            timeout=10000,
        ) as response_info:
            page.locator("#forensicEvidenceForm button[type='submit']").click()
        created_evidence_response = response_info.value
        if created_evidence_response.status != 201:
            failures.append(f"el registro de evidencia desde la interfaz respondió HTTP {created_evidence_response.status}")
        page.wait_for_function(
            """() => (document.querySelector("#forensicEvidenceList")?.textContent || "")
              .includes("Muestra creada en Chromium") &&
              (document.querySelector("#forensicWorkspaceStatus")?.textContent || "")
                .includes("quedó registrada")""",
            timeout=10000,
        )
    except Exception as exc:
        failures.append(f"no se completó el alta de caso y evidencia desde Chromium: {exc}")
    return failures


def _activity_synthetic_import_failures(page, base_url: str, scenarios_dir: Path) -> list[str]:
    """Prueba el recorrido CSV visible con archivos sintéticos y una base temporal propia."""
    failures: list[str] = []
    required_files = (
        "activity.csv",
        "activity-invalid-sensitive.csv",
        "activity-invalid-duplicate-header.csv",
    )
    missing = [name for name in required_files if not (scenarios_dir / name).is_file()]
    if missing:
        return [f"faltan los escenarios CSV sintéticos: {', '.join(missing)}"]

    try:
        import_tab = page.locator('button.section-tab[data-tab-target="activity-import"]')
        if import_tab.count() != 1:
            return ["no se encontró la pestaña Importar de Actividad"]
        import_tab.click()
        page.wait_for_function(
            """() => {
              const device = document.querySelector("#csvDevice");
              return device && device.options.length > 1;
            }""",
            timeout=8000,
        )
        page.locator("#csvDevice").select_option(index=1)
        page.locator("#csvFile").set_input_files(str(scenarios_dir / "activity.csv"))

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/activity/import/preview"),
            timeout=10000,
        ) as response_info:
            page.locator("#previewImport").click()
        preview_response = response_info.value
        if preview_response.status != 200:
            failures.append(f"la vista previa CSV válida respondió HTTP {preview_response.status}")
        page.wait_for_function(
            """() => {
              const panel = document.querySelector("#previewPanel");
              const summary = document.querySelector("#previewSummary");
              return panel && !panel.hidden && summary &&
                summary.textContent.includes("6 fila(s) válidas");
            }""",
            timeout=8000,
        )
        summary = page.locator("#previewSummary").inner_text()
        if "6 nueva(s)" not in summary:
            failures.append(f"la vista previa no identificó seis filas nuevas: {summary}")
        if "No se guardaron eventos" not in page.locator("#importStatus").inner_text():
            failures.append("la vista previa no confirmó que todavía no se guardaron eventos")

        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/activity/import"),
            timeout=10000,
        ) as response_info:
            page.locator("#import").click()
        import_response = response_info.value
        if import_response.status != 200:
            failures.append(f"la importación CSV válida respondió HTTP {import_response.status}")
        page.wait_for_function(
            """() => (document.querySelector("#importStatus")?.textContent || "")
              .includes("6 evento(s) importados")""",
            timeout=10000,
        )

        # Repetir el archivo debe detectar duplicados, no insertar otra copia.
        with page.expect_response(
            lambda response: response.request.method == "POST"
            and response.url.endswith("/api/activity/import/preview"),
            timeout=10000,
        ) as response_info:
            page.locator("#previewImport").click()
        duplicate_response = response_info.value
        if duplicate_response.status != 200:
            failures.append(f"la vista previa repetida respondió HTTP {duplicate_response.status}")
        page.wait_for_function(
            """() => {
              const summary = document.querySelector("#previewSummary");
              return summary && summary.textContent.includes("6 duplicada(s)");
            }""",
            timeout=8000,
        )
        duplicate_summary = page.locator("#previewSummary").inner_text()
        if "0 nueva(s)" not in duplicate_summary:
            failures.append(f"la repetición de CSV no quedó completamente deduplicada: {duplicate_summary}")

        for filename in ("activity-invalid-sensitive.csv", "activity-invalid-duplicate-header.csv"):
            page.locator("#importStatus").evaluate("(element) => { element.textContent = ''; }")
            page.locator("#csvFile").set_input_files(str(scenarios_dir / filename))
            with page.expect_response(
                lambda response: response.request.method == "POST"
                and response.url.endswith("/api/activity/import/preview"),
                timeout=10000,
            ) as response_info:
                page.locator("#previewImport").click()
            response = response_info.value
            if not 400 <= response.status < 500:
                failures.append(f"{filename} no fue rechazado por la API (HTTP {response.status})")
            page.wait_for_function(
                """() => (document.querySelector("#importStatus")?.textContent || "").trim().length > 0""",
                timeout=8000,
            )
            if not page.locator("#previewPanel").is_hidden():
                failures.append(f"{filename} dejó visible una vista previa como si fuera válida")
            error_text = page.locator("#importStatus").inner_text()
            if "Vista previa completada. No se guardaron eventos." in error_text:
                failures.append(f"{filename} mostró un mensaje de éxito en lugar de rechazo")
    except Exception as exc:
        failures.append(f"el recorrido CSV sintético no se completó en Chromium: {exc}")
    finally:
        # No dejamos la vista en un panel de error ni reutilizamos el archivo inválido.
        try:
            page.goto(f"{base_url}/activity", wait_until="load", timeout=10000)
        except Exception:
            pass
    return failures


def _world_map_render_failures(page, base_url: str) -> list[str]:
    """Comprueba el mapa local, una IP sintética importada y el filtro de destinos."""
    failures: list[str] = []
    try:
        page.wait_for_function(
            """() => {
              const map = document.querySelector("#worldMap");
              const body = document.querySelector("#geoDestinationsBody");
              const status = document.querySelector("#geoMapStatus");
              return map && map.querySelectorAll(".geo-country").length > 0 &&
                body && Array.from(body.querySelectorAll("tr")).some((row) =>
                  row.textContent.includes("1.1.1.1")) &&
                status && status.textContent.includes("evento(s) con IP destino");
            }""",
            timeout=10000,
        )

        response = page.request.get(f"{base_url}/api/geolocation/map?limit=250")
        if response.status != 200:
            return [f"la API del mapa respondió HTTP {response.status}"]
        payload = response.json()
        summary = payload.get("summary", {})
        databases = payload.get("databases", {})
        if int(summary.get("events_with_destination_ip", 0)) < 1:
            failures.append("la API del mapa no reconoció eventos con IP destino después de importar el CSV sintético")

        # Si no hay una base City válida, la interfaz debe conservar la tabla y el
        # mapa base pero no dibujar ubicaciones fabricadas.
        if databases.get("city_status") != "available":
            markers = page.locator("#worldMap .geo-observed-marker-layer .geo-marker").count()
            if markers:
                failures.append("el mapa dibujó marcadores observados sin una base GeoIP disponible")

        target_row = page.locator("#geoDestinationsBody tr").filter(has_text="1.1.1.1").first
        if target_row.count() != 1:
            failures.append("la tabla del mapa no muestra la IP sintética pública 1.1.1.1")
        else:
            target_row.locator("button.geo-select-ip").click()
            page.wait_for_function(
                """() => document.querySelector("#geoSelectedTitle")?.textContent === "1.1.1.1" """,
                timeout=5000,
            )
            page.locator("#geoDestinationFilter").fill("no-such-synthetic-destination")
            page.wait_for_function(
                """() => (document.querySelector("#geoDestinationsBody")?.textContent || "")
                  .includes("No hay destinos que coincidan con el filtro.")""",
                timeout=5000,
            )
            page.locator("#geoDestinationFilter").fill("")
            page.wait_for_function(
                """() => Array.from(document.querySelectorAll("#geoDestinationsBody tr"))
                  .some((row) => row.textContent.includes("1.1.1.1"))""",
                timeout=5000,
            )
    except Exception as exc:
        failures.append(f"el mapa mundial no completó la comprobación con el CSV sintético: {exc}")
    finally:
        try:
            page.goto(f"{base_url}/world-map", wait_until="load", timeout=10000)
        except Exception:
            pass
    return failures


def _guided_test_interaction_failures(page, base_url: str, scenarios_dir: Path | None = None) -> list[str]:
    """Valida el asistente secuencial, sus resultados, la persistencia y la ausencia de escaneos."""
    failures: list[str] = []
    scan_posts: list[str] = []
    popups = []

    def track_request(request) -> None:
        if request.method == "POST" and request.url.split("?", 1)[0].rstrip("/").endswith("/api/scan"):
            scan_posts.append(request.url)

    def track_popup(popup) -> None:
        popups.append(popup)
        popup.on("request", track_request)

    page.on("request", track_request)
    page.on("popup", track_popup)
    try:
        page.goto(f"{base_url}/guided-test", wait_until="load")
        if page.locator("#wizardStepTitle").inner_text() != "Vamos a validar NetSentinel juntos":
            return ["la guía no muestra la pantalla inicial del asistente"]
        if page.locator("[data-guided-step]").count():
            failures.append("la nueva guía conserva la lista antigua de casillas dispersas")
        if "no llama a" not in page.locator(".wizard-safety").inner_text().lower():
            failures.append("la guía no explica que sus comprobaciones no inician escaneos")

        page.locator("#wizardStart").focus()
        page.keyboard.press("Enter")
        if "Comprobar que el laboratorio está preparado" not in page.locator("#wizardStepTitle").inner_text():
            failures.append("el botón Empezar no condujo al primer paso")
            return failures
        if page.evaluate("document.activeElement && document.activeElement.id") != "wizardStepTitle":
            failures.append("el foco no anunció el título del paso nuevo después de empezar")

        # Simulamos un fallo ya registrado para comprobar el estado de recuperación
        # sin interceptar la petición real de salud que usará el paso siguiente.
        page.evaluate(
            """() => localStorage.setItem("netsentinel.acceptance-wizard.v3", JSON.stringify({
              currentStep: 1,
              records: {
                lab: {
                  outcome: "failed",
                  note: "",
                  opened: false,
                  autoChecked: true,
                  autoResult: {
                    ok: false,
                    summary: "Fallo temporal sintético",
                    details: [{label: "API de salud", value: "HTTP 503 simulado", ok: false}],
                    checkedAt: new Date().toISOString()
                  }
                }
              },
              finishedAt: null
            }))"""
        )
        page.reload(wait_until="load")
        if "Comprobar que el laboratorio está preparado" not in page.locator("#wizardStepTitle").inner_text():
            failures.append("el estado de recuperación no volvió al paso de preparación")
            return failures
        if not page.locator("#wizardNext").is_disabled():
            failures.append("la guía permitió avanzar con un prerrequisito marcado como fallido")
        if not page.locator("#wizardRecoveryDetails").evaluate("(element) => element.open"):
            failures.append("la guía no abrió la ayuda de recuperación para un prerrequisito fallido")
        if page.locator("#wizardRunCheck").inner_text() != "Comprobar de nuevo":
            failures.append("la guía no ofrece repetir la comprobación después del fallo")
        page.evaluate("window.localStorage.removeItem('netsentinel.acceptance-wizard.v3')")
        page.reload(wait_until="load")
        if page.locator("#wizardStepTitle").inner_text() != "Vamos a validar NetSentinel juntos":
            failures.append("la guía no recuperó el inicio limpio después de reiniciar el estado sintético")

        page.locator("#wizardStart").focus()
        page.keyboard.press("Enter")
        if "Comprobar que el laboratorio está preparado" not in page.locator("#wizardStepTitle").inner_text():
            failures.append("el botón Empezar no condujo al primer paso")
            return failures
        if page.evaluate("document.activeElement && document.activeElement.id") != "wizardStepTitle":
            failures.append("el foco no anunció el título del paso nuevo después de empezar")

        page.locator("#wizardRunCheck").click()
        page.wait_for_function(
            """() => {
              const panel = document.querySelector("#wizardAutomaticPanel");
              const badge = document.querySelector("#wizardAutomaticBadge");
              const rows = document.querySelectorAll("#wizardAutomaticDetails .wizard-check-result");
              return panel && !panel.hidden && badge && badge.textContent && rows.length >= 3;
            }""",
            timeout=8000,
        )
        if "Comprobación correcta" not in page.locator("#wizardAutomaticBadge").inner_text():
            failures.append(
                "la comprobación inicial del asistente no confirmó la fixture: "
                + page.locator("#wizardAutomaticSummary").inner_text()
            )
            return failures
        if page.locator("#wizardNext").is_disabled():
            failures.append("el primer paso correcto no habilitó Siguiente")
            return failures

        page.locator("#wizardNext").click()
        if "topología guardada" not in page.locator("#wizardStepTitle").inner_text().lower():
            failures.append("el asistente no avanzó a la comprobación de topología")
            return failures
        if page.evaluate("document.activeElement && document.activeElement.id") != "wizardStepTitle":
            failures.append("el foco no se trasladó al título tras avanzar al paso de topología")

        page.locator("#wizardRunCheck").click()
        page.wait_for_function(
            """() => {
              const panel = document.querySelector("#wizardAutomaticPanel");
              const badge = document.querySelector("#wizardAutomaticBadge");
              return panel && !panel.hidden && badge && badge.textContent.trim().length > 0;
            }""",
            timeout=8000,
        )
        if "Comprobación correcta" not in page.locator("#wizardAutomaticBadge").inner_text():
            failures.append(
                "la comprobación automática de topología no confirmó la fixture: "
                + page.locator("#wizardAutomaticSummary").inner_text()
            )
            return failures

        def _select_synthetic_device(target_page, selector: str) -> str:
            target_page.wait_for_function(
                """selector => {
                  const control = document.querySelector(selector);
                  return control && Array.from(control.options).some(option => option.value);
                }""",
                arg=selector,
                timeout=8000,
            )
            select = target_page.locator(selector)
            options = select.locator("option").evaluate_all(
                "(items) => items.filter(item => item.value).map(item => ({value:item.value,text:item.textContent || ''}))"
            )
            selected = next(
                (item for item in options if "192.168.56.20" in item["text"] or "Dispositivo sintético de prueba" in item["text"]),
                options[0] if options else None,
            )
            if selected is None:
                raise AssertionError(f"el selector {selector} no recibió dispositivos")
            select.select_option(selected["value"])
            return selected["value"]

        def _clear_status(target_page, selector: str) -> None:
            target_page.locator(selector).evaluate("(element) => { element.textContent = ''; }")

        def _exercise_activity_scenario(target_page, step_title: str) -> None:
            if scenarios_dir is None:
                return
            tab = target_page.get_by_role("tab", name="Importar")
            if tab.count() != 1:
                failures.append(f"el módulo Actividad no mostró la pestaña Importar para «{step_title}»")
                return
            tab.click()

            if "CSV: revisar antes de importar" in step_title or "CSV: importar una vez" in step_title:
                _select_synthetic_device(target_page, "#csvDevice")
                target_page.locator("#csvFile").set_input_files(str(scenarios_dir / "activity.csv"))
                _clear_status(target_page, "#importStatus")
                target_page.locator("#previewImport").click()
                target_page.wait_for_function(
                    """() => {
                      const panel = document.querySelector("#previewPanel");
                      const summary = document.querySelector("#previewSummary");
                      return panel && !panel.hidden && summary && summary.textContent.includes("6 fila(s) válidas");
                    }""",
                    timeout=8000,
                )
                if "CSV: importar una vez" in step_title:
                    _clear_status(target_page, "#importStatus")
                    target_page.locator("#import").click()
                    target_page.wait_for_function(
                        """() => (document.querySelector("#importStatus")?.textContent || "").includes("evento(s) importados")""",
                        timeout=8000,
                    )
                    first_status = target_page.locator("#importStatus").inner_text()
                    if "evento(s) importados" not in first_status or "duplicado(s) omitidos" not in first_status:
                        failures.append("la primera importación CSV no informó claramente importados y duplicados")

                    # Volver a previsualizar debe mostrar los seis registros como duplicados.
                    _clear_status(target_page, "#importStatus")
                    target_page.locator("#previewImport").click()
                    target_page.wait_for_function(
                        """() => {
                          const panel = document.querySelector("#previewPanel");
                          const summary = document.querySelector("#previewSummary")?.textContent || "";
                          return panel && !panel.hidden && summary.includes("6 fila(s) válidas") &&
                            summary.includes("0 nueva(s)") && summary.includes("6 duplicada(s)");
                        }""",
                        timeout=8000,
                    )
                    # La segunda importación demuestra que los duplicados no se guardan de nuevo.
                    _clear_status(target_page, "#importStatus")
                    target_page.locator("#import").click()
                    target_page.wait_for_function(
                        """() => (document.querySelector("#importStatus")?.textContent || "").includes("duplicado(s) omitidos")""",
                        timeout=8000,
                    )
                    second_status = target_page.locator("#importStatus").inner_text()
                    if "0 evento(s) importados" not in second_status or "6 duplicado(s) omitidos" not in second_status:
                        failures.append("la segunda importación CSV no informó 0 nuevos y 6 duplicados omitidos")
                return

            if "CSV: rechazar archivos inválidos" in step_title:
                _select_synthetic_device(target_page, "#csvDevice")
                for filename in ("activity-invalid-sensitive.csv", "activity-invalid-duplicate-header.csv"):
                    target_page.locator("#csvFile").set_input_files(str(scenarios_dir / filename))
                    _clear_status(target_page, "#importStatus")
                    target_page.locator("#previewImport").click()
                    target_page.wait_for_function(
                        """() => (document.querySelector("#importStatus")?.textContent || "").trim().length > 0""",
                        timeout=8000,
                    )
                    if not target_page.locator("#previewPanel").is_hidden():
                        failures.append(f"{filename} dejó una vista previa visible como si fuera válido durante el asistente")
                return

            if "Zeek:" in step_title:
                _select_synthetic_device(target_page, "#zeekDevice")
                target_page.locator("#zeekFile").set_input_files(str(scenarios_dir / "zeek-conn.tsv"))
                _clear_status(target_page, "#zeekImportStatus")
                target_page.locator("#previewZeekImport").click()
                target_page.wait_for_function(
                    """() => {
                      const panel = document.querySelector("#zeekPreviewPanel");
                      const summary = document.querySelector("#zeekPreviewSummary");
                      return panel && !panel.hidden && summary && summary.textContent.trim().length > 0;
                    }""",
                    timeout=8000,
                )
                _clear_status(target_page, "#zeekImportStatus")
                target_page.locator("#importZeek").click()
                target_page.wait_for_function(
                    """() => (document.querySelector("#zeekImportStatus")?.textContent || "").includes("registro(s) importados")""",
                    timeout=8000,
                )
                first_status = target_page.locator("#zeekImportStatus").inner_text()
                if "registro(s) importados" not in first_status or "duplicado(s)" not in first_status:
                    failures.append("la primera importación Zeek no informó claramente importados y duplicados")

                # Repetir primero la vista previa y después la importación prueba idempotencia por UID.
                _clear_status(target_page, "#zeekImportStatus")
                target_page.locator("#previewZeekImport").click()
                target_page.wait_for_function(
                    """() => {
                      const panel = document.querySelector("#zeekPreviewPanel");
                      const summary = document.querySelector("#zeekPreviewSummary")?.textContent || "";
                      return panel && !panel.hidden && summary.includes("0 nuevo(s)") && summary.includes("2 duplicado(s)");
                    }""",
                    timeout=8000,
                )
                _clear_status(target_page, "#zeekImportStatus")
                target_page.locator("#importZeek").click()
                target_page.wait_for_function(
                    """() => (document.querySelector("#zeekImportStatus")?.textContent || "").includes("duplicado(s)")""",
                    timeout=8000,
                )
                second_status = target_page.locator("#zeekImportStatus").inner_text()
                if "0 registro(s) importados" not in second_status or "2 duplicado(s)" not in second_status:
                    failures.append("la segunda importación Zeek no informó 0 nuevos y 2 UID duplicados")
                return

        def open_module_and_record(outcome: str = "passed") -> str:
            title = page.locator("#wizardStepTitle").inner_text()
            link = page.locator("#wizardActionLink")
            if link.count() != 1 or not link.is_visible():
                failures.append(f"el paso «{title}» no muestra el enlace a su módulo")
                return title
            with page.expect_popup(timeout=8000) as popup_info:
                link.click()
            popup = popup_info.value
            popup.wait_for_load_state("load", timeout=10000)
            expected_path = link.get_attribute("href")
            if expected_path and not popup.url.endswith(expected_path):
                failures.append(f"el paso «{title}» abrió una dirección inesperada: {popup.url}")
            if expected_path == "/activity":
                try:
                    _exercise_activity_scenario(popup, title)
                except Exception as exc:
                    failures.append(f"no se pudo completar la acción requerida en «{title}»: {exc}")
            popup.close()
            if "topología guardada" not in title.lower():
                if page.locator("#wizardRunCheck").is_visible():
                    page.locator("#wizardRunCheck").click()
                    page.wait_for_function(
                        """() => {
                          const panel = document.querySelector("#wizardAutomaticPanel");
                          const badge = document.querySelector("#wizardAutomaticBadge");
                          return panel && !panel.hidden && badge && badge.textContent;
                        }""",
                        timeout=8000,
                    )
            if page.locator("#wizardManualResultPanel").is_hidden():
                failures.append(f"el paso «{title}» no mostró las opciones de resultado al volver de la pestaña")
                return title
            button = page.locator(f'[data-wizard-outcome="{outcome}"]')
            if button.is_disabled():
                failures.append(f"el resultado {outcome!r} quedó deshabilitado en el paso «{title}»")
                return title
            button.click()
            if page.locator("#wizardNext").is_disabled():
                failures.append(f"registrar el resultado no habilitó Siguiente en «{title}»")
            return title

        # La API y la vista del grafo se comprueban sin iniciar descubrimiento.
        title = open_module_and_record("passed")
        if "topología guardada" not in title.lower():
            failures.append("se perdió el contexto del paso de topología")

        for index in range(10):
            if page.locator("#wizardNext").is_hidden():
                failures.append("el asistente ocultó Siguiente antes de completar todos los pasos")
                break
            page.locator("#wizardNext").click()
            title = page.locator("#wizardStepTitle").inner_text()
            outcome = "passed"
            if "rutas inseguras" in title.lower():
                outcome = "failed"
            elif "generar y verificar el informe" in title.lower():
                outcome = "blocked"
            if not page.locator("#wizardActionLink").is_visible():
                failures.append(f"el paso «{title}» no indica qué módulo abrir")
                break
            # CSV/Zeek posteriores a una acción deshabilitan esta comprobación hasta
            # que el usuario abre el módulo y termina la importación indicada.
            check_button = page.locator("#wizardRunCheck")
            if check_button.is_visible() and check_button.is_enabled():
                check_button.click()
                page.wait_for_function(
                    """() => {
                      const panel = document.querySelector("#wizardAutomaticPanel");
                      const badge = document.querySelector("#wizardAutomaticBadge");
                      return panel && !panel.hidden && badge && badge.textContent;
                    }""",
                    timeout=8000,
                )
            open_module_and_record(outcome)
            if page.locator("#wizardNext").is_disabled():
                break

        if page.locator("#wizardNext").is_visible() and not page.locator("#wizardNext").is_disabled():
            page.locator("#wizardNext").click()

        if page.locator("#wizardSummaryPanel").is_hidden():
            failures.append("no apareció el panel de resumen al finalizar el recorrido")
        else:
            if page.locator(".wizard-summary-row").count() != 12:
                failures.append(
                    f"el informe mostró {page.locator('.wizard-summary-row').count()} resultados en vez de 12"
                )
            summary = page.locator("#wizardCompletionMessage").inner_text()
            if "fallo" not in summary.lower() or "sin comprobar" not in summary.lower():
                failures.append("el resumen no distinguió fallos de pasos no comprobados")
            if page.locator("#wizardCopyReport").is_hidden() or page.locator("#wizardDownloadReport").is_hidden():
                failures.append("el cierre no ofrece copiar o descargar el informe")

        page.reload(wait_until="load")
        if page.locator("#wizardSummaryPanel").is_hidden():
            failures.append("el asistente no conservó el cierre y el resumen al recargar")
        if "Recorrido finalizado" not in page.locator("#wizardStepTitle").inner_text():
            failures.append("el título de cierre no quedó visible tras recargar")

        if scan_posts:
            failures.append(
                "el asistente de pruebas envió POST /api/scan, pero este flujo debe ser estrictamente de solo lectura: "
                + ", ".join(scan_posts)
            )

        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("#wizardRestart").click()
        if page.locator("#wizardStepTitle").inner_text() != "Vamos a validar NetSentinel juntos":
            failures.append("Reiniciar el recorrido no volvió a la introducción")
        if page.locator("#wizardProgressCount").inner_text() != "0%":
            failures.append("reiniciar no limpió el progreso del asistente")
    except Exception as exc:
        failures.append(f"la interacción del asistente de pruebas falló en Chromium: {exc}")
    finally:
        try:
            for popup in popups:
                if not popup.is_closed():
                    popup.close()
            page.goto(f"{base_url}/guided-test", wait_until="load", timeout=10000)
            page.evaluate("window.localStorage.removeItem('netsentinel.acceptance-wizard.v3')")
            page.reload(wait_until="load")
        except Exception:
            pass
    return failures


def _run_browser_checks(base_url: str, viewports: tuple[Viewport, ...], output_dir: Path, screenshots: bool, scenarios_dir: Path | None = None) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Falta Playwright. Instalá la opción de prueba con "
            'python -m pip install -e ".[test,ui-test]" y ejecutá '
            "python -m playwright install chromium."
        ) from exc

    report = {
        "base_url": base_url,
        "viewport_count": len(viewports),
        "page_count": len(PAGE_CASES),
        "cases": [],
        "failures": [],
        "screenshots": [],
    }
    active_case = {"path": "", "viewport": ""}
    page_errors: list[dict[str, str]] = []

    if screenshots:
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(device_scale_factor=1)
                page.on(
                    "pageerror",
                    lambda error: page_errors.append({
                        "path": active_case["path"],
                        "viewport": active_case["viewport"],
                        "message": str(error),
                    }),
                )

                for viewport in viewports:
                    for path, expected_title, page_name in PAGE_CASES:
                        active_case["path"] = path
                        active_case["viewport"] = viewport.label
                        error_start = len(page_errors)
                        case_failures: list[str] = []

                        try:
                            page.set_viewport_size({
                                "width": viewport.width,
                                "height": viewport.height,
                            })
                            response = page.goto(
                                f"{base_url}{path}",
                                wait_until="load",
                                timeout=20000,
                            )
                            if response is None:
                                case_failures.append("el navegador no recibió una respuesta HTTP")
                            elif response.status != 200:
                                case_failures.append(f"la página respondió HTTP {response.status}")

                            page.wait_for_selector("main.wrap", timeout=5000)
                            page.evaluate(
                                "() => document.fonts ? document.fonts.ready.then(() => true) : true"
                            )

                            headings = page.locator("h1.app-section-title")
                            if headings.count() != 1:
                                case_failures.append("no se encontró un único título de sección")
                            elif not headings.first.is_visible():
                                case_failures.append("el título de la sección no está visible")
                            elif headings.first.inner_text().strip() != expected_title:
                                actual = headings.first.inner_text().strip()
                                case_failures.append(
                                    f"título inesperado: {actual!r}; se esperaba {expected_title!r}"
                                )

                            if path == "/forensics":
                                current_links = page.locator(
                                    '.product-switcher a.product-link[aria-current="true"]'
                                )
                            else:
                                current_links = page.locator(
                                    '.primary-nav a.nav-link[aria-current="page"]'
                                )
                            if current_links.count() != 1:
                                case_failures.append(
                                    "la navegación no identifica exactamente un módulo activo"
                                )

                            theme_options = page.locator('input[name="themeSelect"]')
                            if theme_options.count() != 3:
                                case_failures.append("no aparecen los tres temas visuales")

                            metrics = _page_metrics(page)
                            if metrics["documentWidth"] > metrics["viewportWidth"] + 1:
                                case_failures.append(
                                    "hay desplazamiento horizontal en toda la página "
                                    f"(documento {metrics['documentWidth']} px, "
                                    f"ventana {metrics['viewportWidth']} px)"
                                )

                            if path == "/":
                                case_failures.extend(_inventory_layout_failures(page, viewport))
                            if path in {"/", "/network"} and viewport == Viewport(1440, 900):
                                case_failures.extend(_scan_comparison_failures(page))
                            if path == "/network":
                                case_failures.extend(_topology_panel_failures(
                                    page,
                                    check_missing_evidence=(viewport == Viewport(1440, 900)),
                                ))
                            if path == "/monitors" and viewport == Viewport(1440, 900):
                                case_failures.extend(_monitor_history_accessibility_failures(page))
                            if path == "/activity" and viewport in {
                                Viewport(390, 844),
                                Viewport(1440, 900),
                            }:
                                case_failures.extend(_zeek_import_ui_failures(page, base_url, viewport))
                            if path == "/forensics" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(_forensics_hash_failure_refresh_failures(page))
                            if path == "/activity" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(
                                    _activity_synthetic_import_failures(page, base_url, scenarios_dir)
                                )
                            if path == "/guided-test" and viewport == Viewport(1440, 900):
                                case_failures.extend(
                                    _guided_test_interaction_failures(page, base_url, scenarios_dir)
                                )
                            if path == "/world-map" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(_world_map_render_failures(page, base_url))
                            if path == "/world-map" and viewport == Viewport(1440, 900) and scenarios_dir is None:
                                case_failures.extend(_world_map_empty_state_failures(page))

                            for script_error in page_errors[error_start:]:
                                case_failures.append(
                                    f"error JavaScript: {script_error['message']}"
                                )

                            should_capture = screenshots and (
                                path in {"/", "/network"} or viewport == Viewport(1440, 900)
                            )
                            if should_capture:
                                capture_path = output_dir / (
                                    f"{page_name}-{viewport.label}.png"
                                )
                                page.screenshot(path=str(capture_path), full_page=True)
                                report["screenshots"].append(str(capture_path))

                            case = {
                                "path": path,
                                "page": page_name,
                                "viewport": asdict(viewport),
                                "metrics": metrics,
                                "passed": not case_failures,
                                "failures": case_failures,
                            }
                        except Exception as exc:
                            case = {
                                "path": path,
                                "page": page_name,
                                "viewport": asdict(viewport),
                                "passed": False,
                                "failures": [f"no se pudo completar la comprobación: {exc}"],
                            }

                        report["cases"].append(case)
                        for problem in case["failures"]:
                            report["failures"].append({
                                "path": path,
                                "viewport": viewport.label,
                                "message": problem,
                            })
                        state = "OK" if case["passed"] else "FALLO"
                        print(f"[{state}] {viewport.label:>9}  {path}")
                        for problem in case["failures"]:
                            print(f"         - {problem}")
            finally:
                browser.close()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            "No pude iniciar Chromium. Instalá el navegador con "
            "python -m playwright install chromium. "
            f"Detalle: {exc}"
        ) from exc

    report["passed_cases"] = sum(1 for case in report["cases"] if case["passed"])
    report["failed_cases"] = sum(1 for case in report["cases"] if not case["passed"])
    report["passed"] = not report["failures"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Revisa las secciones de NetSentinel en múltiples tamaños. "
            "Por defecto usa un servidor y una base de datos temporales."
        )
    )
    parser.add_argument(
        "--viewports",
        type=parse_viewports,
        default=DEFAULT_VIEWPORTS,
        metavar="LISTA",
        help=f"Tamaños separados por comas (por defecto: {DEFAULT_VIEWPORTS_TEXT}).",
    )
    parser.add_argument(
        "--base-url",
        help="Prueba un servidor local que ya esté iniciado, por ejemplo http://127.0.0.1:8765.",
    )
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Guarda capturas del Inventario en todos los tamaños y de las otras secciones a 1440x900.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / ".netsentinel-test-artifacts" / "responsive-ui",
        help="Carpeta para el informe JSON y las capturas opcionales.",
    )
    args = parser.parse_args()

    scenarios_dir: Path | None = None
    if args.base_url:
        try:
            base_url = _validate_local_url(args.base_url)
        except ValueError as exc:
            parser.error(str(exc))
        temp_manager = None
    else:
        temp_manager = tempfile.TemporaryDirectory(prefix="netsentinel-responsive-")
        temp_root = Path(temp_manager.name)
        data_dir = temp_root / "data"
        data_dir.mkdir(parents=True)
        _seed_topology_fixture(data_dir)
        port = _free_local_port()
        base_url = f"http://127.0.0.1:{port}"

    try:
        if temp_manager is None:
            report = _run_browser_checks(
                base_url, args.viewports, args.output_dir, args.screenshots
            )
        else:
            scenarios_dir = temp_root / "manual-scenarios"
            generated = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "generate_manual_scenarios.py"),
                    "--output-dir", str(scenarios_dir),
                    "--device-ip", "192.168.56.20",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if generated.returncode != 0:
                raise RuntimeError(
                    "No pude preparar los CSV sintéticos para la prueba de navegador. "
                    f"Detalle: {generated.stderr[-2000:]}"
                )
            with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as server_log:
                environment = os.environ.copy()
                environment["NETSENTINEL_DATA_DIR"] = str(data_dir)
                environment["NETSENTINEL_DISABLE_SCHEDULER"] = "1"
                process = subprocess.Popen(
                    [
                        sys.executable, "-m", "netsentinel",
                        "--host", "127.0.0.1",
                        "--port", str(port),
                        "--no-browser",
                    ],
                    cwd=REPO_ROOT,
                    env=environment,
                    stdout=server_log,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                try:
                    _wait_for_server(base_url, process, server_log)
                    report = _run_browser_checks(
                        base_url, args.viewports, args.output_dir, args.screenshots, scenarios_dir
                    )
                finally:
                    _stop_server(process)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if temp_manager is not None:
            temp_manager.cleanup()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.output_dir / "report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print()
    print(
        f"Resultado: {report['passed_cases']}/{len(report['cases'])} "
        f"comprobaciones correctas; {report['failed_cases']} con fallos."
    )
    print(f"Informe: {report_path}")
    if args.screenshots:
        print(f"Capturas: {args.output_dir}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
