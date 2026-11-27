#!/usr/bin/env python3
"""End-to-end test of the unpacked MV3 extension in real Chromium.

All navigations are fulfilled by Playwright from synthetic HTML. Any request
outside the explicit synthetic allowlist is aborted, so the test never visits
an external site or transmits navigation data.
"""
from __future__ import annotations

import argparse
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit


SENSITIVE_FIXTURE = "netsentinel-extension-secret-fixture"
SEARCH_FIXTURE = "netsentinel-smoke-search-phrase"
PRIVATE_FRAGMENT = "must-not-leak-this-fragment"


def _synthetic_response(blocked_requests: list[str]):
    """Return a route handler that only fulfils synthetic sites and records blocked requests."""
    def handle(route, request) -> None:
        parsed = urlsplit(request.url)
        if parsed.scheme not in {"http", "https"}:
            # Browser-internal and extension resources never use the external network.
            route.continue_()
            return

        host = (parsed.hostname or "").lower()
        allowed_hosts = {"example.com", "sub.example.com", "www.google.com"}
        is_loopback_fixture = host == "127.0.0.1"

        if parsed.scheme == "https" and host in allowed_hosts:
            route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body=(
                    "<!doctype html><html lang='en'><head><title>NetSentinel synthetic page</title>"
                    "</head><body><main>synthetic browser fixture</main></body></html>"
                ),
            )
            return
        if parsed.scheme == "http" and is_loopback_fixture:
            route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                body="<html><body>loopback fixture</body></html>",
            )
            return

        # Abort before transmission and fail the test if Chromium tried an unapproved URL.
        blocked_requests.append(request.url)
        route.abort("blockedbyclient")

    return handle


def _extension_id(context) -> str:
    """Wait for the installed Manifest V3 service worker and derive its ID."""
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        for worker in context.service_workers:
            if worker.url.endswith("/service-worker.js"):
                parsed = urlsplit(worker.url)
                if parsed.scheme == "chrome-extension" and parsed.hostname:
                    return parsed.hostname
        context.wait_for_timeout(200)
    urls = [worker.url for worker in context.service_workers]
    raise RuntimeError(f"Extension service worker did not start. Workers seen: {urls!r}")


def _read_events(extension_page) -> list[dict]:
    """Read the extension's local store from its own origin."""
    return extension_page.evaluate(
        """async () => await new Promise(resolve =>
            chrome.storage.local.get(["netsentinelEvents"], value =>
                resolve(Array.isArray(value.netsentinelEvents) ? value.netsentinelEvents : [])
            )
        )"""
    )


