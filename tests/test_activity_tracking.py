import csv
import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.discovery import Neighbor
from netsentinel.main import app


@pytest.fixture(autouse=True)
def disable_scheduler(monkeypatch):
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.20", "AA:BB:CC:DD:EE:91", "en0")])
    with TestClient(app, base_url="http://127.0.0.1") as test_client:
        yield test_client


def device_id(client):
    devices = client.get("/api/devices").json()
    assert devices
    return devices[0]["id"]


def test_activity_page_and_empty_state_are_available(client):
    page = client.get("/activity")
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    assert "Actividad y telemetría" in page.text
    assert "Previsualizar CSV" in page.text
    assert "Exportar CSV filtrado" in page.text
    assert "filterEventType" in page.text
    assert "filterSource" in page.text
    assert "deleteSource" in page.text
    assert "Previsualizar borrado" in page.text
    assert "confirmDeleteActivity" in page.text
    assert "no captura tráfico por sí mismo" in page.text
    assert "otros segmentos o parámetros desconocidos pueden seguir conteniendo datos personales" in page.text

    response = client.get("/api/activity")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["sessions"] == []
    assert payload["events"] == []
    assert payload["retention_days"] == 7
    assert "No se guardan credenciales" in payload["note"]
    assert "otros segmentos o parámetros no reconocidos pueden persistir" in payload["note"]
    assert "rutas ni URLs completas" not in payload["note"]


def test_session_accepts_valid_metadata_only_during_active_window(client):
    selected = device_id(client)
    session_response = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 30, "source_mode": "router_dns"},
    )
    assert session_response.status_code == 200
    session = session_response.json()
    assert session["status"] == "active"
    assert session["device_id"] == selected
    assert len(session["collector_token"]) >= 32
    public_sessions = client.get("/api/activity").json()["sessions"]
    assert "collector_token_hash" not in public_sessions[0]

    event_response = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"],
            "collector_token": session["collector_token"],
            "device_id": selected,
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "www.example.com.",
        },
    )
    assert event_response.status_code == 200
    event = event_response.json()
    assert event["domain"] == "www.example.com"
    assert event["source"] == "router_dns"
    assert "password" not in event
    assert client.get(f"/api/activity?device_id={selected}").json()["events"][0]["domain"] == "www.example.com"

    # Credentials or any unsupported fields must be rejected, not silently accepted.
    leaked = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"], "collector_token": session["collector_token"],
            "device_id": selected, "event_type": "dns_query", "source": "router_dns",
            "domain": "example.com", "password": "must-not-be-accepted",
        },
    )
    assert leaked.status_code == 422

    bad_token = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"], "collector_token": "x" * 40,
            "device_id": selected, "event_type": "dns_query",
            "source": "router_dns", "domain": "example.com",
        },
    )
    assert bad_token.status_code == 403


def test_live_ingest_rejects_events_outside_configured_retention(client):
    selected = device_id(client)
    retention = client.put("/api/activity/retention", json={"retention_days": 1})
    assert retention.status_code == 200

    session = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 30, "source_mode": "router_dns"},
    ).json()
    old_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds")
    response = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"],
            "collector_token": session["collector_token"],
            "device_id": selected,
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "delayed.example",
            "observed_at": old_timestamp,
        },
    )

    assert response.status_code == 422
    assert "retención configurada de 1 día(s)" in response.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


def test_ingest_rejects_wrong_source_unknown_session_and_inactive_session(client):
    selected = device_id(client)
    session = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 15, "source_mode": "router_dns"},
    ).json()
    event = {
        "session_id": session["id"], "collector_token": session["collector_token"],
        "device_id": selected, "event_type": "dns_query", "source": "device_agent", "domain": "example.com",
    }
    assert client.post("/api/activity/ingest", json=event).status_code == 422

    assert client.post(
        "/api/activity/ingest",
        json={**event, "session_id": 9999, "source": "router_dns"},
    ).status_code == 404

    stopped = client.post(f"/api/activity/sessions/{session['id']}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "stopped"
    assert client.post(
        "/api/activity/ingest",
        json={**event, "source": "router_dns"},
    ).status_code == 409


@pytest.mark.parametrize("domain", ["https://example.com/login", "example.com/account", "user@example.com", "192.0.2.1"])
def test_dns_event_rejects_urls_paths_addresses_and_userinfo(client, domain):
    selected = device_id(client)
    session = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 15, "source_mode": "router_dns"},
    ).json()
    response = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"], "collector_token": session["collector_token"],
            "device_id": selected, "event_type": "dns_query", "source": "router_dns", "domain": domain,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", ["/api/activity/import", "/api/activity/import/preview"])
