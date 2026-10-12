import pytest

from netsentinel import __version__
from netsentinel.cli import main


def test_startup_message_explains_discovery_is_manual(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["netsentinel", "--no-browser"])
    monkeypatch.setattr("netsentinel.cli.uvicorn.run", lambda *args, **kwargs: None)

    main()

    output = capsys.readouterr().out
    assert f"NetSentinel iniciará en http://127.0.0.1:8765" in output
    assert "Al iniciar no se sondea la red." in output
    assert "solo empieza cuando lo solicitás desde el panel" in output


def test_cli_version_matches_package(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["netsentinel", "--version"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"NetSentinel {__version__}"


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.com", "localhost.localdomain"])
def test_cli_rejects_non_loopback_host_before_starting_server(monkeypatch, capsys, host):
    monkeypatch.setattr("sys.argv", ["netsentinel", "--host", host, "--no-browser"])
    monkeypatch.setattr(
        "netsentinel.cli.uvicorn.run",
        lambda *args, **kwargs: pytest.fail("El servidor no debe iniciarse con un host remoto."),
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2
    error = capsys.readouterr().err
    assert "por seguridad" in error
    assert "otros hostnames" in error


def test_cli_canonicalizes_localhost_to_literal_ipv4_loopback(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("sys.argv", ["netsentinel", "--host", "localhost", "--no-browser"])
    monkeypatch.setattr("netsentinel.cli.uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))

    main()

    assert "NetSentinel iniciará en http://127.0.0.1:8765" in capsys.readouterr().out
    assert calls[0][1]["host"] == "127.0.0.1"


def test_cli_supports_ipv6_loopback_url(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr("sys.argv", ["netsentinel", "--host", "::1", "--no-browser"])
    monkeypatch.setattr("netsentinel.cli.uvicorn.run", lambda *args, **kwargs: calls.append((args, kwargs)))

    main()

    assert "NetSentinel iniciará en http://[::1]:8765" in capsys.readouterr().out
    assert calls[0][1]["host"] == "::1"


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port"])
def test_cli_rejects_invalid_port(monkeypatch, capsys, port):
    monkeypatch.setattr("sys.argv", ["netsentinel", "--port", port, "--no-browser"])

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 2
    assert "puerto" in capsys.readouterr().err.lower()
