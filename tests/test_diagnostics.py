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



def _checks(*, gateway="ok", router="ok", dns="ok", external="ok"):
    return [
        {"name": "Puerta de enlace", "status": gateway},
        {"name": "Respuesta del router", "status": router},
        {"name": "Resolución DNS", "status": dns},
        {"name": "Conectividad IP externa", "status": external},
    ]


def test_assessment_identifies_possible_dns_problem():
    result = diagnostics.build_assessment(_checks(dns="warning", external="ok"))
    assert result["status"] == "warning"
    assert result["title"] == "Posible problema de DNS"
    assert any("DNS" in step for step in result["next_steps"])


def test_assessment_does_not_claim_internet_is_down_when_external_ping_fails():
    result = diagnostics.build_assessment(_checks(dns="ok", external="warning"))
    assert result["status"] == "warning"
    assert "no demuestra por sí solo" in result["summary"]


def test_assessment_recognizes_icmp_may_be_filtered():
    result = diagnostics.build_assessment(_checks(router="warning"))
    assert result["status"] == "ok"
    assert "bloquear ICMP" in result["summary"]