def test_csv_import_rejects_more_than_1000_rows_before_writing(client, endpoint):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = ["observed_at,event_type,domain"]
    rows.extend(f"{stamp},dns_query,host-{index}.example" for index in range(1001))
    response = client.post(endpoint, json={"device_id": selected, "csv_data": "\n".join(rows) + "\n"})

    assert response.status_code == 422
    assert "1000" in response.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


@pytest.mark.parametrize("endpoint", ["/api/activity/import", "/api/activity/import/preview"])
def test_csv_import_returns_validation_error_for_oversized_field(client, endpoint):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    oversized_value = "x" * 140_000  # Above csv's default per-field parser limit, below the 1 MB API cap.
    csv_data = f"observed_at,event_type,app_name\n{stamp},app_usage,{oversized_value}\n"

    response = client.post(endpoint, json={"device_id": selected, "csv_data": csv_data})

    assert response.status_code == 422
    assert "CSV" in response.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


def test_csv_import_and_rejects_sensitive_columns(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "observed_at,event_type,domain,destination_ip,destination_port,protocol,app_name,blocked\n"
        f"{stamp},dns_query,example.com,,,,,false\n"
    )
    imported = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    payload = client.get(f"/api/activity?device_id={selected}").json()
    assert payload["events"][0]["source"] == "manual_import"
    assert payload["events"][0]["domain"] == "example.com"

    forbidden = (
        "observed_at,event_type,domain,password\n"
        f"{stamp},dns_query,example.com,guessme\n"
    )
    rejected = client.post("/api/activity/import", json={"device_id": selected, "csv_data": forbidden})
    assert rejected.status_code == 422
    assert "privacidad" in rejected.json()["detail"].lower()


