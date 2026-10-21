"""Pruebas de la lectura local de IP de destino para el mapa mundial."""
from __future__ import annotations

from netsentinel import database
from netsentinel.discovery import Neighbor
from netsentinel.geolocation_repository import get_destination_ip_observations


def test_destination_ip_observations_uses_latest_domain_and_bounds_result(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    database.initialize()
    database.record_scan([
        Neighbor("192.168.56.20", "02:00:00:00:00:20", "fixture0")
    ])

    with database.connect() as db:
        device_id = db.execute(
            "SELECT id FROM devices WHERE ip_address = ?",
            ("192.168.56.20",),
        ).fetchone()["id"]
        db.executemany(
            """INSERT INTO activity_events (
                   device_id, observed_at, received_at, event_type, source,
                   domain, destination_ip
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    device_id,
                    "2026-10-20T10:00:00Z",
                    "2026-10-20T10:00:01Z",
                    "connection",
                    "manual_import",
                    "old.example",
                    "8.8.8.8",
                ),
                (
                    device_id,
                    "2026-10-20T11:00:00Z",
                    "2026-10-20T11:00:01Z",
                    "connection",
                    "manual_import",
                    "new.example",
                    "8.8.8.8",
                ),
                (
                    device_id,
                    "2026-10-20T10:30:00Z",
                    "2026-10-20T10:30:01Z",
                    "connection",
                    "manual_import",
                    "resolver.example",
                    "1.1.1.1",
                ),
                (
                    device_id,
                    "2026-10-20T11:30:00Z",
                    "2026-10-20T11:30:01Z",
                    "page_visit",
                    "manual_import",
                    "page-only.example",
                    None,
                ),
            ],
        )

    summary = get_destination_ip_observations(limit=10)
    assert summary["total_events"] == 4
    assert summary["events_with_destination_ip"] == 3
    assert summary["events_without_destination_ip"] == 1
    assert summary["unique_destination_ips"] == 2
    assert summary["limited"] is False

    first = summary["destination_ips"][0]
    assert first["ip"] == "8.8.8.8"
    assert first["event_count"] == 2
    assert first["last_seen"] == "2026-10-20T11:00:00Z"
    assert first["sample_domain"] == "new.example"

    bounded = get_destination_ip_observations(limit=1)
    assert len(bounded["destination_ips"]) == 1
    assert bounded["destination_ips"][0]["ip"] == "8.8.8.8"
    assert bounded["limited"] is True
