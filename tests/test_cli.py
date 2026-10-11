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

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 0
    else:
        raise AssertionError("El argumento --version debería salir correctamente.")

    assert capsys.readouterr().out.strip() == f"NetSentinel {__version__}"
