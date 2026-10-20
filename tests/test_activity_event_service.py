"""Pruebas directas del servicio de validación de eventos."""
import pytest

from netsentinel.activity_event_service import normalize_event


def test_event_normalization_canonicalizes_ipv4_ipv6_and_protocol():
    event = normalize_event({
        "observed_at": "2026-10-13T12:00:00Z",
        "event_type": "connection",
        "source": "router_flow",
        "destination_ip": "2001:0db8:0:0:0:0:0:1",
        "destination_port": "443",
        "protocol": "TCP",
    })
    assert event["destination_ip"] == "2001:db8::1"
    assert event["destination_port"] == 443
    assert event["protocol"] == "tcp"
    assert event["observed_at"] == "2026-10-13T12:00:00+00:00"


@pytest.mark.parametrize("value", ["not-an-ip", "192.0.2.500", "[::1]"])
def test_event_normalization_rejects_invalid_ip_addresses(value):
    with pytest.raises(ValueError, match="destination_ip debe ser una dirección"):
        normalize_event({
            "event_type": "connection",
            "source": "router_flow",
            "destination_ip": value,
        })


@pytest.mark.parametrize("value", [123456, ["2026-10-13T12:00:00Z"], {}])
def test_event_normalization_rejects_non_text_timestamps(value):
    with pytest.raises(ValueError, match="fecha debe ser ISO 8601"):
        normalize_event({
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "example.com",
            "observed_at": value,
        })


def test_event_normalization_rejects_future_and_invalid_timestamps():
    with pytest.raises(ValueError, match="ISO 8601"):
        normalize_event({
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "example.com",
            "observed_at": "yesterday at noon",
        })
    with pytest.raises(ValueError, match="futuro"):
        normalize_event({
            "event_type": "dns_query",
            "source": "router_dns",
            "domain": "example.com",
            "observed_at": "2999-01-01T00:00:00Z",
        })


def test_network_event_contract_preserves_provided_fields():
    event = normalize_event({
        "event_type": "connection", "source": "router_flow",
        "observed_at": "2026-10-20T10:15:00Z",
        "source_ip": "2001:0db8::1", "source_port": "51514",
        "destination_ip": "192.0.2.25", "destination_port": "443", "protocol": "TCP",
        "bytes_sent": "1200", "bytes_received": 0, "packets_sent": 4, "packets_received": 0,
        "network_interface": "  wan0 ", "source_event_id": " flow-00042 ",
    })
    assert event["source_ip"] == "2001:db8::1"
    assert event["source_port"] == 51514
    assert event["destination_ip"] == "192.0.2.25"
    assert event["destination_port"] == 443
    assert event["protocol"] == "tcp"
    assert event["bytes_sent"] == 1200
    assert event["bytes_received"] == 0
    assert event["packets_sent"] == 4
    assert event["packets_received"] == 0
    assert event["network_interface"] == "wan0"
    assert event["source_event_id"] == "flow-00042"


def test_unknown_network_evidence_stays_null_instead_of_becoming_zero():
    event = normalize_event({"event_type": "connection", "source": "router_flow", "destination_ip": "192.0.2.25"})
    assert event["source_ip"] is None
    assert event["source_port"] is None
    assert event["bytes_sent"] is None
    assert event["bytes_received"] is None
    assert event["packets_sent"] is None
    assert event["packets_received"] is None
    assert event["network_interface"] is None
    assert event["source_event_id"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_ip", "not-an-ip", "source_ip"), ("source_port", True, "source_port"),
        ("source_port", 0, "source_port"), ("bytes_sent", True, "bytes_sent"),
        ("bytes_received", -1, "bytes_received"), ("packets_sent", 1.5, "packets_sent"),
        ("packets_received", 9_223_372_036_854_775_808, "packets_received"),
        ("network_interface", "wan0\ninvalid", "network_interface"),
        ("source_event_id", "x" * 161, "source_event_id"),
    ],
)
def test_network_event_contract_rejects_invalid_optional_fields(field, value, message):
    with pytest.raises(ValueError, match=message):
        normalize_event({
            "event_type": "connection", "source": "router_flow",
            "destination_ip": "192.0.2.25", field: value,
        })


def test_email_metadata_requires_explicit_manual_import_and_addresses():
    payload = {
        "event_type": "email_metadata",
        "source": "manual_import",
        "email_from": "sender@example.com",
        "email_to": "recipient@example.com",
        "email_subject": "  quarterly   report ",
    }
    with pytest.raises(ValueError, match="importación explícita"):
        normalize_event(payload)
    event = normalize_event(payload, source_override="manual_import")
    assert event["email_from"] == "sender@example.com"
    assert event["email_to"] == "recipient@example.com"
    assert event["email_subject"] == "quarterly report"
    assert event["source"] == "manual_import"


def test_search_event_requires_engine_and_terms():
    with pytest.raises(ValueError, match="search_query requiere"):
        normalize_event({
            "event_type": "search_query",
            "source": "device_agent",
            "search_engine": "Google",
        })


@pytest.mark.parametrize("value", ["perhaps", "enabled", "2"])
def test_blocked_field_rejects_ambiguous_strings(value):
    with pytest.raises(ValueError, match="blocked debe ser verdadero o falso"):
        normalize_event({
            "event_type": "connection",
            "source": "router_flow",
            "destination_ip": "192.0.2.15",
            "blocked": value,
        })

@pytest.mark.parametrize("value", [80.5, 443.0, True, False, [], {}, object()])
def test_destination_port_rejects_coercible_non_integer_values(value):
    with pytest.raises(ValueError, match="destination_port debe ser un entero"):
        normalize_event({
            "event_type": "connection",
            "source": "router_flow",
            "destination_ip": "192.0.2.15",
            "destination_port": value,
        })


@pytest.mark.parametrize("value", [2, -1, 2.0, 1.0, [], {}, object()])
def test_blocked_field_rejects_non_boolean_non_binary_values(value):
    with pytest.raises(ValueError, match="blocked debe ser verdadero o falso"):
        normalize_event({
            "event_type": "connection",
            "source": "router_flow",
            "destination_ip": "192.0.2.15",
            "blocked": value,
        })


@pytest.mark.parametrize("value, expected", [
    (True, 1), (False, 0), (1, 1), (0, 0),
    ("true", 1), ("YES", 1), ("false", 0), ("0", 0), ("", 0), (None, 0),
])
def test_blocked_field_accepts_explicit_boolean_representations(value, expected):
    event = normalize_event({
        "event_type": "connection",
        "source": "router_flow",
        "destination_ip": "192.0.2.15",
        "blocked": value,
    })
    assert event["blocked"] == expected


@pytest.mark.parametrize("value, expected", [(80, 80), ("443", 443), (" 53 ", 53)])
def test_destination_port_preserves_integer_and_csv_text_compatibility(value, expected):
    event = normalize_event({
        "event_type": "connection",
        "source": "router_flow",
        "destination_ip": "192.0.2.15",
        "destination_port": value,
    })
    assert event["destination_port"] == expected
