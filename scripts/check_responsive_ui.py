#!/usr/bin/env python3
"""Comprueba la interfaz web de NetSentinel en varios tamaños de ventana.

Por defecto inicia una instancia local temporal con una base SQLite nueva.
No inicia descubrimientos ni ejecuta diagnósticos de red.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from dataclasses import asdict, dataclass
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

        # La UI de monitorización también usa solo datos sintéticos.
        from datetime import datetime, timedelta, timezone

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
            failures.append("la segunda fila invade verticalmente la primera")
    else:
        ordered = [inventory, activity, diagnostics, scans]
        if any(
            ordered[index + 1]["top"] < ordered[index]["bottom"] - tolerance
            for index in range(len(ordered) - 1)
        ):
            failures.append("los paneles no se apilan en orden en una ventana estrecha")
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
        node.click()
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
        page.wait_for_function(
            "() => document.querySelectorAll('#topologyEvents .topology-history-entry').length > 0",
            timeout=3000,
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

        page.locator("#topologyZoomIn").click()
        page.locator("#topologyFit").click()
        search = panel.locator("#topologySearch")
        reset = panel.locator("#topologyResetSearch")
        search.fill("filtro-sin-coincidencias")
        page.wait_for_function(
            "() => window.NetSentinelTopology.getGraphStats().deviceCount === 0",
            timeout=3000,
        )
        reset.click()
        page.wait_for_function(
            "() => window.NetSentinelTopology.getGraphStats().deviceCount > 0",
            timeout=4000,
        )
    except Exception as exc:
        failures.append(f"no se pudo seleccionar o filtrar un nodo del mapa: {exc}")

    metrics = _page_metrics(page)
    if metrics["documentWidth"] > metrics["viewportWidth"] + 1:
        failures.append(
            "el mapa abierto produce desplazamiento horizontal global "
            f"(documento {metrics['documentWidth']} px, ventana {metrics['viewportWidth']} px)"
        )
    if check_missing_evidence:
        pattern = "**/api/scans/*/observations"
        try:
            # Simula que una fuente histórica no responde. El mapa no debe
            # inventar líneas ni traducir la falta de datos en un cero confirmado.
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
            if page.locator("#topologyCanvas canvas").count() != 0:
                failures.append("el explorador dibuja relaciones cuando no se recuperó la evidencia histórica")
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
              return result && result.textContent.includes("No se detectaron diferencias") &&
                result.textContent.includes("No demuestra");
            }""",
            timeout=5000,
        )
    except Exception as exc:
        return [f"la comparación entre capturas sintéticas no terminó correctamente: {exc}"]

    rendered = result.inner_text()
    if "192.168.56.0/24" not in rendered:
        failures.append("la comparación no informa la subred compartida")
    if "No demuestra que esté desconectado" not in rendered:
        failures.append("la comparación no explica el límite de interpretar ausencias")
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


def _run_browser_checks(base_url: str, viewports: tuple[Viewport, ...], output_dir: Path, screenshots: bool) -> dict:
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

                            current_links = page.locator(
                                '.primary-nav a.nav-link[aria-current="page"]'
                            )
                            if current_links.count() != 1:
                                case_failures.append(
                                    "la navegación no identifica exactamente una sección activa"
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
                                if viewport == Viewport(1440, 900):
                                    case_failures.extend(_scan_comparison_failures(page))
                            if path == "/network":
                                case_failures.extend(_topology_panel_failures(
                                    page,
                                    check_missing_evidence=(viewport == Viewport(1440, 900)),
                                ))
                            if path == "/monitors" and viewport == Viewport(1440, 900):
                                case_failures.extend(_monitor_history_accessibility_failures(page))

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
            "Revisa las cinco pantallas de NetSentinel en múltiples tamaños. "
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
                        base_url, args.viewports, args.output_dir, args.screenshots
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
