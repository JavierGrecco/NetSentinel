"""Contratos estrictos para números recibidos por la API de actividad."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from netsentinel.api.activity import ActivityEventIngest, ActivityRetentionUpdate


BASE_INGEST = {
    "session_id": 1,
    "collector_token": "t" * 40,
    "device_id": 1,
    "event_type": "connection",
    "source": "router_flow",
}


@pytest.mark.parametrize("value", [True, False, 80.5, 443.0, "443"])
def test_ingest_schema_rejects_coercible_destination_ports(value) -> None:
    with pytest.raises(ValidationError):
        ActivityEventIngest.model_validate({**BASE_INGEST, "destination_port": value})


@pytest.mark.parametrize("value", [1, 53, 443, 65535, None])
def test_ingest_schema_accepts_valid_integer_ports(value) -> None:
    body = ActivityEventIngest.model_validate(
        {**BASE_INGEST, "destination_port": value}
    )
    assert body.destination_port == value


@pytest.mark.parametrize("value", [True, False, 7.5, 7.0, "7"])
def test_retention_schema_rejects_coercible_non_integer_values(value) -> None:
    with pytest.raises(ValidationError):
        ActivityRetentionUpdate.model_validate({"retention_days": value})


@pytest.mark.parametrize("value", [1, 7, 90])
def test_retention_schema_accepts_valid_integer_values(value) -> None:
    body = ActivityRetentionUpdate.model_validate({"retention_days": value})
    assert body.retention_days == value
