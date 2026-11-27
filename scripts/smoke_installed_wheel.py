#!/usr/bin/env python3
"""Install a built wheel in a clean venv and smoke-test the packaged application.

This script deliberately launches the installed package from a temporary
working directory, never from the source checkout. It uses loopback only and
an isolated temporary SQLite directory.
"""
from __future__ import annotations

import argparse
from email.parser import Parser
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
import zipfile


STARTUP_TIMEOUT_SECONDS = 30.0


def _wheel_version(wheel_path: Path) -> str:
    """Read the distribution version directly from the wheel metadata."""
    with zipfile.ZipFile(wheel_path) as wheel:
        metadata_files = [
            name for name in wheel.namelist()
            if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise RuntimeError(
                f"Expected one wheel METADATA file, found {len(metadata_files)}."
            )
        metadata = Parser().parsestr(
            wheel.read(metadata_files[0]).decode("utf-8")
        )
    version = metadata.get("Version")
    if not version:
        raise RuntimeError("The built wheel has no Version metadata.")
    return version


def _venv_python(venv: Path) -> Path:
    """Return the platform-specific Python executable inside a venv."""
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    executable = venv / relative
    if not executable.is_file():
        raise RuntimeError(f"Virtual environment Python was not created: {executable}")
    return executable


def _console_script(venv: Path) -> Path:
    """Return the installed console entry point for the current platform."""
    relative = Path("Scripts/netsentinel.exe") if os.name == "nt" else Path("bin/netsentinel")
    executable = venv / relative
    if not executable.is_file():
        raise RuntimeError(f"Installed netsentinel entry point is missing: {executable}")
    return executable


def _reserve_loopback_port() -> int:
    """Select an available TCP port without binding the app to a non-loopback interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _read_url(url: str, timeout: float = 3.0) -> tuple[int, dict[str, str], bytes]:
    """Read an HTTP response and preserve headers for security assertions."""
    with urlopen(url, timeout=timeout) as response:
        return (
            int(response.status),
            {key.lower(): value for key, value in response.headers.items()},
            response.read(),
        )


def _wait_for_health(base_url: str, process: subprocess.Popen[str]) -> dict[str, Any]:
    """Wait until the isolated installed application serves its health endpoint."""
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error: str | None = None
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            output = process.communicate(timeout=2)[0]
            raise RuntimeError(
                "Installed NetSentinel exited before becoming healthy "
                f"(exit {return_code}). Output:\n{output[-6000:]}"
            )
        try:
            status, headers, body = _read_url(f"{base_url}/api/health", timeout=2.0)
            if status != 200:
                raise RuntimeError(f"Health endpoint returned HTTP {status}.")
            payload = json.loads(body.decode("utf-8"))
            if payload.get("status") != "ok":
                raise RuntimeError(f"Unexpected health payload: {payload!r}")
            request_id = headers.get("x-request-id", "")
            if len(request_id) != 12:
                raise RuntimeError("Health response is missing the 12-character request ID.")
            if headers.get("x-content-type-options", "").lower() != "nosniff":
                raise RuntimeError("Health response is missing X-Content-Type-Options: nosniff.")
            return payload
        except (URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(0.25)

    output = ""
    if process.poll() is not None:
        output = process.communicate(timeout=2)[0]
    raise RuntimeError(
        "Installed NetSentinel did not become healthy within "
        f"{STARTUP_TIMEOUT_SECONDS:.0f}s. Last error: {last_error or 'unknown'}\n"
        f"{output[-6000:]}"
    )


def _assert_json(base_url: str, path: str, expected: Any) -> None:
    status, _headers, body = _read_url(f"{base_url}{path}")
    if status != 200:
        raise RuntimeError(f"{path} returned HTTP {status}.")
    actual = json.loads(body.decode("utf-8"))
    if actual != expected:
        raise RuntimeError(f"{path} returned {actual!r}; expected {expected!r}.")


def _run_smoke(wheel_path: Path) -> None:
    version = _wheel_version(wheel_path)
    print(f"[wheel] artifact version: {version}", flush=True)

    with tempfile.TemporaryDirectory(prefix="netsentinel-wheel-smoke-") as temporary:
        root = Path(temporary)
        venv = root / "venv"
        work_dir = root / "work"
        data_dir = root / "data"
        work_dir.mkdir()
        data_dir.mkdir()

        subprocess.run(
            [sys.executable, "-m", "venv", str(venv)],
            check=True,
            text=True,
        )
        isolated_python = _venv_python(venv)
        subprocess.run(
            [
                str(isolated_python), "-m", "pip", "install",
                "--disable-pip-version-check", "--no-cache-dir",
                str(wheel_path),
            ],
            check=True,
            text=True,
        )
        print("[wheel] installed into a new virtual environment with runtime dependencies", flush=True)

        console = _console_script(venv)
        version_result = subprocess.run(
            [str(console), "--version"],
            cwd=work_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        if version_result.stdout.strip() != f"NetSentinel {version}":
            raise RuntimeError(
                "Console entry point version differs from wheel metadata: "
                f"{version_result.stdout.strip()!r} != {version!r}."
            )

        port = _reserve_loopback_port()
        base_url = f"http://127.0.0.1:{port}"
        environment = os.environ.copy()
        environment["NETSENTINEL_DATA_DIR"] = str(data_dir)
        environment["NETSENTINEL_DISABLE_SCHEDULER"] = "1"
        environment.pop("PYTHONPATH", None)

        process = subprocess.Popen(
            [
                str(isolated_python), "-m", "netsentinel",
                "--host", "127.0.0.1",
                "--port", str(port),
                "--no-browser",
            ],
            cwd=work_dir,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            _wait_for_health(base_url, process)
            print("[wheel] /api/health returned status=ok with security headers", flush=True)

            for path, expected_marker in (
                ("/", "NetSentinel"),
                ("/network", "NetSentinel"),
                ("/activity", "NetSentinel"),
                ("/findings", "NetSentinel"),
                ("/guided-test", "wizardStepTitle"),
            ):
                status, _headers, body = _read_url(f"{base_url}{path}")
                html = body.decode("utf-8")
                if status != 200 or expected_marker not in html:
                    raise RuntimeError(
                        f"Packaged page {path} failed: HTTP {status}; "
                        f"expected marker {expected_marker!r}."
                    )

            for path in ("/static/theme.js", "/static/theme.css", "/static/styles.css"):
                status, _headers, body = _read_url(f"{base_url}{path}")
                if status != 200 or not body:
                    raise RuntimeError(f"Packaged static asset {path} is missing or empty.")
            print("[wheel] core pages and shared theme assets served from the installed package", flush=True)

            _assert_json(base_url, "/api/devices", [])
            _assert_json(base_url, "/api/scans", [])
            status, _headers, body = _read_url(f"{base_url}/api/export/data.json")
            if status != 200:
                raise RuntimeError(f"Initial data export returned HTTP {status}.")
            export = json.loads(body.decode("utf-8"))
            if export.get("format") != "netsentinel-data-export-v4":
                raise RuntimeError(
                    f"Unexpected initial export format: {export.get('format')!r}."
                )
            if any(data_dir.iterdir()) is False:
                raise RuntimeError("The application did not initialize its isolated data directory.")
            print("[wheel] read-only API and initial SQLite data export verified; no discovery was started", flush=True)
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                output = process.communicate(timeout=10)[0]
            except subprocess.TimeoutExpired:
                process.kill()
                output = process.communicate(timeout=5)[0]
            if process.returncode not in (0, -15, 1, 143):
                raise RuntimeError(
                    f"Installed application shut down unexpectedly (exit {process.returncode}).\n"
                    f"{output[-6000:]}"
                )

    print(f"Installed wheel smoke test passed on {sys.platform} ({version}).", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a built NetSentinel wheel in a clean virtual environment and test startup."
    )
    parser.add_argument(
        "--wheel-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing exactly one built .whl file (default: dist).",
    )
    args = parser.parse_args()

    wheel_dir = args.wheel_dir.expanduser().resolve()
    wheels = sorted(wheel_dir.glob("*.whl")) if wheel_dir.is_dir() else []
    if len(wheels) != 1:
        parser.error(
            f"Expected exactly one wheel in {wheel_dir}, found {len(wheels)}."
        )

    try:
        _run_smoke(wheels[0])
    except (OSError, subprocess.SubprocessError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"Installed wheel smoke test failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
