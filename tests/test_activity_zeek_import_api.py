"""Pruebas HTTP del adaptador Zeek con SQLite temporal y datos sintéticos."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from netsentinel import database
from netsentinel.main import app


def _create_device() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    first_seen = (now - timedelta(hours=1)).isoformat()
    last_seen = (now + timedelta(hours=1)).isoformat()
    with database.connect() as db:
        cursor = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, first_seen, last_seen, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            ("02:00:00:00:00:42", "192.0.2.42", first_seen, last_seen, "Zeek import fixture"),
        )
        device_id = int(cursor.lastrowid)
        db.execute(
            """INSERT INTO device_addresses
               (device_id, ip_address, first_seen, last_seen, interface, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (device_id, "192.0.2.42", first_seen, last_seen, "fixture0", "zeek-import-test"),
        )
        return device_id


def _record(uid: str = "CZeekApi42") -> dict:
    return {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).timestamp(),
        "uid": uid,
        "id.orig_h": "192.0.2.42",
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


def _jsonl(*records: dict) -> str:
    return "\n".join(json.dumps(record) for record in records) + "\n"

def _zeek_tsv(*records: dict) -> str:
    fields = [
        "ts", "uid", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p",
        "proto", "orig_bytes", "resp_bytes", "orig_pkts", "orig_ip_bytes",
        "resp_pkts", "resp_ip_bytes",
    ]
    types = [
        "time", "string", "addr", "port", "addr", "port", "enum",
        "count", "count", "count", "count", "count", "count",
    ]
    lines = [
        r"#separator \x09",
        "#set_separator ,",
        "#empty_field (empty)",
        "#unset_field -",
        "#path conn",
        "#open 2026-10-20-12-00-00",
        "#fields " + "\t".join(fields),
        "#types " + "\t".join(types),
    ]
    for record in records:
        lines.append(
            "\t".join("-" if record.get(field) is None else str(record.get(field, "-")) for field in fields)
        )
    lines.append("#close 2026-10-20-12-00-00")
    return "\n".join(lines) + "\n"




