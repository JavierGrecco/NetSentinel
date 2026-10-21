"""Pruebas HTTP del mapa mundial, sin datos reales ni servicios externos."""
from __future__ import annotations

from fastapi.testclient import TestClient

from netsentinel import geolocation_service
from netsentinel.main import app


def test_world_map_api_is_read_only_and_disables_caching(monkeypatch):
    expected = {
        "source": "activity_events.destination_ip",
        "summary": {"public_destination_ips_in_sample": 1, "mapped_destination_ips": 0},
        "databases": {"city_status": "database_missing", "asn_status": "database_missing"},
        "destinations": [{
            "ip": "8.8.8.8",
            "event_count": 2,
            "last_seen": "2026-10-20T12:00:00Z",
            "sample_domain": "dns.google",
            "country": "",
            "country_iso": "",
            "city": "",
            "latitude": None,
            "longitude": None,
            "asn": None,
            "asn_organization": "",
            "location_status": "database_unavailable",
        }],
        "notes": [],
    }
    monkeypatch.setattr(
        geolocation_service,
        "get_world_map_data",
        lambda *, limit: {**expected, "received_limit": limit},
    )

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.get("/api/geolocation/map?limit=17")

    assert response.status_code == 200, response.text
    assert response.json()["received_limit"] == 17
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_world_map_api_rejects_unbounded_limits(monkeypatch):
    monkeypatch.setattr(geolocation_service, "get_world_map_data", lambda **kwargs: {})
    with TestClient(app, base_url="http://127.0.0.1") as client:
        too_small = client.get("/api/geolocation/map?limit=0")
        too_large = client.get("/api/geolocation/map?limit=501")
    assert too_small.status_code == 422
    assert too_large.status_code == 422


def test_current_dns_ip_lookup_is_local_and_disables_caching(monkeypatch):
    seen = []

    def lookup(addresses):
        seen.extend(addresses)
        return {
            "source": "current_dns_resolution",
            "queried_at": "2026-10-20T12:00:00Z",
            "summary": {"requested_ip_count": len(addresses), "public_ip_count": 1},
            "destinations": [{"ip": "8.8.8.8", "latitude": 37.4, "longitude": -122.0}],
        }

    monkeypatch.setattr(geolocation_service, "lookup_public_ips", lookup)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/geolocation/lookup",
            json={"addresses": ["8.8.8.8", "192.168.1.1"]},
            headers={"Origin": "http://127.0.0.1"},
        )

    assert response.status_code == 200, response.text
    assert seen == ["8.8.8.8", "192.168.1.1"]
    assert response.json()["source"] == "current_dns_resolution"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_current_dns_ip_lookup_requires_a_bounded_nonempty_list():
    with TestClient(app, base_url="http://127.0.0.1") as client:
        empty = client.post("/api/geolocation/lookup", json={"addresses": []})
        too_many = client.post(
            "/api/geolocation/lookup",
            json={"addresses": [f"8.8.8.{index % 255}" for index in range(33)]},
        )
    assert empty.status_code == 422
    assert too_many.status_code == 422
