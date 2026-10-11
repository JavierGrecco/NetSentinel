import pytest
from fastapi.testclient import TestClient
from netsentinel import database
from netsentinel.main import app
from netsentinel.monitoring import validate_spec


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


def test_monitor_spec_validation():
    assert validate_spec("tcp", "127.0.0.1:443", 60, 3) == ("tcp", "127.0.0.1:443", 60, 3)
    assert validate_spec("http", "https://example.com/health", 60, 3)[0] == "http"
    with pytest.raises(ValueError):
        validate_spec("ping", "-c 10 127.0.0.1", 60, 3)
    with pytest.raises(ValueError):
        validate_spec("tcp", "127.0.0.1:99999", 60, 3)
    with pytest.raises(ValueError):
        validate_spec("http", "https://example.com/health?token=secret", 60, 3)
    with pytest.raises(ValueError):
        validate_spec("ping", "127.0.0.1", 1, 3)


def test_incident_deduplication_and_recovery(tmp_path):
    path = tmp_path / "monitor.sqlite3"
    database.initialize(path)
    monitor = database.create_monitor("Servicio", "tcp", "127.0.0.1:9", 60, 2, path=path)
    first = database.record_monitor_check(monitor["id"], "down", None, "No conecta", path=path)
    repeated = database.record_monitor_check(monitor["id"], "down", None, "Sigue caído", path=path)
    recovered = database.record_monitor_check(monitor["id"], "up", 1.2, "Conexión correcta", path=path)
    assert first["transition"]["transition"] == "down"
    assert repeated["transition"] is None
    assert recovered["transition"]["transition"] == "recovered"
    incidents = database.get_incidents(path=path, limit=10)
    assert len(incidents) == 1
    assert incidents[0]["status"] == "resolved"
    assert incidents[0]["failure_count"] == 2
    events = database.get_events(path=path)
    assert sum(event["event_type"] == "monitor_down" for event in events) == 1
    assert sum(event["event_type"] == "monitor_recovered" for event in events) == 1


def test_monitor_api_and_static_css(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monkeypatch.setattr("netsentinel.monitoring.probe", lambda kind, target, timeout: {
        "status": "up", "latency_ms": 1.5, "detail": "Prueba simulada"
    })
    with TestClient(app) as client:
        assert client.get("/monitors").status_code == 200
        assert client.get("/static/styles.css").status_code == 200
        assert client.get("/static/monitors.css").status_code == 200
        created = client.post("/api/monitors", json={
            "name": "Endpoint local", "kind": "http", "target": "https://example.com/health",
            "interval_seconds": 60, "timeout_seconds": 3,
        })
        assert created.status_code == 201
        monitor_id = created.json()["id"]
        checked = client.post(f"/api/monitors/{monitor_id}/check")
        assert checked.status_code == 200
        assert checked.json()["check"]["status"] == "up"
        assert len(client.get(f"/api/monitors/{monitor_id}/checks").json()) == 1
        assert client.get("/api/notifications").status_code == 200
        assert client.delete(f"/api/monitors/{monitor_id}").json()["ok"] is True


def test_monitor_api_rejects_unsafe_targets(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app) as client:
        bad = client.post("/api/monitors", json={
            "name": "Bad", "kind": "http", "target": "https://example.com/path?secret=value",
            "interval_seconds": 60, "timeout_seconds": 3,
        })
        assert bad.status_code == 422
