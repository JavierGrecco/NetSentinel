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
    ("/findings", "Hallazgos con evidencia", "hallazgos"),
    ("/monitors", "Monitorización", "monitorizacion"),
    ("/tools", "Herramientas de red", "herramientas"),
    ("/activity", "Actividad y telemetría", "actividad"),
    ("/forensics", "Área de análisis forense", "forensics"),
    ("/world-map", "Mapa mundial de IP", "geolocation"),
    ("/guided-test", "Prueba guiada de NetSentinel", "guided-test"),
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




def _topology_panel_failures(page) -> list[str]:
    """Comprueba el grafo real con una fixture local, selección y filtro."""
    failures: list[str] = []
    panel = page.locator("#topologyPanel")
    if panel.count() != 1:
        return ["no aparece un único panel del mapa de relaciones"]

    summary_button = panel.locator(":scope > summary")
    if summary_button.count() != 1:
        return ["el mapa no tiene un control claro para abrir o cerrar la vista"]

    try:
        if panel.get_attribute("open") is None:
            summary_button.click()
        page.wait_for_function(
            """() => {
              const svg = document.querySelector("#topologyCanvas svg.topology-svg");
              return svg && svg.querySelectorAll(".topology-device-node").length > 0;
            }""",
            timeout=5000,
        )
    except Exception as exc:
        return [f"el mapa no terminó de dibujar la fixture de prueba: {exc}"]

    accessible_details = panel.locator("details.topology-accessible")
    if accessible_details.count() != 1:
        failures.append("falta el acceso a la alternativa textual")
    elif accessible_details.get_attribute("open") is None:
        accessible_details.locator("summary").click()

    for selector, description in (
        ("#topologySearch", "el filtro de dispositivos"),
        ("#topologyResetSearch", "el botón para limpiar el filtro"),
        ("#topologyCanvas", "el área del grafo"),
        ("#topologySelection", "el panel de detalle"),
        ("#topologyAccessibleList", "la alternativa textual"),
    ):
        element = panel.locator(selector)
        if element.count() != 1:
            failures.append(f"falta {description}")
        elif not element.is_visible():
            failures.append(f"no está visible {description} al abrir el mapa")

    try:
        node = panel.locator("#topologyCanvas .topology-device-node").first
        node.click()
        detail = panel.locator("#topologySelection")
        if "Evidencia de la lectura #" not in detail.inner_text():
            failures.append("seleccionar un nodo no muestra la evidencia de la lectura")
        if "192.168.56.20" not in detail.inner_text():
            failures.append("el detalle no muestra la dirección observada en la fixture")

        search = panel.locator("#topologySearch")
        reset = panel.locator("#topologyResetSearch")
        search.fill("filtro-sin-coincidencias")
        if panel.locator("#topologyCanvas .topology-device-node").count() != 0:
            failures.append("el filtro del grafo no oculta nodos que no coinciden")
        reset.click()
        if panel.locator("#topologyCanvas .topology-device-node").count() == 0:
            failures.append("Limpiar filtro no restablece los nodos del mapa")
    except Exception as exc:
        failures.append(f"no se pudo seleccionar o filtrar un nodo del mapa: {exc}")

    metrics = _page_metrics(page)
    if metrics["documentWidth"] > metrics["viewportWidth"] + 1:
        failures.append(
            "el mapa abierto produce desplazamiento horizontal global "
            f"(documento {metrics['documentWidth']} px, ventana {metrics['viewportWidth']} px)"
        )
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

    # Comprueba el recorrido real del nuevo botón y verifica el archivo que descarga.
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


def _guided_test_interaction_failures(page, base_url: str) -> list[str]:
    """Comprueba el progreso persistente y las dos comprobaciones de API de la guía."""
    failures: list[str] = []
    try:
        steps = page.locator("[data-guided-step]")
        if steps.count() != 16:
            return [f"la guía mostró {steps.count()} pasos en lugar de 16"]
        setup_step = page.locator('[data-guided-step="setup"]')
        if setup_step.count() != 1:
            return ["falta la casilla para confirmar la preparación del laboratorio"]

        page.locator("#resetGuidedProgress").click()
        setup_step.check()
        if page.locator("#guidedProgressCount").inner_text() != "1 de 16 pasos":
            failures.append("el contador de progreso no actualizó el primer paso")
        page.reload(wait_until="load")
        if not page.locator('[data-guided-step="setup"]').is_checked():
            failures.append("el progreso de la guía no persistió al recargar la página")

        page.locator("#checkMapApi").click()
        page.wait_for_function(
            """() => document.querySelector("#mapApiStatus")?.classList.contains("is-success")""",
            timeout=8000,
        )
        if "API del mapa: disponible" not in page.locator("#mapApiStatus").inner_text():
            failures.append("la guía no confirmó correctamente la API del mapa")

        page.locator("#checkForensicsApi").click()
        page.wait_for_function(
            """() => document.querySelector("#forensicsApiStatus")?.classList.contains("is-success")""",
            timeout=8000,
        )
        if "API de Forense: disponible" not in page.locator("#forensicsApiStatus").inner_text():
            failures.append("la guía no confirmó correctamente la API de Forense")

        page.locator("#resetGuidedProgress").click()
        if page.locator("[data-guided-step]:checked").count() != 0:
            failures.append("el botón de reinicio no limpió las casillas de la guía")
        if page.locator("#guidedProgressCount").inner_text() != "0 de 16 pasos":
            failures.append("el reinicio no devolvió el contador de la guía a cero")
    except Exception as exc:
        failures.append(f"la interacción de Prueba guiada falló en Chromium: {exc}")
    finally:
        try:
            page.goto(f"{base_url}/guided-test", wait_until="load", timeout=10000)
            page.locator("#resetGuidedProgress").click()
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
                                case_failures.extend(_topology_panel_failures(page))
                                if viewport == Viewport(1440, 900):
                                    case_failures.extend(_scan_comparison_failures(page))
                            if path == "/monitors" and viewport == Viewport(1440, 900):
                                case_failures.extend(_monitor_history_accessibility_failures(page))
                            if path == "/forensics" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(_forensics_hash_failure_refresh_failures(page))
                            if path == "/activity" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(
                                    _activity_synthetic_import_failures(page, base_url, scenarios_dir)
                                )
                            if path == "/guided-test" and viewport == Viewport(1440, 900):
                                case_failures.extend(
                                    _guided_test_interaction_failures(page, base_url)
                                )
                            if path == "/world-map" and viewport == Viewport(1440, 900) and scenarios_dir is not None:
                                case_failures.extend(_world_map_render_failures(page, base_url))

                            for script_error in page_errors[error_start:]:
                                case_failures.append(
                                    f"error JavaScript: {script_error['message']}"
                                )

                            should_capture = screenshots and (
                                path == "/" or viewport == Viewport(1440, 900)
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
