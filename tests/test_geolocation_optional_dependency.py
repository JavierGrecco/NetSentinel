"""Integración real con MaxMind DB para el extra opcional GeoIP.

Estas pruebas usan fixtures pequeños y públicos del repositorio MaxMind-DB.
No necesitan Internet ni una base GeoLite2 de producción.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from netsentinel import geolocation_service as service


def test_world_map_reads_city_and_asn_with_real_maxminddb_readers(monkeypatch):
    maxminddb = pytest.importorskip("maxminddb")
    fixture_dir = Path(__file__).parent / "fixtures" / "geoip"
    city_path = fixture_dir / "GeoIP2-City-Test.mmdb"
    asn_path = fixture_dir / "GeoLite2-ASN-Test.mmdb"
    assert city_path.is_file()
    assert asn_path.is_file()

    opened_readers = []

    def open_database(path):
        reader = maxminddb.open_database(str(path))
        opened_readers.append(reader)
        return reader

    monkeypatch.setattr(
        service,
        "_maxminddb",
        SimpleNamespace(open_database=open_database),
    )
    monkeypatch.setattr(service, "city_database_path", lambda: city_path)
    monkeypatch.setattr(service, "asn_database_path", lambda: asn_path)
    monkeypatch.setattr(
        service.geolocation_repository,
        "get_destination_ip_observations",
        lambda *, limit: {
            "total_events": 2,
            "events_with_destination_ip": 2,
            "events_without_destination_ip": 0,
            "unique_destination_ips": 2,
            "destination_ips": [
                {
                    "ip": "81.2.69.160",
                    "event_count": 1,
                    "last_seen": "2026-10-20T12:00:00Z",
                    "sample_domain": "example.test",
                },
                {
                    "ip": "1.128.0.0",
                    "event_count": 1,
                    "last_seen": "2026-10-20T11:00:00Z",
                    "sample_domain": "asn.example.test",
                },
            ],
            "limited": False,
        },
    )

    payload = service.get_world_map_data(limit=250)

    assert payload["databases"]["city_status"] == "available"
    assert payload["databases"]["asn_status"] == "available"

    city_record = next(
        item for item in payload["destinations"] if item["ip"] == "81.2.69.160"
    )
    assert city_record["country"] == "United Kingdom"
    assert city_record["location_status"] == "located"
    assert isinstance(city_record["latitude"], float)
    assert isinstance(city_record["longitude"], float)
    assert -90 <= city_record["latitude"] <= 90
    assert -180 <= city_record["longitude"] <= 180

    asn_record = next(
        item for item in payload["destinations"] if item["ip"] == "1.128.0.0"
    )
    assert asn_record["asn"] == 1221
    assert asn_record["asn_organization"] == "Telstra Pty Ltd"

    assert len(opened_readers) == 2
    assert all(reader.closed for reader in opened_readers)
