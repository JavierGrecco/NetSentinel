from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from netsentinel import activity_repository, database


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def test_retention_update_cleans_events_and_expires_old_sessions(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

    with database.connect() as db:
        device_id = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, first_seen, last_seen, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            ("AA:BB:CC:DD:EE:91", "192.168.5.20", _iso(now), _iso(now), "Test device"),
        ).lastrowid

        active_session_id = db.execute(
            """INSERT INTO activity_sessions
               (device_id, source_mode, started_at, ends_at, status, collector_token_hash)
               VALUES (?, 'router_dns', ?, ?, 'active', ?)""",
            (device_id, _iso(now - timedelta(hours=1)), _iso(now - timedelta(minutes=1)), "hash"),
        ).lastrowid
        stale_session_id = db.execute(
            """INSERT INTO activity_sessions
               (device_id, source_mode, started_at, ends_at, stopped_at, status, collector_token_hash)
               VALUES (?, 'router_dns', ?, ?, ?, 'stopped', ?)""",
            (
                device_id,
                _iso(now - timedelta(days=100)),
                _iso(now - timedelta(days=91)),
                _iso(now - timedelta(days=91)),
                "old-hash",
            ),
        ).lastrowid

        for observed_at, domain in (
            (now - timedelta(days=10), "old.example"),
            (now - timedelta(days=1), "recent.example"),
        ):
            db.execute(
                """INSERT INTO activity_events
                   (session_id, device_id, observed_at, received_at, event_type, source, domain)
                   VALUES (?, ?, ?, ?, 'dns_query', 'router_dns', ?)""",
                (active_session_id, device_id, _iso(observed_at), _iso(now), domain),
            )

    result = activity_repository.update_retention(2, now=now)

    assert result == {"retention_days": 2, "deleted_events": 1}
    with database.connect() as db:
        domains = {
            row["domain"]
            for row in db.execute("SELECT domain FROM activity_events").fetchall()
        }
        active_session = db.execute(
            "SELECT status FROM activity_sessions WHERE id = ?",
            (active_session_id,),
        ).fetchone()
        stale_session = db.execute(
            "SELECT id FROM activity_sessions WHERE id = ?",
            (stale_session_id,),
        ).fetchone()

    assert domains == {"recent.example"}
    assert active_session["status"] == "expired"
    assert stale_session is None


