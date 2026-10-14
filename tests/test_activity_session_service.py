"""Pruebas directas del ciclo de vida de sesiones de actividad."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest

from netsentinel import activity_session_service, database
from netsentinel.activity_session_service import InvalidCollectorToken


def _create_device() -> int:
    """Inserta un dispositivo mínimo aislado para las pruebas."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database.connect() as db:
        cursor = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, first_seen, last_seen, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            ("AA:BB:CC:DD:EE:A1", "192.0.2.40", now, now, "Session test device"),
        )
        return int(cursor.lastrowid)


def test_session_service_stores_only_token_hash_and_accepts_valid_event(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    device_id = _create_device()

    session = activity_session_service.start_session(device_id, 30, " ROUTER_DNS ")
    token = session["collector_token"]
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert len(token) >= 32
    assert session["source_mode"] == "router_dns"
    assert "collector_token_hash" not in session

    with database.connect() as db:
        stored = db.execute(
            "SELECT collector_token_hash FROM activity_sessions WHERE id = ?",
            (session["id"],),
        ).fetchone()
    assert stored["collector_token_hash"] == token_hash
    assert token not in stored["collector_token_hash"]

    event = activity_session_service.ingest_event(
        session["id"],
        device_id,
        token,
        {
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "example.test",
        },
    )
    assert event["event_type"] == "dns_query"
    assert event["domain"] == "example.test"

    with pytest.raises(InvalidCollectorToken, match="token de recopilación"):
        activity_session_service.ingest_event(
            session["id"],
            device_id,
            "wrong-token-" + ("x" * 40),
            {
                "event_type": "dns_query",
                "source": "router_dns",
                "domain": "example.test",
            },
        )


@pytest.mark.parametrize(
    ("duration", "source", "message"),
    [
        (4, "router_dns", "duración"),
        (721, "router_dns", "duración"),
        (30, "unknown", "Fuente elegible"),
        (30, None, "Fuente elegible"),
    ],
)
def test_session_service_rejects_invalid_session_parameters(
    duration, source, message
):
    with pytest.raises(ValueError, match=message):
        activity_session_service.start_session(1, duration, source)


def test_stopped_session_refuses_new_events(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    device_id = _create_device()
    session = activity_session_service.start_session(device_id, 30, "router_dns")
    assert activity_session_service.stop_session(session["id"])["status"] == "stopped"

    with pytest.raises(PermissionError, match="sesión no está activa"):
        activity_session_service.ingest_event(
            session["id"],
            device_id,
            session["collector_token"],
            {
                "event_type": "dns_query",
                "source": "router_dns",
                "domain": "after-stop.example",
            },
        )