def _wait_for_event_count(extension_page, expected: int, timeout_ms: int = 10000) -> list[dict]:
    """Wait until the serialized service-worker queue has persisted its result."""
    extension_page.wait_for_function(
        """expected => new Promise(resolve =>
            chrome.storage.local.get(["netsentinelEvents"], value =>
                resolve(Array.isArray(value.netsentinelEvents) &&
                    value.netsentinelEvents.length === expected)
            )
        )""",
        arg=expected,
        timeout=timeout_ms,
    )
    return _read_events(extension_page)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run_extension_test(extension_dir: Path) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            'Playwright is required; install with python -m pip install -e ".[test,ui-test]".'
        ) from exc

    if not extension_dir.is_dir():
        raise RuntimeError(f"Extension directory not found: {extension_dir}")

    with tempfile.TemporaryDirectory(prefix="netsentinel-chromium-extension-") as temporary:
        profile = Path(temporary) / "profile"
        downloads = Path(temporary) / "downloads"
        downloads.mkdir()

        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile),
                headless=False,
                accept_downloads=True,
                downloads_path=str(downloads),
                args=[
                    f"--disable-extensions-except={extension_dir}",
                    f"--load-extension={extension_dir}",
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-default-apps",
                    "--no-default-browser-check",
                    "--no-first-run",
                    "--disable-sync",
                ],
            )
            try:
                context.set_default_timeout(10000)
                blocked_requests: list[str] = []
                context.route("**/*", _synthetic_response(blocked_requests))
                extension_id = _extension_id(context)
                extension_url = f"chrome-extension://{extension_id}/popup.html"

                popup = context.new_page()
                popup.goto(extension_url, wait_until="load")
                _assert(
                    not popup.locator("#enabled").is_checked(),
                    "The extension must be off by default in a newly created profile.",
                )
                _assert(
                    "No se registra navegación" in popup.locator("#statusText").inner_text(),
                    "The default popup status must explain that capture is stopped.",
                )
                _assert(popup.locator("#count").inner_text() == "0", "A clean profile must have no events.")

                page = context.new_page()
                # A navigation before opt-in must not be recorded.
                page.goto("https://example.com/before-opt-in", wait_until="load")
                popup.reload(wait_until="load")
                _assert(_read_events(popup) == [], "A visit before opt-in was recorded.")

                # Explicit opt-in is required and visible.
                popup.on("dialog", lambda dialog: dialog.accept())
                popup.locator("#enabled").check()
                popup.wait_for_function(
                    "() => (document.querySelector('#statusText')?.textContent || '').startsWith('Activo.')"
                )
                _assert(popup.locator("#enabled").is_checked(), "Opt-in did not persist as enabled.")

                # Sensitive query keys and URL fragments must not survive sanitization.
                page.goto(
                    "https://example.com/account?access_token="
                    + SENSITIVE_FIXTURE
                    + "&keep=visible#"
                    + PRIVATE_FRAGMENT,
                    wait_until="load",
                )
                # Search terms are stored as an explicit search event, not in page_url.
                page.goto(
                    "https://www.google.com/search?q="
                    + SEARCH_FIXTURE
                    + "&access_token="
                    + SENSITIVE_FIXTURE,
                    wait_until="load",
                )
                events = _wait_for_event_count(popup, 3)
                serialized = str(events)
                _assert(SENSITIVE_FIXTURE not in serialized, "A sensitive query parameter leaked into storage.")
                _assert(PRIVATE_FRAGMENT not in serialized, "A URL fragment leaked into storage.")
                _assert(any(
                    event.get("event_type") == "page_visit"
                    and event.get("domain") == "example.com"
                    and "keep=visible" in (event.get("page_url") or "")
                    for event in events
                ), "The allowed account-page visit or its safe query parameter was not captured.")
                _assert(any(
                    event.get("event_type") == "search_query"
                    and event.get("search_engine") == "Google"
                    and event.get("search_terms") == SEARCH_FIXTURE
                    for event in events
                ), "The synthetic Google search was not separated into a search_query event.")

                # User-managed domain exclusions are applied to subdomains too.
                popup.locator("#excludeDomains").fill("example.com")
                popup.locator("#saveSettings").click()
                popup.wait_for_function(
                    "() => (document.querySelector('#statusText')?.textContent || '').startsWith('Activo.')"
                )
                page.goto("https://sub.example.com/excluded", wait_until="load")
                page.goto("http://127.0.0.1:8765/private-network-fixture", wait_until="load")
                context.wait_for_timeout(500)
                popup.reload(wait_until="load")
                events = _wait_for_event_count(popup, 3)
                _assert(
                    all(event.get("domain") != "sub.example.com" for event in events),
                    "The subdomain exclusion did not apply.",
                )
                _assert(
                    all(event.get("domain") != "127.0.0.1" for event in events),
                    "A loopback/private destination was captured.",
                )

                # Export should preserve safe values while excluding secret material.
                with popup.expect_download() as download_info:
                    popup.locator("#export").click()
                download = download_info.value
                download_path = download.path()
                _assert(download_path is not None, "CSV download did not produce a file.")
                csv_bytes = Path(download_path).read_bytes()
                csv_text = csv_bytes.decode("utf-8-sig")
                _assert(csv_bytes.startswith(bytes((0xEF, 0xBB, 0xBF))), "CSV export must contain its UTF-8 BOM.")
                _assert(SEARCH_FIXTURE in csv_text, "CSV export omitted the safe synthetic search phrase.")
                _assert(SENSITIVE_FIXTURE not in csv_text, "CSV export leaked a sensitive query parameter.")
                _assert(PRIVATE_FRAGMENT not in csv_text, "CSV export leaked a URL fragment.")

                # Clearing is routed through the service worker's serialized queue.
                popup.locator("#clear").click()
                popup.wait_for_function(
                    "() => (document.querySelector('#count')?.textContent || '') === '0'"
                )
                _assert(_read_events(popup) == [], "The explicit clear action left events in storage.")

                # Turning capture off again must stop future recording.
                popup.locator("#enabled").uncheck()
                popup.wait_for_function(
                    "() => (document.querySelector('#statusText')?.textContent || '').startsWith('Detenido.')"
                )
                page.goto("https://example.com/after-stop", wait_until="load")
                context.wait_for_timeout(500)
                popup.reload(wait_until="load")
                _assert(_read_events(popup) == [], "A visit after opt-out was recorded.")

                _assert(
                    not blocked_requests,
                    "Chromium attempted an unapproved HTTP/HTTPS request; all requests must stay inside the synthetic allowlist: "
                    + repr(blocked_requests),
                )
                print(
                    "Chromium extension integration passed: default-off, explicit opt-in, "
                    "synthetic page/search capture, URL sanitization, domain/loopback exclusions, "
                    "CSV export and clear/opt-out. All HTTP navigations were intercepted; "
                    "no unapproved request was attempted."
                )
            finally:
                context.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise the unpacked NetSentinel MV3 extension inside Chromium with mocked pages."
    )
    parser.add_argument(
        "--extension-dir",
        type=Path,
        default=Path("browser-extension"),
        help="Directory containing manifest.json (default: browser-extension).",
    )
    args = parser.parse_args()
    try:
        run_extension_test(args.extension_dir.expanduser().resolve())
    except Exception as exc:
        print(f"Chromium extension integration failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
