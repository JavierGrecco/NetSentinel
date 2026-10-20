"""Pruebas del importador Zeek JSONL sin captura ni acceso a redes reales."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from netsentinel import activity_zeek_import_service as importer


def _record(**overrides):
    record = {
        "ts": datetime.now(timezone.utc).timestamp(),
        "uid": "CZeekFixture42",
        "id.orig_h": "192.0.2.20",
        "id.orig_p": 51514,
        "id.resp_h": "198.51.100.53",
        "id.resp_p": 53,
        "proto": "udp",
        "orig_bytes": 62,
        "resp_bytes": 141,
        "orig_ip_bytes": 118,
        "resp_ip_bytes": 197,
        "orig_pkts": 2,
        "resp_pkts": 3,
    }
    record.update(overrides)
    return record


def _jsonl(*records):
    return "\n".join(json.dumps(record) for record in records) + "\n"


def _active_interval():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return (
        (now - timedelta(hours=1)).isoformat(),
        (now + timedelta(hours=1)).isoformat(),
    )


def _mock_selected_ip_history(monkeypatch, device_id: int, selected_ip: str = "192.0.2.20"):
    first_seen, last_seen = _active_interval()
    row = {
        "ip_address": selected_ip,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }
    monkeypatch.setattr(
        importer.inventory_read_repository,
        "get_device_addresses",
        lambda _device_id: [row],
    )

    def owners_for_ips(ip_addresses):
        return {
            ip: ([{"device_id": device_id, **row}] if ip == selected_ip else [])
            for ip in ip_addresses
        }

    monkeypatch.setattr(importer.inventory_read_repository, "get_address_owners", owners_for_ips)


def test_zeek_mapping_keeps_directions_and_source_uid():
    mapped = importer._to_event(_record(), 1)

    assert mapped["event_type"] == "connection"
    assert mapped["source_ip"] == "192.0.2.20"
    assert mapped["source_port"] == 51514
    assert mapped["destination_ip"] == "198.51.100.53"
    assert mapped["destination_port"] == 53
    assert mapped["protocol"] == "udp"
    assert mapped["bytes_sent"] == 118
    assert mapped["bytes_received"] == 197
    assert mapped["packets_sent"] == 2
    assert mapped["packets_received"] == 3
    assert mapped["source_event_id"] == "zeek:CZeekFixture42"


def test_zeek_mapping_keeps_missing_counters_unknown_and_zero_as_zero():
    mapped = importer._to_event(
        _record(orig_ip_bytes=0, resp_ip_bytes="-", orig_pkts=None, resp_pkts=0),
        1,
    )

    assert mapped["bytes_sent"] == 0
    assert mapped["bytes_received"] is None
    assert mapped["packets_sent"] is None
    assert mapped["packets_received"] == 0


def test_zeek_protocols_without_a_common_name_map_to_other():
    assert importer._protocol("unknown_transport") == "other"
    assert importer._protocol("tcp") == "tcp"
    assert importer._protocol("ICMP") == "icmp"


def test_zeek_port_zero_means_not_applicable_and_not_an_invalid_port():
    mapped = importer._to_event(_record(proto="unknown_transport", **{
        "id.orig_p": 0,
        "id.resp_p": 0,
    }), 1)

    assert mapped["protocol"] == "other"
    assert mapped["source_port"] is None
    assert mapped["destination_port"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ts", float("nan")),
        ("ts", True),
        ("uid", "-"),
        ("id.orig_h", "not-an-ip"),
        ("id.resp_h", "198.51.100.53/24"),
        ("id.orig_p", True),
        ("id.resp_p", 65536),
        ("orig_ip_bytes", -1),
        ("resp_pkts", 1.5),
    ],
)
def test_zeek_import_rejects_invalid_required_fields_and_counters(field, value):
    record = _record(**{field: value})
    with pytest.raises(ValueError):
        event = importer._to_event(record, 4)
        from netsentinel import activity_event_service
        activity_event_service.normalize_event(event, source_override="manual_import")


def test_zeek_import_rejects_duplicate_json_keys_and_non_objects():
    with pytest.raises(ValueError, match="JSON válido"):
        importer._parse_json_line('{"ts": 1, "ts": 2}', 3)
    with pytest.raises(ValueError, match="objeto JSON"):
        importer._parse_json_line('["not", "an", "event"]', 5)


def test_zeek_import_enforces_size_and_row_limits(monkeypatch):
    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda _id: None)

    with pytest.raises(ValueError, match="1 MB"):
        importer.import_jsonl(1, " " * (importer.MAX_IMPORT_BYTES + 1))

    jsonl = _jsonl(*[_record(uid=f"uid-{index}") for index in range(importer.MAX_IMPORT_ROWS + 1)])
    with pytest.raises(ValueError, match="1000"):
        importer.import_jsonl(1, jsonl)


def test_zeek_preview_does_not_write_and_reports_duplicate_source_ids(monkeypatch):
    calls = {}

    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda device_id: None)
    _mock_selected_ip_history(monkeypatch, 7)

    def fake_import(device_id, events, line_numbers, *, now, preview):
        calls.update(
            device_id=device_id, events=events, line_numbers=line_numbers,
            now=now, preview=preview,
        )
        return {
            "imported": 1,
            "skipped_duplicates": 1,
            "preview_dispositions": ["new", "duplicate"],
        }

    monkeypatch.setattr(importer.activity_repository, "import_manual_events", fake_import)

    result = importer.import_jsonl(
        7,
        _jsonl(_record(), _record()),
        normalize_event=lambda event, **kwargs: {**event, "source": kwargs["source_override"]},
        preview=True,
    )

    assert calls["device_id"] == 7
    assert calls["preview"] is True
    assert calls["line_numbers"] == [1, 2]
    assert calls["events"][0]["source_event_id"] == "zeek:CZeekFixture42"
    assert result["valid_rows"] == 2
    assert result["matching_rows"] == 2
    assert result["skipped_out_of_scope"] == 0
    assert result["would_import"] == 1
    assert result["skipped_duplicates"] == 1
    assert [row["disposition"] for row in result["preview_rows"]] == ["new", "duplicate"]
    assert "no se guardó" in result["note"].lower()


def test_zeek_import_skips_connections_that_do_not_touch_the_selected_device(monkeypatch):
    calls = {}
    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda _id: None)
    _mock_selected_ip_history(monkeypatch, 1)

    def fake_import(device_id, events, line_numbers, *, now, preview):
        calls["events"] = events
        calls["line_numbers"] = line_numbers
        calls["preview"] = preview
        return {"imported": 1, "skipped_duplicates": 0, "preview_dispositions": ["new"]}

    monkeypatch.setattr(importer.activity_repository, "import_manual_events", fake_import)
    other = _record(uid="COutside42", **{
        "id.orig_h": "203.0.113.44",
        "id.resp_h": "198.51.100.80",
    })
    result = importer.import_jsonl(
        1,
        _jsonl(_record(), other),
        normalize_event=lambda event, **kwargs: {**event, "source": kwargs["source_override"]},
        preview=True,
    )

    assert len(calls["events"]) == 1
    assert calls["line_numbers"] == [1]
    assert calls["preview"] is True
    assert result["valid_rows"] == 2
    assert result["matching_rows"] == 1
    assert result["skipped_out_of_scope"] == 1
    assert result["would_import"] == 1


def test_zeek_import_does_not_use_ip_outside_its_observed_interval(monkeypatch):
    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda _id: None)
    _mock_selected_ip_history(monkeypatch, 1)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Una conexión fuera del intervalo no debe importarse.")

    monkeypatch.setattr(importer.activity_repository, "import_manual_events", fail_if_called)
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
    result = importer.import_jsonl(
        1,
        _jsonl(_record(ts=old_ts)),
        normalize_event=lambda event, **kwargs: {**event, "source": kwargs["source_override"]},
        preview=True,
    )

    assert result["valid_rows"] == 1
    assert result["matching_rows"] == 0
    assert result["skipped_out_of_scope"] == 1
    assert result["skipped_ambiguous"] == 0
    assert result["would_import"] == 0
    assert "fuera del intervalo observado" in result["note"]


def test_zeek_import_skips_flows_when_ip_history_overlaps_another_asset(monkeypatch):
    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda _id: None)
    first_seen, last_seen = _active_interval()
    address = {
        "ip_address": "192.0.2.20",
        "first_seen": first_seen,
        "last_seen": last_seen,
    }
    monkeypatch.setattr(
        importer.inventory_read_repository,
        "get_device_addresses",
        lambda _id: [address],
    )
    monkeypatch.setattr(
        importer.inventory_read_repository,
        "get_address_owners",
        lambda ips: {
            ip: ([{"device_id": 1, **address}, {"device_id": 99, **address}]
                 if ip == "192.0.2.20" else [])
            for ip in ips
        },
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Una dirección con propietarios solapados no debe importarse.")

    monkeypatch.setattr(importer.activity_repository, "import_manual_events", fail_if_called)
    result = importer.import_jsonl(
        1,
        _jsonl(_record()),
        normalize_event=lambda event, **kwargs: {**event, "source": kwargs["source_override"]},
        preview=True,
    )

    assert result["valid_rows"] == 1
    assert result["matching_rows"] == 0
    assert result["skipped_ambiguous"] == 1
    assert result["skipped_out_of_scope"] == 0
    assert result["would_import"] == 0
    assert "propietarios históricos solapados" in result["note"]


def test_zeek_import_rejects_bad_record_before_repository_write(monkeypatch):
    monkeypatch.setattr(importer.activity_repository, "require_device_exists", lambda _id: None)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("No debe persistir un archivo malformado.")

    monkeypatch.setattr(importer.activity_repository, "import_manual_events", fail_if_called)

    invalid = _record(**{"id.orig_h": "invalid-ip"})
    with pytest.raises(ValueError, match="Fila 1"):
        importer.import_jsonl(1, _jsonl(invalid))
