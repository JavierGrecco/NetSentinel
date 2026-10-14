"""Pruebas de política temporal y retención de actividad."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from netsentinel import activity_retention_service


def test_iso_treats_naive_datetime_as_utc() -> None:
    value = datetime(2026, 10, 14, 12, 30, 45)

    assert activity_retention_service.iso(value) == "2026-10-14T12:30:45+00:00"


def test_iso_converts_aware_datetime_to_utc() -> None:
    value = datetime(
        2026, 10, 14, 15, 30, tzinfo=timezone(timedelta(hours=3))
    )

    assert activity_retention_service.iso(value) == "2026-10-14T12:30:00+00:00"


def test_now_returns_utc_aware_datetime() -> None:
    value = activity_retention_service.now()

    assert value.tzinfo is not None
    assert value.utcoffset() == timedelta(0)


@pytest.mark.parametrize("days", [0, 91, True, False, 1.5, 7.25, None, object()])
def test_update_retention_rejects_invalid_values_before_storage(
    monkeypatch, days
) -> None:
    def unexpected_update(*args, **kwargs):
        pytest.fail("Una retención inválida no debe llegar al repositorio.")

    monkeypatch.setattr(
        activity_retention_service.activity_repository, "update_retention", unexpected_update
    )

    with pytest.raises(ValueError, match="retención debe ser de 1 a 90 días"):
        activity_retention_service.update_retention(days)


@pytest.mark.parametrize("days, expected", [(1, 1), (7, 7), (90, 90), ("07", 7)])
def test_update_retention_delegates_validated_days_and_utc_time(
    monkeypatch, days, expected
) -> None:
    fixed_now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    calls: dict[str, object] = {}

    monkeypatch.setattr(activity_retention_service, "now", lambda: fixed_now)

    def update(days_arg, *, now):
        calls["args"] = (days_arg, now)
        return {"retention_days": days_arg, "deleted_events": 2}

    monkeypatch.setattr(
        activity_retention_service.activity_repository, "update_retention", update
    )

    result = activity_retention_service.update_retention(days)

    assert calls["args"] == (expected, fixed_now)
    assert result == {"retention_days": expected, "deleted_events": 2}


def test_cleanup_reuses_the_shared_utc_clock(monkeypatch) -> None:
    fixed_now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    sentinel_db = object()
    calls: dict[str, object] = {}
    monkeypatch.setattr(activity_retention_service, "now", lambda: fixed_now)

    def cleanup(db, *, now):
        calls["args"] = (db, now)
        return 4

    monkeypatch.setattr(
        activity_retention_service.activity_repository, "cleanup", cleanup
    )

    assert activity_retention_service.cleanup(sentinel_db) == 4
    assert calls["args"] == (sentinel_db, fixed_now)
