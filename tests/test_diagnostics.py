from netsentinel import diagnostics


def test_ping_command_uses_windows_options(monkeypatch):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Windows")
    assert diagnostics._ping_command("192.168.1.1") == ["ping", "-n", "1", "-w", "1200", "192.168.1.1"]


def test_ping_command_uses_milliseconds_on_macos(monkeypatch):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Darwin")
    assert diagnostics._ping_command("192.168.1.1") == ["ping", "-c", "1", "-W", "2000", "192.168.1.1"]


def test_ping_command_uses_seconds_on_linux(monkeypatch):
    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Linux")
    assert diagnostics._ping_command("192.168.1.1") == ["ping", "-c", "1", "-W", "2", "192.168.1.1"]
