import pytest
from fastapi.testclient import TestClient
from netsentinel import database
from netsentinel.main import app
from netsentinel.monitoring import DEFAULT_MONITOR_HISTORY_DAYS, HISTORY_CLEANUP_INTERVAL_SECONDS, MonitorSupervisor, monitor_history_retention_days, validate_spec


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
        page = client.get("/monitors")
        assert page.status_code == 200
        assert 'id="analytics"' in page.text
        assert "history-timeline" in page.text
        assert client.get("/static/styles.css").status_code == 200
        monitor_css = client.get("/static/monitors.css")
        assert monitor_css.status_code == 200
        assert ".check-mark.up" in monitor_css.text
        assert ".check-mark.down" in monitor_css.text
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
    assert export.startswith("\ufeff")
    rows = list(csv.DictReader(io.StringIO(export.lstrip("\ufeff"))))
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
    assert response.text.lstrip("\ufeff").splitlines()[1].startswith("168,")
    assert invalid.status_code == 422


def test_monitor_analytics_has_time_index_for_growing_history(tmp_path):
    path = tmp_path / "indexed-analytics.sqlite3"
    database.initialize(path)
    with database.connect(path) as db:
        indexes = {row["name"] for row in db.execute("PRAGMA index_list(monitor_checks)")}
    assert "idx_monitor_checks_checked_at" in indexes


