"""Pruebas de la consulta acotada de contexto Zeek usada por Hallazgos."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from netsentinel import database, findings_activity_repository


def _stamp(value: datetime) -> str:
    """Serializa una fecha de prueba en el formato UTC del almacenamiento."""
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat(timespec="seconds")


def _database_with_zeek(monkeypatch, tmp_path, *, observed_at: datetime, source_id: str = "zeek:CZeekTest42", source: str = "manual_import"):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    stamp = _stamp(observed_at)
    with database.connect() as db:
        device_id = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, first_seen, last_seen, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            ("AA:BB:CC:DD:EE:42", "192.0.2.42", stamp, stamp, "Equipo sintético"),
        ).lastrowid
        db.execute(
            """INSERT INTO activity_events
               (device_id, observed_at, received_at, event_type, source, source_event_id,
                source_ip, source_port, destination_ip, destination_port, protocol,
                bytes_sent, bytes_received, packets_sent, packets_received)
               VALUES (?, ?, ?, 'connection', ?, ?, ?, ?, ?, ?, 'tcp', 120, 240, 2, 3)""",
            (
                device_id, stamp, _stamp(datetime.now(timezone.utc)), source, source_id,
                "192.0.2.42", 51514, "198.51.100.10", 443,
            ),
        )
    return int(device_id), stamp


def _context(*, device_id=None, target_ip=None, anchor_at, start_at=None, end_at=None):
    anchor = datetime.fromisoformat(anchor_at)
    return {
        "context_id": "finding:fixture",
        "device_id": device_id,
        "target_ip": target_ip,
        "anchor_at": anchor_at,
        "start_at": start_at or _stamp(anchor - timedelta(minutes=5)),
        "end_at": end_at or _stamp(anchor + timedelta(minutes=5)),
        "relation": "test_context",
    }


def test_zeek_context_query_matches_exact_device_and_preserves_source_counters(monkeypatch, tmp_path):
    observed = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    device_id, stamp = _database_with_zeek(monkeypatch, tmp_path, observed_at=observed)

    rows = findings_activity_repository.get_zeek_activity_contexts([
        _context(device_id=device_id, anchor_at=stamp),
    ])

    assert len(rows) == 1
    row = rows[0]
    assert row["context_id"] == "finding:fixture"
    assert row["activity_id"] > 0
    assert row["source_event_id"] == "zeek:CZeekTest42"
    assert row["device_id"] == device_id
    assert row["observed_at"] == stamp
    assert row["source_ip"] == "192.0.2.42"
    assert row["destination_ip"] == "198.51.100.10"
    assert row["bytes_sent"] == 120
    assert row["bytes_received"] == 240
    assert row["packets_sent"] == 2
    assert row["packets_received"] == 3
    assert row["time_delta_seconds"] == pytest.approx(0)


def test_zeek_context_query_matches_only_exact_monitor_ip_in_time_window(monkeypatch, tmp_path):
    observed = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    _device_id, stamp = _database_with_zeek(monkeypatch, tmp_path, observed_at=observed)

    rows = findings_activity_repository.get_zeek_activity_contexts([
        _context(target_ip="198.51.100.10", anchor_at=stamp),
    ])
    wrong_ip = findings_activity_repository.get_zeek_activity_contexts([
        _context(target_ip="198.51.100.99", anchor_at=stamp),
    ])

    assert len(rows) == 1
    assert rows[0]["source_event_id"] == "zeek:CZeekTest42"
    assert wrong_ip == []


def test_zeek_context_query_excludes_non_zeek_sources_and_out_of_window_records(monkeypatch, tmp_path):
    observed = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    device_id, stamp = _database_with_zeek(
        monkeypatch, tmp_path, observed_at=observed, source_id="csv:record-42"
    )

    contexts = [
        _context(device_id=device_id, anchor_at=stamp),
        _context(
            device_id=device_id,
            anchor_at=_stamp(observed + timedelta(minutes=20)),
        ),
    ]
    assert findings_activity_repository.get_zeek_activity_contexts(contexts) == []


@pytest.mark.parametrize("value", [0, 6, True, "5"])
def test_zeek_context_query_rejects_invalid_per_context_limit(value):
    with pytest.raises(ValueError, match="límite por contexto"):
        findings_activity_repository.get_zeek_activity_contexts([], per_context_limit=value)


def test_zeek_context_query_caps_the_number_of_contexts():
    now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
    stamp = _stamp(now)
    contexts = [
        _context(device_id=index + 1, anchor_at=stamp) | {"context_id": f"finding:{index}"}
        for index in range(401)
    ]
    with pytest.raises(ValueError, match="máximo de contextos"):
        findings_activity_repository.get_zeek_activity_contexts(contexts)
