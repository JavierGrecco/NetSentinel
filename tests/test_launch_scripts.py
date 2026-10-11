from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_unix_launchers_use_a_local_virtual_environment():
    run_script = (ROOT / "run.sh").read_text(encoding="utf-8")
    macos_script = (ROOT / "run-macos.command").read_text(encoding="utf-8")
    assert ".venv/bin/python" in run_script
    assert "-m pip install -e ." in run_script
    assert ".netsentinel-install-hash" in run_script
    assert "pyproject.toml" in run_script
    assert "-m netsentinel" in run_script
    assert "exec ./run.sh" in macos_script


def test_windows_launcher_uses_local_virtual_environment():
    script = (ROOT / "run-windows.bat").read_text(encoding="utf-8")
    assert r".venv\Scripts\python.exe" in script
    assert "%PYTHON_CMD% -m venv .venv" in script
    assert "-m pip install -e ." in script
    assert ".netsentinel-install-hash" in script
    assert "pyproject.toml" in script
    assert "-m netsentinel" in script
    assert "3,10" in script
