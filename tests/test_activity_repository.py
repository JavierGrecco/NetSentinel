from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