def test_csv_import_is_idempotent_and_skips_duplicate_rows(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = f"""observed_at,event_type,domain
{stamp},dns_query,duplicate.example
{stamp},dns_query,duplicate.example
"""

    first = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert first.status_code == 200, first.text
    assert first.json()["imported"] == 1
    assert first.json()["skipped_duplicates"] == 1

    second = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert second.status_code == 200, second.text
    assert second.json()["imported"] == 0
    assert second.json()["skipped_duplicates"] == 2

    events = client.get(f"/api/activity?device_id={selected}").json()["events"]
    assert sum(event["domain"] == "duplicate.example" for event in events) == 1


def test_csv_preview_is_read_only_and_reports_deduplicated_rows(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = f"""observed_at,event_type,domain
{stamp},dns_query,preview.example
{stamp},dns_query,preview.example
"""

    preview = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["valid_rows"] == 2
    assert result["would_import"] == 1
    assert result["skipped_duplicates"] == 1
    assert [row["disposition"] for row in result["preview_rows"]] == ["new", "duplicate"]
    assert "no se guardó" in result["note"].lower()
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []

    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1
    assert imported.json()["skipped_duplicates"] == 1

    second_preview = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert second_preview.status_code == 200, second_preview.text
    assert second_preview.json()["would_import"] == 0
    assert second_preview.json()["skipped_duplicates"] == 2
    assert all(row["disposition"] == "duplicate" for row in second_preview.json()["preview_rows"])


def test_csv_preview_shows_server_sanitized_url_without_storing_event(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "observed_at,event_type,page_url\n"
        f'{stamp},page_visit,"https://example.com/docs?lang=es&access_token=secret&utm_source=private#hidden"\n'
    )
    response = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert response.status_code == 200, response.text
    row = response.json()["preview_rows"][0]
    assert row["page_url"] == "https://example.com/docs?lang=es"
    assert row["disposition"] == "new"
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


def test_csv_preview_rejects_message_content_and_unknown_columns(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    unsafe = f"""observed_at,event_type,domain,email_body
{stamp},email_metadata,example.com,PRIVATE BODY
"""
    response = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": unsafe},
    )
    assert response.status_code == 422
    assert "privacidad" in response.json()["detail"].lower()
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


def test_browser_csv_import_captures_page_urls_and_search_queries_safely(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "observed_at,event_type,domain,app_name,blocked,page_url,search_engine,search_terms\n"
        f'{stamp},page_visit,example.com,browser-extension,false,"https://example.com/docs?lang=es&access_token=secret#private",,\n'
        f'{stamp},search_query,www.google.com,browser-extension,false,https://www.google.com/search,Google,"cómo ayudar a menores"\n'
    )
    result = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert result.status_code == 200, result.text
    events = client.get(f"/api/activity?device_id={selected}").json()["events"]
    page = next(event for event in events if event["event_type"] == "page_visit")
    search = next(event for event in events if event["event_type"] == "search_query")
    assert page["page_url"] == "https://example.com/docs?lang=es"
    assert "secret" not in page["page_url"]
    assert "private" not in page["page_url"]
    assert search["search_engine"] == "Google"
    assert search["search_terms"] == "cómo ayudar a menores"


def test_browser_event_url_validation_and_search_required_fields(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    invalid_url_csv = (
        "observed_at,event_type,page_url\n"
        f'{stamp},page_visit,"javascript:alert(1)"\n'
    )
    bad = client.post("/api/activity/import", json={"device_id": selected, "csv_data": invalid_url_csv})
    assert bad.status_code == 422

    missing_terms_csv = (
        "observed_at,event_type,search_engine,search_terms\n"
        f"{stamp},search_query,Google,\n"
    )
    missing = client.post("/api/activity/import", json={"device_id": selected, "csv_data": missing_terms_csv})
    assert missing.status_code == 422


def test_legacy_activity_event_schema_migrates_without_losing_events(monkeypatch, tmp_path):
    from netsentinel.database import connect

    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([Neighbor("192.168.5.90", "AA:BB:CC:DD:EE:90", "en0")])
    device = database.list_devices()[0]
    stamp = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        db.execute("DROP TABLE activity_events")
        db.execute("""
            CREATE TABLE activity_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES activity_sessions(id) ON DELETE SET NULL,
                device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                observed_at TEXT NOT NULL, received_at TEXT NOT NULL,
                event_type TEXT NOT NULL CHECK (event_type IN ('dns_query','connection','tls_sni','app_usage','blocked')),
                source TEXT NOT NULL CHECK (source IN ('router_dns','router_flow','device_agent','manual_import')),
                domain TEXT, destination_ip TEXT,
                destination_port INTEGER, protocol TEXT, app_name TEXT,
                blocked INTEGER NOT NULL DEFAULT 0
            )
        """)
        db.execute(
            """INSERT INTO activity_events
               (device_id, observed_at, received_at, event_type, source, domain)
               VALUES (?, ?, ?, 'dns_query', 'manual_import', 'legacy.example')""",
            (device["id"], stamp, stamp),
        )
    database.initialize()
    with connect() as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(activity_events)")}
        event = db.execute("SELECT * FROM activity_events WHERE domain='legacy.example'").fetchone()
    assert {"page_url", "search_engine", "search_terms", "email_provider", "email_from", "email_to", "email_subject"}.issubset(columns)
    assert event is not None
    assert event["event_type"] == "dns_query"


def test_email_metadata_import_stores_only_sender_recipient_subject(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "observed_at,event_type,email_provider,email_from,email_to,email_subject\n"
        f'{stamp},email_metadata,Gmail,"Parent <parent@example.com>","Child <child@example.com>","Pedido de ayuda"\n'
    )
    response = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert response.status_code == 200, response.text
    event = client.get(f"/api/activity?device_id={selected}").json()["events"][0]
    assert event["event_type"] == "email_metadata"
    assert event["email_provider"] == "Gmail"
    assert event["email_from"] == "parent@example.com"
    assert event["email_to"] == "child@example.com"
    assert event["email_subject"] == "Pedido de ayuda"
    assert "email_body" not in event and "message" not in event


@pytest.mark.parametrize("header", ["message", "email_body", "body_text", "body_html", "content", "attachments", "attachment_content"])
def test_email_message_body_or_attachment_columns_are_rejected(client, header):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = f"observed_at,event_type,email_provider,email_from,email_to,{header}\n{stamp},email_metadata,Gmail,a@example.com,b@example.com,PRIVATE\n"
    response = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert response.status_code == 422
    assert "privacidad" in response.json()["detail"].lower()


def test_microsoft_message_trace_csv_aliases_import_metadata(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "receivedDateTime,senderAddress,recipientAddress,subject,status,messageId,size\n"
        f'{stamp},parent@example.com,child@example.com,"Consulta escolar",Delivered,"<abc@example.com>",3456\n'
    )
    response = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert response.status_code == 200, response.text
    event = client.get(f"/api/activity?device_id={selected}").json()["events"][0]
    assert event["event_type"] == "email_metadata"
    assert event["email_provider"] == "Microsoft 365"
    assert event["email_from"] == "parent@example.com"
    assert event["email_to"] == "child@example.com"
    assert event["email_subject"] == "Consulta escolar"


def test_google_workspace_email_log_csv_aliases_import_metadata(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    csv_data = (
        "Subject or Message ID,Date,Sender,Recipient\n"
        f'"Consulta de tarea",{stamp},parent@example.com,child@example.com\n'
    )
    response = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert response.status_code == 200, response.text
    event = client.get(f"/api/activity?device_id={selected}").json()["events"][0]
    assert event["event_type"] == "email_metadata"
    assert event["email_provider"] == "Google Workspace"
    assert event["email_from"] == "parent@example.com"
    assert event["email_to"] == "child@example.com"
    assert event["email_subject"] == "Consulta de tarea"


def test_email_metadata_cannot_be_live_ingested(client):
    selected = device_id(client)
    session = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 15, "source_mode": "device_agent"},
    ).json()
    response = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"], "collector_token": session["collector_token"],
            "device_id": selected, "event_type": "email_metadata", "source": "device_agent",
            "email_from": "a@example.com", "email_to": "b@example.com", "email_subject": "Example",
        },
    )
    assert response.status_code == 422


