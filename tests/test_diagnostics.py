import subprocess

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



def test_dns_resolver_runs_isolated_process_with_explicit_timeout(monkeypatch):
    calls = {}

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            command, 0, stdout='["192.0.2.10", "2001:db8::10"]', stderr=""
        )

    monkeypatch.setattr(diagnostics.subprocess, "run", fake_run)
    addresses, error = diagnostics._resolve_hostname("example.com", timeout=1.25)

    assert addresses == ["192.0.2.10", "2001:db8::10"]
    assert error is None
    assert calls["command"][0] == diagnostics.sys.executable
    assert calls["command"][1] == "-c"
    compile(calls["command"][2], "<dns-resolver>", "exec")
    assert calls["command"][-1] == "example.com"
    assert calls["kwargs"]["timeout"] == 1.25
    assert calls["kwargs"]["capture_output"] is True


def test_dns_resolver_reports_timeout_without_waiting_indefinitely(monkeypatch):
    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(diagnostics.subprocess, "run", timeout_run)
    addresses, error = diagnostics._resolve_hostname("example.com", timeout=0.5)

    assert addresses == []
    assert error == "timeout"


def test_dns_resolver_rejects_failed_child_response(monkeypatch):
    monkeypatch.setattr(
        diagnostics.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 1, stdout='{"error":"gaierror"}', stderr=""
        ),
    )

    addresses, error = diagnostics._resolve_hostname("example.com")

    assert addresses == []
    assert error == "name_resolution_failed"


def test_assessment_explains_dns_timeout_without_claiming_permanent_failure():
    result = diagnostics.build_assessment(_checks(dns="timeout", external="ok"))

    assert result["status"] == "warning"
    assert result["title"] == "La consulta DNS tardó demasiado"
    assert "no confirma una avería permanente" in result["summary"]
    assert any("No cambies" in step for step in result["next_steps"])

def test_diagnostic_command_failures_have_stable_codes_and_logging_policy(monkeypatch):
    from netsentinel import diagnostics

    logged = []

    def missing_command(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(diagnostics.subprocess, "run", missing_command)
    monkeypatch.setattr(diagnostics.logger, "warning", lambda *args, **kwargs: logged.append(args))

    result = diagnostics.run_diagnostics()
    assert len(result["checks"]) == 4
    failures = [check for check in result["checks"] if "error_code" in check]
    assert failures
    assert all(check["error_code"].startswith("NS-DIAG-") for check in failures)
    assert any(check["logged"] for check in failures)
    assert logged
    assert all("detail" in check for check in failures)


def test_ping_nonresponse_is_mapped_but_not_logged_as_program_failure(monkeypatch):
    from netsentinel import diagnostics

    monkeypatch.setattr(diagnostics.platform, "system", lambda: "Linux")
    monkeypatch.setattr(diagnostics, "_find_default_gateway_result", lambda: ("192.168.1.1", None))
    monkeypatch.setattr(
        diagnostics,
        "_run_diagnostic",
        lambda command, timeout=3.0: (
            subprocess.CompletedProcess(command, 1, stdout="", stderr=""),
            "nonzero_exit",
        ),
    )
    logged = []
    monkeypatch.setattr(diagnostics.logger, "warning", lambda *args, **kwargs: logged.append(args))
    monkeypatch.setattr(diagnostics, "_resolve_hostname", lambda hostname, timeout=3.0: (["93.184.216.34"], None))

    result = diagnostics.run_diagnostics()
    router = next(check for check in result["checks"] if check["name"] == "Respuesta del router")
    external = next(check for check in result["checks"] if check["name"] == "Conectividad IP externa")

    assert router["error_code"] == "NS-DIAG-ROUTER-005"
    assert external["error_code"] == "NS-DIAG-EXT-005"
    assert router["logged"] is False
    assert external["logged"] is False
    assert not logged