def test_missing_retention_row_uses_legacy_default(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with database.connect() as db:
        db.execute("DELETE FROM activity_settings")
        assert activity_repository.get_retention_days(db) == 7


def test_retention_update_restores_a_missing_setting_row(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    with database.connect() as db:
        db.execute("DELETE FROM activity_settings")

    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    result = activity_repository.update_retention(2, now=now)

    assert result == {"retention_days": 2, "deleted_events": 0}
    with database.connect() as db:
        assert activity_repository.get_retention_days(db) == 2
        assert db.execute("SELECT COUNT(*) FROM activity_settings").fetchone()[0] == 1


def _insert_device(db, now: datetime) -> int:
    return db.execute(
        """INSERT INTO devices
           (mac_address, ip_address, first_seen, last_seen, display_name)
           VALUES (?, ?, ?, ?, ?)""",
        ("AA:BB:CC:DD:EE:92", "192.168.5.21", _iso(now), _iso(now), "Repository test"),
    ).lastrowid


def test_session_repository_replaces_active_session_and_stop_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    now_text = _iso(now)

    with database.connect() as db:
        device_id = _insert_device(db, now)
        first = activity_repository.start_session(
            db, device_id=device_id, source_mode="router_dns",
            started_at=now_text, ends_at=_iso(now + timedelta(minutes=30)),
            token_hash="hash-one",
        )
        second_started = now + timedelta(minutes=1)
        second = activity_repository.start_session(
            db, device_id=device_id, source_mode="device_agent",
            started_at=_iso(second_started), ends_at=_iso(second_started + timedelta(minutes=30)),
            token_hash="hash-two",
        )

        first_current = activity_repository.get_session_for_device(db, first["id"], device_id)
        assert first_current is not None
        assert first_current["status"] == "stopped"
        assert first_current["stopped_at"] == _iso(second_started)
        second_current = activity_repository.get_session_for_device(db, second["id"], device_id)
        assert second_current is not None and second_current["status"] == "active"
        assert activity_repository.get_session_for_device(db, second["id"], device_id + 1) is None

        stopped = activity_repository.stop_session(db, second["id"], now=_iso(now + timedelta(minutes=2)))
        stopped_again = activity_repository.stop_session(db, second["id"], now=_iso(now + timedelta(minutes=3)))
        assert stopped is not None and stopped["status"] == "stopped"
        assert stopped_again is not None
        assert stopped_again["stopped_at"] == _iso(now + timedelta(minutes=2))
        assert activity_repository.stop_session(db, 99999, now=now_text) is None


def test_event_repository_inserts_validated_metadata(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    now_text = _iso(now)

    with database.connect() as db:
        device_id = _insert_device(db, now)
        session = activity_repository.start_session(
            db, device_id=device_id, source_mode="router_dns",
            started_at=now_text, ends_at=_iso(now + timedelta(minutes=30)),
            token_hash="only-the-hash-is-stored",
        )
        event = {
            "observed_at": now_text, "event_type": "dns_query", "source": "router_dns",
            "domain": "example.com", "destination_ip": None, "destination_port": None,
            "protocol": None, "app_name": None, "page_url": None, "search_engine": None,
            "search_terms": None, "email_provider": None, "email_from": None,
            "email_to": None, "email_subject": None, "blocked": 0,
        }
        inserted = activity_repository.insert_event(
            db, session["id"], device_id, event, received_at=now_text
        )

    assert inserted["session_id"] == session["id"]
    assert inserted["device_id"] == device_id
    assert inserted["event_type"] == "dns_query"
    assert inserted["source"] == "router_dns"
    assert inserted["domain"] == "example.com"
    assert "collector_token_hash" not in inserted


def test_activity_scope_repository_checks_bounds_and_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    now_text = _iso(now)

    with database.connect() as db:
        device_id = _insert_device(db, now)
        event = {
            "observed_at": now_text, "event_type": "dns_query", "source": "manual_import",
            "domain": "example.com", "destination_ip": None, "destination_port": None,
            "protocol": None, "app_name": None, "page_url": None, "search_engine": None,
            "search_terms": None, "email_provider": None, "email_from": None,
            "email_to": None, "email_subject": None, "blocked": 0,
        }
        activity_repository.insert_event(db, None, device_id, event, received_at=now_text)
        activity_repository.insert_event(db, None, device_id, event, received_at=now_text)

    where_sql = " WHERE device_id = ? AND event_type = ?"
    params = (device_id, "dns_query")
    assert activity_repository.count_activity_scope(
        where_sql, params, device_id=device_id
    ) == 2

    for unbounded_sql in ("", " WHERE 1=1", " WHERE device_id = ? OR 1=1"):
        with pytest.raises(ValueError, match="alcance explícito"):
            activity_repository.count_activity_scope(unbounded_sql, ())

        with pytest.raises(ValueError, match="alcance explícito"):
            activity_repository.delete_activity_scope(
                unbounded_sql, (), device_id=device_id, confirmation="BORRAR 2"
            )

    with pytest.raises(LookupError, match="No se encontró el dispositivo"):
        activity_repository.count_activity_scope(
            where_sql, (device_id + 9999, "dns_query"), device_id=device_id + 9999
        )

    with pytest.raises(PermissionError, match="No se borró nada"):
        activity_repository.delete_activity_scope(
            where_sql, params, device_id=device_id, confirmation="BORRAR 1"
        )
    # A stale or incorrect confirmation must never partially delete rows.
    assert activity_repository.count_activity_scope(
        where_sql, params, device_id=device_id
    ) == 2

    assert activity_repository.delete_activity_scope(
        where_sql, params, device_id=device_id, confirmation="BORRAR 2"
    ) == 2
    assert activity_repository.count_activity_scope(
        where_sql, params, device_id=device_id
    ) == 0



def _manual_event(now: datetime, domain: str) -> dict:
    """Crea un evento ya normalizado para probar la frontera de persistencia."""
    return {
        "observed_at": _iso(now),
        "event_type": "dns_query",
        "source": "manual_import",
        "domain": domain,
        "destination_ip": None,
        "destination_port": None,
        "protocol": None,
        "app_name": None,
        "page_url": None,
        "search_engine": None,
        "search_terms": None,
        "email_provider": None,
        "email_from": None,
        "email_to": None,
        "email_subject": None,
        "blocked": 0,
    }


def test_manual_import_repository_keeps_preview_read_only_and_deduplicates(monkeypatch, tmp_path):
    """La previsualización no escribe y una importación repetida no duplica datos."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)

    with database.connect() as db:
        device_id = _insert_device(db, now)

    events = [_manual_event(now, "csv.example")]
    lines = [2]
    activity_repository.require_device_exists(device_id)
    preview = activity_repository.import_manual_events(
        device_id, events, lines, now=now, preview=True
    )
    assert preview == {
        "imported": 1,
        "skipped_duplicates": 0,
        "preview_dispositions": ["new"],
    }
    with database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0] == 0

    first = activity_repository.import_manual_events(
        device_id, events, lines, now=now, preview=False
    )
    duplicate = activity_repository.import_manual_events(
        device_id, events, lines, now=now, preview=False
    )
    assert first["imported"] == 1
    assert first["skipped_duplicates"] == 0
    assert duplicate["imported"] == 0
    assert duplicate["skipped_duplicates"] == 1
    with database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0] == 1
        assert db.execute("SELECT import_format FROM activity_events").fetchone()[0] == "csv"


def test_manual_import_repository_rejects_old_rows_before_writing(monkeypatch, tmp_path):
    """Un lote fuera de retención se rechaza completo, sin inserciones parciales."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    with database.connect() as db:
        device_id = _insert_device(db, now)
        db.execute("UPDATE activity_settings SET retention_days = 2 WHERE id = 1")

    events = [_manual_event(now - timedelta(days=1), "recent.example"),
              _manual_event(now - timedelta(days=3), "expired.example")]
    with pytest.raises(ValueError, match="fuera de la retención configurada"):
        activity_repository.import_manual_events(
            device_id, events, [2, 3], now=now, preview=False
        )

    with database.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0] == 0


def test_activity_read_repository_validates_filters_and_preserves_summary_scope(
    monkeypatch, tmp_path
):
    """Las lecturas solo aceptan filtros permitidos y no cambian el contrato de resúmenes."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_text = _iso(now)

    with database.connect() as db:
        device_id = _insert_device(db, now)
        dns_event = _manual_event(now, "dns.example")
        search_event = _manual_event(now, "search.example")
        search_event.update(
            event_type="search_query",
            search_engine="Google",
            search_terms="weather",
        )
        activity_repository.insert_event(
            db, None, device_id, dns_event, received_at=now_text
        )
        activity_repository.insert_event(
            db, None, device_id, search_event, received_at=now_text
        )

    snapshot = activity_repository.get_activity_snapshot(
        device_id=device_id,
        event_filter="WHERE event_type = ?",
        event_params=("dns_query",),
        limit=100,
    )
    assert [event["event_type"] for event in snapshot["events"]] == ["dns_query"]
    # La API documenta que los filtros afectan a la lista, no a los indicadores globales.
    assert snapshot["total_events"] == 2
    assert {item["domain"] for item in snapshot["top_domains"]} == {
        "dns.example", "search.example"
    }

    exported = activity_repository.get_activity_export_rows(
        where_sql=" WHERE e.device_id = ?",
        params=(device_id,),
        device_id=device_id,
        limit=100,
    )
    assert len(exported) == 2

    with pytest.raises(ValueError, match="filtros de lectura"):
        activity_repository.get_activity_snapshot(
            device_id=device_id,
            event_filter="WHERE 1=1",
            event_params=(),
            limit=100,
        )
    with pytest.raises(ValueError, match="no coinciden"):
        activity_repository.get_activity_export_rows(
            where_sql="",
            params=(device_id,),
            device_id=device_id,
            limit=100,
        )

def test_manual_import_deduplicates_by_source_event_id_when_metadata_changes(
    monkeypatch, tmp_path
):
    """Un identificador estable de origen evita duplicados con campos enriquecidos."""
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    with database.connect() as db:
        device_id = _insert_device(db, now)

    first_event = _manual_event(now, "dns.example")
    first_event.update(source_event_id="router-row-42", bytes_sent=120)
    first = activity_repository.import_manual_events(
        device_id, [first_event], [2], now=now, preview=False
    )
    assert first["imported"] == 1

    # The same provider record is exported again with a more complete domain/counter.
    enriched_event = {
        **first_event,
        "domain": "dns-enriched.example",
        "bytes_sent": 240,
    }
    preview = activity_repository.import_manual_events(
        device_id, [enriched_event], [2], now=now, preview=True
    )
    assert preview["imported"] == 0
    assert preview["skipped_duplicates"] == 1
    assert preview["preview_dispositions"] == ["duplicate"]

    duplicate = activity_repository.import_manual_events(
        device_id, [enriched_event], [2], now=now, preview=False
    )
    assert duplicate["imported"] == 0
    assert duplicate["skipped_duplicates"] == 1
    with database.connect() as db:
        rows = db.execute(
            "SELECT source_event_id, domain, bytes_sent FROM activity_events WHERE device_id = ?",
            (device_id,),
        ).fetchall()
    assert [dict(row) for row in rows] == [{
        "source_event_id": "router-row-42",
        "domain": "dns.example",
        "bytes_sent": 120,
    }]
