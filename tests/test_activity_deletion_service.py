"""Pruebas unitarias del caso de uso de borrado selectivo de actividad."""
from __future__ import annotations

import pytest

from netsentinel import activity_deletion_service


def test_preview_is_read_only_and_returns_exact_confirmation(monkeypatch) -> None:
    calls: dict[str, object] = {}
    expected_scope = (" WHERE device_id = ? AND source = ?", (7, "manual_import"))

    def build_scope(device_id, event_type, from_date, to_date, source):
        calls["scope_args"] = (device_id, event_type, from_date, to_date, source)
        return expected_scope

    def count_scope(where_sql, params, *, device_id):
        calls["count_args"] = (where_sql, params, device_id)
        return 3

    def unexpected_delete(*args, **kwargs):
        pytest.fail("La vista previa no debe borrar eventos.")

    monkeypatch.setattr(
        activity_deletion_service.activity_filters, "activity_delete_scope", build_scope
    )
    monkeypatch.setattr(
        activity_deletion_service.activity_repository, "count_activity_scope", count_scope
    )
    monkeypatch.setattr(
        activity_deletion_service.activity_repository, "delete_activity_scope", unexpected_delete
    )

    result = activity_deletion_service.preview_delete_activity(
        device_id=7, source="manual_import"
    )

    assert calls["scope_args"] == (7, None, None, None, "manual_import")
    assert calls["count_args"] == (*expected_scope, 7)
    assert result == {
        "device_id": 7,
        "event_type": None,
        "from_date": None,
        "to_date": None,
        "source": "manual_import",
        "matching_events": 3,
        "confirmation_required": "BORRAR 3",
        "deleted": False,
        "note": "Vista previa únicamente: no se borró ningún evento.",
    }


@pytest.mark.parametrize("confirmation", [None, 42, "B" * 41])
def test_delete_rejects_invalid_confirmation_before_repository_write(
    monkeypatch, confirmation
) -> None:
    monkeypatch.setattr(
        activity_deletion_service.activity_filters,
        "activity_delete_scope",
        lambda *args: (" WHERE device_id = ?", (7,)),
    )

    def unexpected_delete(*args, **kwargs):
        pytest.fail("Una confirmación inválida no debe llegar al repositorio.")

    monkeypatch.setattr(
        activity_deletion_service.activity_repository, "delete_activity_scope", unexpected_delete
    )

    with pytest.raises(PermissionError, match="frase de confirmación no es válida"):
        activity_deletion_service.delete_activity(
            7, None, None, None, confirmation, source=None
        )


def test_delete_delegates_scope_and_confirmation_to_repository(monkeypatch) -> None:
    calls: dict[str, object] = {}
    expected_scope = (" WHERE device_id = ? AND event_type = ?", (7, "dns_query"))

    monkeypatch.setattr(
        activity_deletion_service.activity_filters,
        "activity_delete_scope",
        lambda *args: expected_scope,
    )

    def delete_scope(where_sql, params, *, device_id, confirmation):
        calls["delete_args"] = (where_sql, params, device_id, confirmation)
        return 2

    monkeypatch.setattr(
        activity_deletion_service.activity_repository, "delete_activity_scope", delete_scope
    )

    result = activity_deletion_service.delete_activity(
        7, "dns_query", None, None, "BORRAR 2"
    )

    assert calls["delete_args"] == (*expected_scope, 7, "BORRAR 2")
    assert result == {
        "deleted_events": 2,
        "device_id": 7,
        "event_type": "dns_query",
        "from_date": None,
        "to_date": None,
        "source": None,
        "note": "Se borraron únicamente los eventos que coincidían con el alcance confirmado.",
    }


def test_repository_rejection_is_not_hidden(monkeypatch) -> None:
    monkeypatch.setattr(
        activity_deletion_service.activity_filters,
        "activity_delete_scope",
        lambda *args: (" WHERE device_id = ?", (7,)),
    )

    def reject_stale_confirmation(*args, **kwargs):
        raise PermissionError("No se borró nada: cambió la cantidad de eventos.")

    monkeypatch.setattr(
        activity_deletion_service.activity_repository,
        "delete_activity_scope",
        reject_stale_confirmation,
    )

    with pytest.raises(PermissionError, match="cambió la cantidad"):
        activity_deletion_service.delete_activity(
            7, None, None, None, "BORRAR 3"
        )