def test_zeek_preview_import_and_reimport_are_read_only_and_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    selected_device = _create_device()
    sample = _record()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        preview = client.post(
            "/api/activity/import/zeek/preview",
            json={"device_id": selected_device, "log_data": _jsonl(sample, sample)},
        )
        assert preview.status_code == 200, preview.text
        preview_body = preview.json()
        assert preview_body["valid_rows"] == 2
        assert preview_body["matching_rows"] == 2
        assert preview_body["skipped_out_of_scope"] == 0
        assert preview_body["skipped_ambiguous"] == 0
        assert preview_body["would_import"] == 1
        assert preview_body["skipped_duplicates"] == 1
        assert [row["disposition"] for row in preview_body["preview_rows"]] == ["new", "duplicate"]
        assert "no se guardó" in preview_body["note"].lower()
        assert client.get(f"/api/activity?device_id={selected_device}").json()["events"] == []

        imported = client.post(
            "/api/activity/import/zeek",
            json={"device_id": selected_device, "log_data": _jsonl(sample, sample)},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["imported"] == 1
        assert imported.json()["skipped_duplicates"] == 1
        assert imported.json()["skipped_out_of_scope"] == 0
        assert imported.json()["skipped_ambiguous"] == 0

        imported_again = client.post(
            "/api/activity/import/zeek",
            json={"device_id": selected_device, "log_data": _jsonl(sample, sample)},
        )
        assert imported_again.status_code == 200, imported_again.text
        assert imported_again.json()["imported"] == 0
        assert imported_again.json()["skipped_duplicates"] == 2

        events = client.get(f"/api/activity?device_id={selected_device}").json()["events"]
        assert len(events) == 1
        event = events[0]
        assert event["event_type"] == "connection"
        assert event["source"] == "manual_import"
        assert event["source_event_id"] == "zeek:CZeekApi42"
        assert event["source_ip"] == "192.0.2.42"
        assert event["source_port"] == 51514
        assert event["destination_ip"] == "198.51.100.53"
        assert event["destination_port"] == 53
        assert event["protocol"] == "udp"
        assert event["bytes_sent"] == 118
        assert event["bytes_received"] == 197
        assert event["packets_sent"] == 2
        assert event["packets_received"] == 3


def test_zeek_import_rejects_malformed_data_without_partial_writes(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    selected_device = _create_device()
    good = _record()
    bad = _record("CBadRecord")
    bad["id.orig_h"] = "not-an-ip"

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/activity/import/zeek",
            json={"device_id": selected_device, "log_data": _jsonl(good, bad)},
        )
        assert response.status_code == 422
        assert "Fila 2" in response.json()["detail"]
        assert client.get(f"/api/activity?device_id={selected_device}").json()["events"] == []


def test_zeek_import_skips_rows_outside_selected_device_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    selected_device = _create_device()
    matching = _record("CMatchesDevice")
    outside = _record("COtherDevice")
    outside["id.orig_h"] = "203.0.113.44"
    outside["id.resp_h"] = "198.51.100.80"

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/activity/import/zeek/preview",
            json={"device_id": selected_device, "log_data": _jsonl(matching, outside)},
        )
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["valid_rows"] == 2
        assert preview["matching_rows"] == 1
        assert preview["would_import"] == 1
        assert preview["skipped_out_of_scope"] == 1
        assert preview["skipped_ambiguous"] == 0
        assert len(preview["preview_rows"]) == 1
        assert preview["preview_rows"][0]["source_event_id"] == "zeek:CMatchesDevice"
        assert client.get(f"/api/activity?device_id={selected_device}").json()["events"] == []

        imported = client.post(
            "/api/activity/import/zeek",
            json={"device_id": selected_device, "log_data": _jsonl(matching, outside)},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["imported"] == 1
        assert imported.json()["skipped_out_of_scope"] == 1
        assert imported.json()["skipped_ambiguous"] == 0
        assert imported.json()["note"].count("fuera del intervalo observado") == 1
        assert "otros dispositivos" not in imported.json()["note"]
        events = client.get(f"/api/activity?device_id={selected_device}").json()["events"]
        assert len(events) == 1
        assert events[0]["source_event_id"] == "zeek:CMatchesDevice"


def test_zeek_import_supports_legacy_device_without_address_history(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    first_seen = (now - timedelta(minutes=10)).isoformat()
    last_seen = (now + timedelta(minutes=10)).isoformat()
    with database.connect() as db:
        cursor = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, first_seen, last_seen, display_name)
               VALUES (?, ?, ?, ?, ?)""",
            ("02:00:00:00:00:43", "192.0.2.42", first_seen, last_seen, "Legacy Zeek fixture"),
        )
        selected_device = int(cursor.lastrowid)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/activity/import/zeek/preview",
            json={"device_id": selected_device, "log_data": _jsonl(_record())},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["valid_rows"] == 1
        assert result["matching_rows"] == 1
        assert result["would_import"] == 1
        assert result["skipped_out_of_scope"] == 0
        assert result["skipped_ambiguous"] == 0


def test_zeek_import_accepts_native_tsv_conn_log(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    selected_device = _create_device()
    record = _record("CZeekTsv42")
    record["id.orig_h"] = "192.0.2.42"
    log_data = _zeek_tsv(record)

    with TestClient(app, base_url="http://127.0.0.1") as client:
        preview = client.post(
            "/api/activity/import/zeek/preview",
            json={"device_id": selected_device, "log_data": log_data},
        )
        assert preview.status_code == 200, preview.text
        preview_body = preview.json()
        assert preview_body["valid_rows"] == 1
        assert preview_body["matching_rows"] == 1
        assert preview_body["would_import"] == 1
        assert preview_body["preview_rows"][0]["source_event_id"] == "zeek:CZeekTsv42"
        assert preview_body["preview_rows"][0]["bytes_sent"] == 118
        assert preview_body["preview_rows"][0]["bytes_received"] == 197
        assert client.get(f"/api/activity?device_id={selected_device}").json()["events"] == []

        imported = client.post(
            "/api/activity/import/zeek",
            json={"device_id": selected_device, "log_data": log_data},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["imported"] == 1
        event = client.get(f"/api/activity?device_id={selected_device}").json()["events"][0]
        assert event["source_event_id"] == "zeek:CZeekTsv42"
        assert event["bytes_sent"] == 118
        assert event["bytes_received"] == 197


def test_zeek_import_rejects_unknown_request_fields(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NETSENTINEL_DISABLE_SCHEDULER", "1")
    database.initialize()
    selected_device = _create_device()

    with TestClient(app, base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/activity/import/zeek/preview",
            json={
                "device_id": selected_device,
                "log_data": _jsonl(_record()),
                "unexpected": "ignored data must not enter the import contract",
            },
        )
        assert response.status_code == 422
        assert client.get(f"/api/activity?device_id={selected_device}").json()["events"] == []
