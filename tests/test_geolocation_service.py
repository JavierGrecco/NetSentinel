"""Pruebas de geolocalización que no requieren Internet ni una base GeoIP real."""
from __future__ import annotations

from pathlib import Path

from netsentinel import geolocation_service as service


class _FakeReader:
    def __init__(self, records):
        self.records = records
        self.closed = False

    def get(self, ip):
        return self.records.get(ip)

    def close(self):
        self.closed = True


class _FakeMaxMind:
    def __init__(self, readers):
        self.readers = readers

    def open_database(self, path):
        return self.readers[str(path)]


def _snapshot(rows):
    return {
        "total_events": 8,
        "events_with_destination_ip": 6,
        "events_without_destination_ip": 2,
        "unique_destination_ips": len(rows),
        "destination_ips": rows,
        "limited": False,
    }


def test_world_map_uses_local_geoip_and_asn_databases_without_network_calls(
    monkeypatch, tmp_path: Path
):
    city_path = tmp_path / "GeoLite2-City.mmdb"
    asn_path = tmp_path / "GeoLite2-ASN.mmdb"
    city_path.touch()
    asn_path.touch()
    city_reader = _FakeReader({
        "8.8.8.8": {
            "country": {"iso_code": "US", "names": {"en": "United States"}},
            "city": {"names": {"en": "Mountain View"}},
            "location": {"latitude": 37.4056, "longitude": -122.0775},
        },
        "1.1.1.1": {
            "country": {"iso_code": "AU", "names": {"en": "Australia"}},
            "city": {"names": {"en": "Sydney"}},
            "location": {"latitude": -33.8688, "longitude": 151.2093},
        },
    })
    asn_reader = _FakeReader({
        "8.8.8.8": {
            "autonomous_system_number": 15169,
            "autonomous_system_organization": "Google LLC",
        },
        "1.1.1.1": {
            "autonomous_system_number": 13335,
            "autonomous_system_organization": "Cloudflare, Inc.",
        },
    })
    fake_module = _FakeMaxMind({str(city_path): city_reader, str(asn_path): asn_reader})
    monkeypatch.setattr(service, "_maxminddb", fake_module)
    monkeypatch.setattr(service, "city_database_path", lambda: city_path)
    monkeypatch.setattr(service, "asn_database_path", lambda: asn_path)
    monkeypatch.setattr(
        service.geolocation_repository,
        "get_destination_ip_observations",
        lambda *, limit: _snapshot([
            {"ip": "8.8.8.8", "event_count": 3, "last_seen": "2026-10-20T12:00:00Z", "sample_domain": "dns.google"},
            {"ip": "1.1.1.1", "event_count": 2, "last_seen": "2026-10-20T11:00:00Z", "sample_domain": "one.one.one.one"},
            {"ip": "192.168.1.1", "event_count": 1, "last_seen": "2026-10-20T10:00:00Z", "sample_domain": ""},
            {"ip": "198.51.100.25", "event_count": 1, "last_seen": "2026-10-20T09:00:00Z", "sample_domain": "invalid.example"},
        ]),
    )

    payload = service.get_world_map_data(limit=250)

    assert payload["summary"]["mapped_destination_ips"] == 2
    assert payload["summary"]["non_public_ip_events_skipped"] == 2
    assert [item["ip"] for item in payload["destinations"]] == ["1.1.1.1", "8.8.8.8"]
    google = next(item for item in payload["destinations"] if item["ip"] == "8.8.8.8")
    assert google["country"] == "United States"
    assert google["country_iso"] == "US"
    assert google["city"] == "Mountain View"
    assert google["asn"] == 15169
    assert google["asn_organization"] == "Google LLC"
    assert google["location_status"] == "located"
    assert city_reader.closed is True
    assert asn_reader.closed is True


def test_world_map_degrades_safely_without_optional_library_or_database(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setattr(service, "_maxminddb", None)
    monkeypatch.setattr(service, "city_database_path", lambda: tmp_path / "missing-city.mmdb")
    monkeypatch.setattr(service, "asn_database_path", lambda: tmp_path / "missing-asn.mmdb")
    monkeypatch.setattr(
        service.geolocation_repository,
        "get_destination_ip_observations",
        lambda *, limit: _snapshot([
            {"ip": "8.8.4.4", "event_count": 2, "last_seen": "2026-10-20T12:00:00Z", "sample_domain": "dns.google"},
            {"ip": "10.0.0.1", "event_count": 1, "last_seen": "2026-10-20T11:00:00Z", "sample_domain": ""},
        ]),
    )

    payload = service.get_world_map_data(limit=5)

    assert payload["databases"]["geoip_library_available"] is False
    assert payload["databases"]["city_status"] == "library_missing"
    assert payload["databases"]["asn_status"] == "library_missing"
    assert len(payload["destinations"]) == 1
    assert payload["destinations"][0]["ip"] == "8.8.4.4"
    assert payload["destinations"][0]["location_status"] == "database_unavailable"
    assert payload["destinations"][0]["latitude"] is None
    assert payload["summary"]["mapped_destination_ips"] == 0


def test_world_map_never_emits_unbounded_or_invalid_coordinates(monkeypatch, tmp_path: Path):
    city_path = tmp_path / "city.mmdb"
    city_path.touch()
    reader = _FakeReader({
        "8.8.8.8": {
            "country": {"iso_code": "US"},
            "location": {"latitude": 200, "longitude": 0},
        },
    })
    monkeypatch.setattr(service, "_maxminddb", _FakeMaxMind({str(city_path): reader}))
    monkeypatch.setattr(service, "city_database_path", lambda: city_path)
    monkeypatch.setattr(service, "asn_database_path", lambda: tmp_path / "missing-asn.mmdb")
    monkeypatch.setattr(
        service.geolocation_repository,
        "get_destination_ip_observations",
        lambda *, limit: _snapshot([
            {"ip": "8.8.8.8", "event_count": 1, "last_seen": "2026-10-20T12:00:00Z", "sample_domain": ""},
            {"ip": "not-an-ip", "event_count": 2, "last_seen": "2026-10-20T11:00:00Z", "sample_domain": ""},
        ]),
    )

    payload = service.get_world_map_data(limit=250)

    assert payload["destinations"][0]["location_status"] == "no_coordinates"
    assert payload["destinations"][0]["latitude"] is None
    assert payload["summary"]["invalid_ip_events_skipped"] == 2