def test_incident_api_reports_estimated_detection_and_recovery_duration(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monitor = database.create_monitor("Servicio", "tcp", "127.0.0.1:443", 60, 3)
    database.record_monitor_check(monitor["id"], "down", None, "No responde")
    database.record_monitor_check(monitor["id"], "up", 3.0, "Recuperado")
    incident = database.get_incidents(limit=10)[0]
    with database.connect() as db:
        db.execute(
            "UPDATE incidents SET opened_at = ?, resolved_at = ?, updated_at = ? WHERE id = ?",
            ("2026-10-11T10:00:00+00:00", "2026-10-11T10:12:34+00:00",
             "2026-10-11T10:12:34+00:00", incident["id"]),
        )
    data = database.get_incidents(limit=10)[0]
    assert data["duration_seconds"] == 754
    assert data["time_to_recovery_seconds"] == 754
    assert data["duration_is_estimated"] is True
    assert data["duration_basis"] == "first_failure_to_recovery_check"


def test_open_incident_reports_elapsed_detection_time_not_recovery(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monitor = database.create_monitor("Servicio activo", "tcp", "127.0.0.1:443", 60, 3)
    database.record_monitor_check(monitor["id"], "down", None, "No responde")
    with database.connect() as db:
        db.execute(
            "UPDATE incidents SET opened_at = ? WHERE monitor_id = ? AND status = 'open'",
            ("2026-10-11T10:00:00+00:00", monitor["id"]),
        )
    incident = database.get_incidents(limit=10)[0]
    assert incident["duration_seconds"] >= 0
    assert incident["time_to_recovery_seconds"] is None
    assert incident["duration_basis"] == "elapsed_since_first_failed_check"


def test_monitor_analytics_includes_average_recovery_time(tmp_path):
    path = tmp_path / "recovery-analytics.sqlite3"
    database.initialize(path)
    monitor = database.create_monitor("Servicio", "tcp", "127.0.0.1:443", 60, 3, path=path)
    failed = database.record_monitor_check(monitor["id"], "down", None, "Falló", path=path)
    database.record_monitor_check(monitor["id"], "up", 3.0, "Recuperado", path=path)
    from datetime import datetime, timedelta, timezone

    recovered_at = datetime.now(timezone.utc).replace(microsecond=0)
    opened_at = recovered_at - timedelta(seconds=120)
    with database.connect(path) as db:
        db.execute(
            "UPDATE incidents SET opened_at = ?, resolved_at = ?, updated_at = ? WHERE id = ?",
            (opened_at.isoformat(), recovered_at.isoformat(), recovered_at.isoformat(),
             failed["transition"]["incident_id"]),
        )
    summary = database.get_monitor_analytics(window_hours=168, path=path)["summary"]
    assert summary["incidents_resolved"] >= 1
    assert summary["average_recovery_seconds"] == 120
    assert summary["max_recovery_seconds"] == 120


def test_latency_trend_ui_has_accessible_chart_and_recovery_metrics(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        page = client.get("/monitors")
        css = client.get("/static/monitors.css")
        summary = client.get("/api/monitoring/summary?hours=168")
    assert page.status_code == 200
    assert "appendLatencyTrend" in page.text
    assert "latency-chart" in page.text
    assert "Recuperación media" in page.text
    assert ".latency-bar.up" in css.text
    assert summary.status_code == 200
    assert "average_recovery_seconds" in summary.json()["summary"]


def test_incident_csv_export_contains_durations_and_neutralizes_formulas(tmp_path):
    import csv
    import io

    path = tmp_path / "incident-export.sqlite3"
    database.initialize(path)
    monitor = database.create_monitor("=SUM(A1:A2)", "tcp", "127.0.0.1:443", 60, 3, path=path)
    failed = database.record_monitor_check(monitor["id"], "down", None, "Error", path=path)
    database.record_monitor_check(monitor["id"], "up", 4.0, "Recuperado", path=path)
    with database.connect(path) as db:
        db.execute(
            "UPDATE incidents SET opened_at = ?, resolved_at = ?, updated_at = ? WHERE id = ?",
            ("2026-10-11T10:00:00+00:00", "2026-10-11T10:05:00+00:00",
             "2026-10-11T10:05:00+00:00", failed["transition"]["incident_id"]),
        )
    output = database.export_incidents_csv(status="resolved", path=path)
    rows = list(csv.DictReader(io.StringIO(output.lstrip("\\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["monitor"] == "'=SUM(A1:A2)"
    assert rows[0]["estado"] == "resuelto"
    assert rows[0]["duracion_estimada_segundos"] == "300"
    assert rows[0]["tiempo_recuperacion_segundos"] == "300"
    open_rows = list(csv.DictReader(io.StringIO(database.export_incidents_csv(status="open", path=path).lstrip("\\ufeff"))))
    assert open_rows == []


def test_latency_history_aggregates_by_hour_and_six_hour_bucket(tmp_path):
    from datetime import datetime, timedelta, timezone

    path = tmp_path / "latency-trend.sqlite3"
    database.initialize(path)
    monitor = database.create_monitor("Latency", "tcp", "127.0.0.1:443", 60, 3, path=path)
    database.record_monitor_check(monitor["id"], "up", 12.0, "Correcto", path=path)
    database.record_monitor_check(monitor["id"], "up", 18.0, "Correcto", path=path)
    database.record_monitor_check(monitor["id"], "down", None, "Falló", path=path)
    recent = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    earlier = recent - timedelta(hours=30)
    with database.connect(path) as db:
        ids = [row["id"] for row in db.execute(
            "SELECT id FROM monitor_checks WHERE monitor_id = ? ORDER BY id", (monitor["id"],)
        )]
        db.execute("UPDATE monitor_checks SET checked_at = ? WHERE id = ?", (recent.isoformat(), ids[0]))
        db.execute("UPDATE monitor_checks SET checked_at = ? WHERE id = ?", (recent.isoformat(), ids[1]))
        db.execute("UPDATE monitor_checks SET checked_at = ? WHERE id = ?", (earlier.isoformat(), ids[2]))
    day = database.get_monitor_latency_trend(monitor["id"], window_hours=24, path=path)
    week = database.get_monitor_latency_trend(monitor["id"], window_hours=168, path=path)
    assert day["bucket_minutes"] == 60
    recent_points = [p for p in day["points"] if p["checks_total"]]
    assert len(recent_points) == 1
    assert recent_points[0]["checks_up"] == 2
    assert recent_points[0]["average_latency_ms"] == 15.0
    assert week["bucket_minutes"] == 360
    assert sum(p["checks_total"] for p in week["points"]) == 3
    assert database.get_monitor_latency_trend(9999, path=path) is None


def test_incident_and_latency_export_endpoints_are_no_store(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    monitor = database.create_monitor("Servicio", "tcp", "127.0.0.1:443", 60, 3)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        incidents = client.get("/api/export/incidents.csv")
        invalid = client.get("/api/export/incidents.csv?status=unknown")
        trend = client.get(f"/api/monitors/{monitor['id']}/latency?hours=168")
        export = client.get(f"/api/export/monitor-latency.csv?monitor_id={monitor['id']}&hours=168")
        missing = client.get("/api/monitors/9999/latency")
        missing_export = client.get("/api/export/monitor-latency.csv?monitor_id=9999")
    assert incidents.status_code == 200
    assert incidents.headers["cache-control"] == "no-store"
    assert "netsentinel-incidents.csv" in incidents.headers["content-disposition"]
    assert invalid.status_code == 422
    assert trend.status_code == 200
    assert trend.json()["bucket_minutes"] == 360
    assert export.status_code == 200
    assert export.headers["cache-control"] == "no-store"
    assert "inicio_bucket_utc" in export.text
    assert missing.status_code == 404
    assert missing_export.status_code == 404


def test_monitor_page_exposes_incident_filter_and_historical_latency_exports(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with TestClient(app, base_url="http://127.0.0.1") as client:
        page = client.get("/monitors")
        css = client.get("/static/monitors.css")
    assert page.status_code == 200
    assert 'id="incidentStatus"' in page.text
    assert 'id="incidentExport"' in page.text
    assert "appendHistoricalLatencyTrend" in page.text
    assert "/api/export/monitor-latency.csv" in page.text
    assert ".latency-history-bar" in css.text


def test_monitor_history_retention_config_is_safe_and_explicit(monkeypatch):
    monkeypatch.delenv("NETSENTINEL_MONITOR_HISTORY_DAYS", raising=False)
    assert monitor_history_retention_days() == DEFAULT_MONITOR_HISTORY_DAYS == 90

    monkeypatch.setenv("NETSENTINEL_MONITOR_HISTORY_DAYS", "30")
    assert monitor_history_retention_days() == 30

    for disabled in ("0", "off", "disabled", "none", "never"):
        monkeypatch.setenv("NETSENTINEL_MONITOR_HISTORY_DAYS", disabled)
        assert monitor_history_retention_days() is None

    # Invalid values preserve all samples rather than risk an unintended deletion.
    for invalid in ("invalid", "-1", "3651", "3.5"):
        monkeypatch.setenv("NETSENTINEL_MONITOR_HISTORY_DAYS", invalid)
        assert monitor_history_retention_days() is None


def test_monitor_history_cleanup_runs_no_more_than_daily(monkeypatch):
    cleaned = []
    monkeypatch.setenv("NETSENTINEL_MONITOR_HISTORY_DAYS", "30")
    monkeypatch.setattr(
        "netsentinel.monitoring.database.cleanup_monitor_history",
        lambda days: cleaned.append(days) or 4,
    )
    supervisor = MonitorSupervisor()

    assert supervisor.cleanup_history_if_due(now=100) == 4
    assert supervisor.cleanup_history_if_due(now=100 + 10) == 0
    assert supervisor.cleanup_history_if_due(now=100 + HISTORY_CLEANUP_INTERVAL_SECONDS - 1) == 0
    assert supervisor.cleanup_history_if_due(now=100 + HISTORY_CLEANUP_INTERVAL_SECONDS) == 4
    assert cleaned == [30, 30]