def test_retention_is_configurable_and_deletes_expired_events(client):
    selected = device_id(client)
    old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    csv_data = (
        "observed_at,event_type,domain\n"
        f"{old},dns_query,old.example\n"
    )
    imported = client.post("/api/activity/import", json={"device_id": selected, "csv_data": csv_data})
    assert imported.status_code == 200
    response = client.put("/api/activity/retention", json={"retention_days": 1})
    assert response.status_code == 200
    assert response.json()["retention_days"] == 1
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []


def test_limits_unknown_device_and_invalid_retention(client):
    assert client.get("/api/activity?device_id=99999").status_code == 404
    assert client.post(
        "/api/activity/sessions",
        json={"device_id": 99999, "duration_minutes": 15, "source_mode": "router_dns"},
    ).status_code == 404
    assert client.put("/api/activity/retention", json={"retention_days": 365}).status_code == 422
    assert client.post(
        "/api/activity/sessions",
        json={"device_id": device_id(client), "duration_minutes": 721, "source_mode": "router_dns"},
    ).status_code == 422


def test_activity_filters_by_type_and_inclusive_utc_dates(client):
    selected = device_id(client)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    old = (now - timedelta(days=2)).isoformat()
    today = now.isoformat()
    csv_data = f"""observed_at,event_type,domain,search_engine,search_terms
{old},dns_query,old.example,,
{today},dns_query,today.example,,
{today},search_query,www.google.com,Google,=1+1
"""
    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 200, imported.text

    today_filter = client.get(
        "/api/activity",
        params={
            "device_id": selected,
            "event_type": "dns_query",
            "from_date": now.date().isoformat(),
            "to_date": now.date().isoformat(),
            "limit": 500,
        },
    )
    assert today_filter.status_code == 200, today_filter.text
    events = today_filter.json()["events"]
    assert [event["domain"] for event in events] == ["today.example"]

    invalid_range = client.get(
        "/api/activity",
        params={
            "from_date": now.date().isoformat(),
            "to_date": (now.date() - timedelta(days=1)).isoformat(),
        },
    )
    assert invalid_range.status_code == 422


