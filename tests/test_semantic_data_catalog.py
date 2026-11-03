"""Pruebas del catálogo semántico: resolución explícita y sugerencias no vinculantes."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from netsentinel.semantics.catalog import get_source_profile
from netsentinel.semantics.models import (
    HeaderStatus,
    QuantityStatus,
    SourceProfile,
    ValueKind,
)
from netsentinel.semantics.resolver import missing_required_fields, normalize_header, resolve_headers
from netsentinel.semantics.values import inspect_value, parse_quantity


def test_header_normalization_supports_bom_camel_case_accents_and_zeek_paths() -> None:
    assert normalize_header("\ufeffreceivedDateTime") == ("received_date_time", None)
    assert normalize_header("DirecciónIP") == ("direccion_ip", None)
    assert normalize_header("id.orig_h") == ("id.orig_h", None)
    assert normalize_header("src-ip") == ("src_ip", None)


def test_header_normalization_rejects_confusable_unicode_and_controls() -> None:
    assert normalize_header("іd.orig_h")[0] is None  # Cyrillic small letter Byelorussian-Ukrainian i.
    assert normalize_header("source\u200b_ip")[0] is None
    assert normalize_header("x" * 129)[0] is None


def test_activity_csv_resolves_existing_aliases_and_ignores_known_metadata() -> None:
    plan = resolve_headers(
        ["receivedDateTime", "senderAddress", "recipientAddress", "src_ip", "interface", "size"],
        "activity_csv",
    )

    assert [item.status for item in plan.headers] == [
        HeaderStatus.ALIAS,
        HeaderStatus.ALIAS,
        HeaderStatus.ALIAS,
        HeaderStatus.ALIAS,
        HeaderStatus.ALIAS,
        HeaderStatus.IGNORED,
    ]
    assert [item.field_name for item in plan.headers[:5]] == [
        "observed_at", "email_from", "email_to", "source_ip", "network_interface",
    ]
    assert plan.headers[5].field_name is None


def test_zeek_conn_profile_preserves_field_direction_and_ip_byte_semantics() -> None:
    plan = resolve_headers(
        ["ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p",
         "proto", "orig_ip_bytes", "resp_ip_bytes", "orig_pkts", "resp_pkts"],
        "zeek_conn_log",
    )

    assert [item.field_name for item in plan.headers] == [
        "observed_at", "source_event_id", "source_ip", "source_port",
        "destination_ip", "destination_port", "protocol", "bytes_sent",
        "bytes_received", "packets_sent", "packets_received",
    ]
    assert all(item.usable for item in plan.headers)


def test_sensitive_csv_headers_are_blocked_including_compound_names() -> None:
    plan = resolve_headers(
        ["messageBody", "requestBody", "authorization", "user", "trace_message", "messageId", "messageSubject"],
        "activity_csv",
    )

    assert [item.status for item in plan.headers] == [
        HeaderStatus.BLOCKED,
        HeaderStatus.BLOCKED,
        HeaderStatus.BLOCKED,
        HeaderStatus.BLOCKED,
        HeaderStatus.BLOCKED,
        HeaderStatus.IGNORED,
        HeaderStatus.ALIAS,
    ]


def test_missing_required_fields_are_reported_even_when_typos_are_suggested() -> None:
    plan = resolve_headers(["timestamp", "destionation_ip"], "activity_csv")

    assert missing_required_fields(plan, {"observed_at", "event_type", "destination_ip"}) == (
        "destination_ip",
        "event_type",
    )


def test_zeek_payload_bytes_are_blocked_instead_of_mapped_to_ip_bytes() -> None:
    plan = resolve_headers(["orig_bytes", "resp_bytes"], "zeek_conn_log")

    assert all(item.status is HeaderStatus.BLOCKED for item in plan.headers)
    assert all("carga útil" in (item.reason or "") for item in plan.headers)


def test_typo_is_a_suggestion_and_never_an_automatic_assignment() -> None:
    plan = resolve_headers(["destionation_ip"], "activity_csv")

    result = plan.headers[0]
    assert result.status is HeaderStatus.SUGGESTION
    assert result.field_name is None
    assert result.suggestions[0].field_name == "destination_ip"
    assert result.usable is False


def test_custom_profile_can_reuse_a_builtin_name_without_inheriting_its_aliases() -> None:
    profile = SourceProfile(
        name="activity_csv",
        description="Perfil aislado para esta prueba.",
        aliases=MappingProxyType({"custom_address": "source_ip"}),
        ignored_headers=MappingProxyType({}),
        blocked_headers=MappingProxyType({}),
        field_scopes=MappingProxyType({}),
    )

    result = resolve_headers(["custom_address", "src_ip"], profile)

    assert result.headers[0].status is HeaderStatus.ALIAS
    assert result.headers[0].field_name == "source_ip"
    assert result.headers[1].status is HeaderStatus.UNKNOWN


def test_close_candidates_are_reported_as_ambiguous() -> None:
    profile = SourceProfile(
        name="test_ambiguous",
        description="Perfil solo para probar empates.",
        aliases=MappingProxyType({"alpha": "source_ip", "alphi": "destination_ip"}),
        ignored_headers=MappingProxyType({}),
        blocked_headers=MappingProxyType({}),
        field_scopes=MappingProxyType({}),
    )

    result = resolve_headers(["alph"], profile).headers[0]

    assert result.status is HeaderStatus.AMBIGUOUS
    assert result.field_name is None
    assert len(result.suggestions) == 2


def test_two_columns_for_the_same_field_are_a_collision_not_last_write_wins() -> None:
    plan = resolve_headers(["src_ip", "source_ip"], "activity_csv")

    assert len(plan.collisions) == 1
    assert plan.collisions[0].field_name == "source_ip"
    assert all(item.status is HeaderStatus.COLLISION for item in plan.headers)
    assert all(item.usable is False for item in plan.headers)


def test_unknown_headers_are_not_assigned_from_value_ranges() -> None:
    plan = resolve_headers(["size", "unknown_metric"], "activity_csv")

    assert plan.headers[0].status is HeaderStatus.IGNORED
    assert plan.headers[1].status is HeaderStatus.UNKNOWN
    assert inspect_value("8080").kind is ValueKind.INTEGER
    assert parse_quantity("8080").status is QuantityStatus.NO_UNIT


def test_value_inspection_recognizes_shapes_without_inventing_roles() -> None:
    assert inspect_value("192.0.2.10").kind is ValueKind.IP_ADDRESS
    assert inspect_value("08:00:27:AA:BB:CC").kind is ValueKind.MAC_ADDRESS
    assert inspect_value("2026-11-03T12:00:00-03:00").timezone_aware is True
    assert inspect_value("2026-11-03 12:00:00").timezone_aware is False
    assert inspect_value("0").kind is ValueKind.INTEGER
    assert inspect_value("true").kind is ValueKind.BOOLEAN
    assert inspect_value(" ").kind is ValueKind.EMPTY


@pytest.mark.parametrize(
    ("raw", "expected_dimension", "expected_unit", "expected_value"),
    [
        ("1.5 KiB", "data_size", "B", "1536.0"),
        ("250 ms", "time", "s", "0.250"),
        ("25%", "ratio", "1", "0.25"),
        ("2 kB", "data_size", "B", "2000"),
    ],
)
def test_explicit_units_convert_only_within_their_declared_dimension(
    raw: str,
    expected_dimension: str,
    expected_unit: str,
    expected_value: str,
) -> None:
    result = parse_quantity(raw)

    assert result.status is QuantityStatus.EXPLICIT
    assert result.dimension == expected_dimension
    assert result.canonical_unit == expected_unit
    assert result.normalized_value == Decimal(expected_value)


def test_decimal_unit_conversion_preserves_precision_beyond_default_decimal_context() -> None:
    raw = "123456789012345678901234567890 kB"

    result = parse_quantity(raw)

    assert result.status is QuantityStatus.EXPLICIT
    assert result.normalized_value == Decimal("123456789012345678901234567890000")


def test_oversized_values_are_rejected_before_expensive_parsing() -> None:
    assert parse_quantity("1" * 129).status is QuantityStatus.INVALID_NUMBER
    assert inspect_value("1" * 129).kind is ValueKind.INVALID
    assert inspect_value("x" * 4097).kind is ValueKind.INVALID


def test_ambiguous_or_unknown_units_are_not_converted() -> None:
    ambiguous = parse_quantity("12 KB")
    unknown = parse_quantity("12 widgets")

    assert ambiguous.status is QuantityStatus.AMBIGUOUS_UNIT
    assert ambiguous.normalized_value is None
    assert unknown.status is QuantityStatus.UNKNOWN_UNIT
    assert unknown.normalized_value is None


def test_numeric_unix_timestamp_candidate_is_not_inferred_from_magnitude() -> None:
    value = inspect_value("1793728800")

    assert value.kind is ValueKind.INTEGER
    assert value.timezone_aware is None
    assert value.quantity is not None
    assert value.quantity.status is QuantityStatus.NO_UNIT
