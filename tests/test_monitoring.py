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
    with TestClient(app, base_url='http://127.0.0.1') as client:
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
    with TestClient(app, base_url='http://127.0.0.1') as client:
        bad = client.post("/api/monitors", json={
            "name": "Bad", "kind": "http", "target": "https://example.com/path?secret=value",
            "interval_seconds": 60, "timeout_seconds": 3,
        })
        assert bad.status_code == 422


def test_monitor_analytics_calculates_window_summary_and_per_monitor_stats(tmp_path):
    path = tmp_path / "analytics.sqlite3"
    database.initialize(path)
    first = database.create_monitor("Servicio A", "tcp", "127.0.0.1:80", 60, 2, path=path)
    second = database.create_monitor("Servicio B", "ping", "127.0.0.1", 60, 2, path=path)
    database.record_monitor_check(first["id"], "up", 20.0, "Correcto", path=path)
    database.record_monitor_check(first["id"], "up", 10.0, "Correcto", path=path)
    database.record_monitor_check(first["id"], "down", None, "Sin respuesta", path=path)
    database.record_monitor_check(second["id"], "up", 5.0, "Correcto", path=path)

    data = database.get_monitor_analytics(window_hours=24, path=path)
    assert data["window_hours"] == 24
    assert data["summary"]["checks_total"] == 4
    assert data["summary"]["checks_up"] == 3
    assert data["summary"]["checks_down"] == 1
    assert data["summary"]["success_rate_percent"] == 75.0
    assert data["summary"]["average_latency_ms"] == pytest.approx(11.67)
    by_id = {item["monitor_id"]: item for item in data["monitors"]}
    assert by_id[first["id"]]["success_rate_percent"] == pytest.approx(66.67)
    assert by_id[first["id"]]["average_latency_ms"] == 15.0
    assert by_id[first["id"]]["min_latency_ms"] == 10.0
    assert by_id[first["id"]]["max_latency_ms"] == 20.0
    assert by_id[second["id"]]["success_rate_percent"] == 100.0


def test_monitor_analytics_empty_window_and_hour_clamp(tmp_path):
    path = tmp_path / "analytics-empty.sqlite3"
    database.initialize(path)
    database.create_monitor("Sin datos", "ping", "127.0.0.1", 60, 2, path=path)
    data = database.get_monitor_analytics(window_hours=999, path=path)
    assert data["window_hours"] == 168
    assert data["summary"]["checks_total"] == 0
    assert data["summary"]["success_rate_percent"] is None
    assert data["summary"]["average_latency_ms"] is None
    assert data["monitors"][0]["success_rate_percent"] is None


def test_monitor_analytics_api_accepts_24_hours_or_week(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        default = client.get("/api/monitoring/summary")
        weekly = client.get("/api/monitoring/summary?hours=168")
        invalid = client.get("/api/monitoring/summary?hours=169")
    assert default.status_code == 200
    assert default.json()["window_hours"] == 24
    assert default.json()["summary"]["checks_total"] == 0
    assert weekly.status_code == 200
    assert weekly.json()["window_hours"] == 168
    assert invalid.status_code == 422


def test_monitor_analytics_csv_export_contains_metrics_and_safe_text(tmp_path):
    import csv
    import io

    path = tmp_path / "report.sqlite3"
    database.initialize(path)
    monitor = database.create_monitor("=SUM(A1:A2)", "tcp", "127.0.0.1:443", 60, 3, path=path)
    database.record_monitor_check(monitor["id"], "up", 4.5, "Correcto", path=path)
    database.record_monitor_check(monitor["id"], "down", None, "Fallo", path=path)

    export = database.export_monitoring_csv(window_hours=24, path=path)
    assert export.startswith("\\ufeff")
    rows = list(csv.DictReader(io.StringIO(export.lstrip("\\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["nombre"] == "'=SUM(A1:A2)"
    assert rows[0]["comprobaciones"] == "2"
    assert rows[0]["correctas"] == "1"
    assert rows[0]["fallidas"] == "1"
    assert rows[0]["tasa_exito_pct"] == "50.0"
    assert rows[0]["latencia_media_ms"] == "4.5"


def test_monitoring_csv_api_sets_download_and_privacy_headers(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.create_monitor("Servicio", "ping", "127.0.0.1", 60, 3)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/export/monitoring.csv?hours=168")
        invalid = client.get("/api/export/monitoring.csv?hours=169")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "netsentinel-monitoring-report.csv" in response.headers["content-disposition"]
    assert response.text.lstrip("\\ufeff").splitlines()[1].startswith("168,")
    assert invalid.status_code == 422
