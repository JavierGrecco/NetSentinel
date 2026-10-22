"""Pruebas unitarias del servicio que interpreta archivos CSV de actividad."""
from __future__ import annotations

from typing import Any

import pytest

from netsentinel import activity_import_service as importer


def test_csv_header_normalization_handles_bom_and_camel_case() -> None:
    """Las cabeceras de proveedores se normalizan antes de buscar sus alias."""
    assert importer._normalized_csv_header("\ufeffreceivedDateTime") == "received_date_time"
    assert importer._canonical_csv_header("senderAddress") == "email_from"
    assert importer._canonical_csv_header("recipientAddress") == "email_to"
    assert importer._canonical_csv_header("src_ip") == "source_ip"
    assert importer._canonical_csv_header("src_port") == "source_port"
    assert importer._canonical_csv_header("eventId") == "source_event_id"
    assert importer._canonical_csv_header("interface") == "network_interface"


@pytest.mark.parametrize(
    "header",
    [
        "messageBody",
        "email_body",
        "attachment_content",
        "requestBody",
        "authorization",
    ],
)
def test_csv_import_service_rejects_sensitive_headers(header: str) -> None:
    """El servicio identifica columnas que podrían contener contenido sensible."""
    assert importer._is_sensitive_csv_header(header) is True


def test_csv_import_service_allows_message_identifiers() -> None:
    """Los identificadores no contienen el cuerpo del mensaje y se pueden ignorar."""
    assert importer._is_sensitive_csv_header("messageId") is False
    assert importer._canonical_csv_header("messageId") is None


def test_csv_preview_normalizes_rows_and_delegates_without_writing(monkeypatch) -> None:
    """La vista previa entrega eventos normalizados y declara que no guarda datos."""
    calls: dict[str, Any] = {}

    def require_device(device_id: int) -> None:
        calls["device_id"] = device_id

    def import_events(
        device_id: int,
        events: list[dict[str, Any]],
        line_numbers: list[int],
        *,
        now,
        preview: bool,
    ) -> dict[str, Any]:
        calls["repository"] = {
            "device_id": device_id,
            "events": events,
            "line_numbers": line_numbers,
            "now": now,
            "preview": preview,
        }
        return {
            "imported": 1,
            "skipped_duplicates": 0,
            "preview_dispositions": ["new"],
        }

    def normalize_event(payload: dict[str, Any], *, source_override: str) -> dict[str, Any]:
        assert source_override == "manual_import"
        return {
            field: payload.get(field)
            for field in importer.CSV_PREVIEW_FIELDS
        }

    monkeypatch.setattr(importer.activity_repository, "require_device_exists", require_device)
    monkeypatch.setattr(importer.activity_repository, "import_manual_events", import_events)

    result = importer.import_csv(
        42,
        "observed_at,event_type,domain,source_ip,source_port,bytes_sent,packets_received,interface,event_id\n"
        "2026-10-14T10:00:00Z,dns_query,example.com,192.0.2.4,53,120,2,wan0,record-42\n",
        normalize_event=normalize_event,
        preview=True,
    )

    assert calls["device_id"] == 42
    assert calls["repository"]["preview"] is True
    assert calls["repository"]["line_numbers"] == [2]
    assert calls["repository"]["events"][0]["domain"] == "example.com"
    assert calls["repository"]["events"][0]["source_ip"] == "192.0.2.4"
    # Este doble de normalize_event devuelve los valores CSV tal cual;
    # la conversión de cadenas numéricas se comprueba en el servicio real.
    assert calls["repository"]["events"][0]["source_port"] == "53"
    assert calls["repository"]["events"][0]["bytes_sent"] == "120"
    assert calls["repository"]["events"][0]["packets_received"] == "2"
    assert calls["repository"]["events"][0]["network_interface"] == "wan0"
    assert calls["repository"]["events"][0]["source_event_id"] == "record-42"
    assert result["would_import"] == 1
    assert result["preview_rows"][0]["disposition"] == "new"
    assert "no se guardó ningún evento" in result["note"]


def test_csv_import_rejects_sensitive_columns_before_accessing_device(monkeypatch) -> None:
    """Un CSV con cuerpo de mensaje se rechaza antes de acceder a la persistencia."""
    def unexpected_repository_call(*args, **kwargs):
        raise AssertionError("No debe acceder al repositorio antes de validar las cabeceras.")

    monkeypatch.setattr(
        importer.activity_repository,
        "require_device_exists",
        unexpected_repository_call,
    )

    with pytest.raises(ValueError, match="por privacidad"):
        importer.import_csv(
            42,
            "observed_at,event_type,messageBody\n2026-10-14T10:00:00Z,email_metadata,secret\n",
            normalize_event=lambda payload, **kwargs: payload,
        )


def test_csv_import_rejects_duplicate_headers_after_alias_normalization(monkeypatch) -> None:
    """Cabeceras distintas que representan el mismo campo no se interpretan ambiguamente."""
    def unexpected_repository_call(*args, **kwargs):
        raise AssertionError("No debe acceder al repositorio con cabeceras ambiguas.")

    monkeypatch.setattr(
        importer.activity_repository,
        "require_device_exists",
        unexpected_repository_call,
    )

    with pytest.raises(ValueError, match="repite una cabecera"):
        importer.import_csv(
            42,
            "observed_at,date,event_type\n2026-10-14T10:00:00Z,2026-10-14,dns_query\n",
            normalize_event=lambda payload, **kwargs: payload,
        )