def test_activity_csv_export_respects_filters_and_neutralizes_formulas(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    csv_data = f"""observed_at,event_type,domain,search_engine,search_terms
{stamp},dns_query,ordinary.example,,
{stamp},search_query,www.google.com,Google,=1+1
"""
    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 200, imported.text

    response = client.get(
        "/api/activity/export.csv",
        params={"device_id": selected, "event_type": "search_query"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("text/csv")
    payload = response.text.lstrip("\ufeff")
    rows = list(csv.DictReader(io.StringIO(payload)))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "search_query"
    assert rows[0]["search_terms"] == "'=1+1"
    assert "ordinary.example" not in payload

    missing = client.get("/api/activity/export.csv", params={"device_id": 99999})
    assert missing.status_code == 404


def test_activity_delete_preview_is_read_only_and_delete_requires_exact_count(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    csv_data = f"""observed_at,event_type,domain,search_engine,search_terms
{stamp},dns_query,first.example,,
{stamp},dns_query,second.example,,
{stamp},search_query,www.google.com,Google,weather
"""
    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 3

    unscoped = client.post("/api/activity/delete/preview", json={})
    assert unscoped.status_code == 422

    preview = client.post(
        "/api/activity/delete/preview",
        json={"device_id": selected, "event_type": "dns_query"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["matching_events"] == 2
    assert preview.json()["confirmation_required"] == "BORRAR 2"
    assert preview.json()["deleted"] is False
    assert "no se borró" in preview.json()["note"].lower()
    before = client.get(f"/api/activity?device_id={selected}").json()["events"]
    assert len(before) == 3

    wrong_confirmation = client.post(
        "/api/activity/delete",
        json={"device_id": selected, "event_type": "dns_query", "confirmation": "BORRAR 1"},
    )
    assert wrong_confirmation.status_code == 409
    assert len(client.get(f"/api/activity?device_id={selected}").json()["events"]) == 3

    deleted = client.post(
        "/api/activity/delete",
        json={"device_id": selected, "event_type": "dns_query", "confirmation": "BORRAR 2"},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_events"] == 2
    remaining = client.get(f"/api/activity?device_id={selected}").json()["events"]
    assert len(remaining) == 1
    assert remaining[0]["event_type"] == "search_query"


def test_activity_delete_preview_validates_device_and_event_type(client):
    selected = device_id(client)
    missing = client.post(
        "/api/activity/delete/preview",
        json={"device_id": 99999, "event_type": "dns_query"},
    )
    assert missing.status_code == 404
    invalid_type = client.post(
        "/api/activity/delete/preview",
        json={"device_id": selected, "event_type": "email_body"},
    )
    assert invalid_type.status_code == 422


def test_activity_source_filters_export_and_selective_delete(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    imported = client.post(
        "/api/activity/import",
        json={
            "device_id": selected,
            "csv_data": f"""observed_at,event_type,domain
{stamp},dns_query,manual.example
""",
        },
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["imported"] == 1

    session = client.post(
        "/api/activity/sessions",
        json={"device_id": selected, "duration_minutes": 30, "source_mode": "router_dns"},
    ).json()
    ingested = client.post(
        "/api/activity/ingest",
        json={
            "session_id": session["id"],
            "collector_token": session["collector_token"],
            "device_id": selected,
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "router.example",
        },
    )
    assert ingested.status_code == 200, ingested.text

    manual_events = client.get(
        "/api/activity",
        params={"device_id": selected, "source": "manual_import"},
    )
    assert manual_events.status_code == 200, manual_events.text
    assert [event["domain"] for event in manual_events.json()["events"]] == ["manual.example"]

    router_events = client.get(
        "/api/activity",
        params={"device_id": selected, "source": "router_dns"},
    )
    assert router_events.status_code == 200, router_events.text
    assert [event["domain"] for event in router_events.json()["events"]] == ["router.example"]
    assert "manual_import" in router_events.json()["activity_sources"]

    invalid_source = client.get(
        "/api/activity",
        params={"device_id": selected, "source": "unknown_source"},
    )
    assert invalid_source.status_code == 422

    exported = client.get(
        "/api/activity/export.csv",
        params={"device_id": selected, "source": "manual_import"},
    )
    assert exported.status_code == 200, exported.text
    rows = list(csv.DictReader(io.StringIO(exported.text.lstrip("\ufeff"))))
    assert len(rows) == 1
    assert rows[0]["source"] == "manual_import"
    assert rows[0]["domain"] == "manual.example"

    preview = client.post(
        "/api/activity/delete/preview",
        json={"device_id": selected, "source": "manual_import"},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["matching_events"] == 1
    assert preview.json()["source"] == "manual_import"

    deleted = client.post(
        "/api/activity/delete",
        json={
            "device_id": selected,
            "source": "manual_import",
            "confirmation": "BORRAR 1",
        },
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted_events"] == 1

    remaining = client.get(f"/api/activity?device_id={selected}").json()["events"]
    assert len(remaining) == 1
    assert remaining[0]["source"] == "router_dns"
    assert remaining[0]["domain"] == "router.example"


def test_metadata_events_are_included_in_json_export(client):
    selected = device_id(client)
    stamp = datetime.now(timezone.utc).isoformat()
    imported = client.post(
        "/api/activity/import",
        json={
            "device_id": selected,
            "csv_data": "observed_at,event_type,domain\n" + f"{stamp},dns_query,example.com\n",
        },
    )
    assert imported.status_code == 200
    response = client.get("/api/export/data.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "netsentinel-data-export-v4"
    assert payload["activity_events"][0]["domain"] == "example.com"
    assert payload["activity_settings"][0]["retention_days"] == 7



def test_csv_import_rejects_rows_outside_retention_until_policy_is_extended(client):
    selected = device_id(client)
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="seconds")
    csv_data = "observed_at,event_type,domain\n" + f"{old},dns_query,old.example\n"

    preview = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert preview.status_code == 422
    assert "retención configurada de 7 día(s)" in preview.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []

    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 422
    assert "Aumentá la retención antes de importar" in imported.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []

    retention = client.put("/api/activity/retention", json={"retention_days": 30})
    assert retention.status_code == 200
    preview = client.post(
        "/api/activity/import/preview",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert preview.status_code == 200
    assert preview.json()["would_import"] == 1

    imported = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    events = client.get(f"/api/activity?device_id={selected}").json()["events"]
    assert any(event["domain"] == "old.example" for event in events)


def test_csv_import_rejects_entire_batch_if_any_row_is_expired(client):
    selected = device_id(client)
    current = datetime.now(timezone.utc).replace(microsecond=0)
    old = (current - timedelta(days=8)).isoformat()
    recent = current.isoformat()
    csv_data = (
        "observed_at,event_type,domain\n"
        f"{recent},dns_query,recent.example\n"
        f"{old},dns_query,old.example\n"
    )

    response = client.post(
        "/api/activity/import",
        json={"device_id": selected, "csv_data": csv_data},
    )
    assert response.status_code == 422
    assert "Fila 3" in response.json()["detail"]
    assert client.get(f"/api/activity?device_id={selected}").json()["events"] == []
