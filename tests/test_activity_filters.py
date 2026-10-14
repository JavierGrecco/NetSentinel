"""Pruebas unitarias de validación de filtros de actividad."""
import pytest

from netsentinel.activity_filters import activity_delete_scope, activity_filter_values


def test_activity_filters_normalize_values_and_use_bound_parameters():
    clauses, params = activity_filter_values(
        " DNS_QUERY ", "2026-10-12", "2026-10-13", " MANUAL_IMPORT "
    )
    assert clauses == [
        "event_type = ?", "source = ?", "observed_at >= ?", "observed_at < ?"
    ]
    assert params == [
        "dns_query",
        "manual_import",
        "2026-10-12T00:00:00+00:00",
        "2026-10-14T00:00:00+00:00",
    ]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"event_type": "unknown"}, "tipo de evento"),
        ({"source": "unknown"}, "fuente de actividad"),
        ({"from_date": "12/10/2026"}, "from_date"),
        ({"from_date": "2026-10-14", "to_date": "2026-10-13"}, "fecha inicial"),
    ],
)
def test_activity_filter_rejects_invalid_values(kwargs, message):
    values = {
        "event_type": None, "from_date": None, "to_date": None, "source": None
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match=message):
        activity_filter_values(**values)


def test_activity_delete_scope_requires_explicit_bounds():
    with pytest.raises(ValueError, match="Elegí al menos un alcance"):
        activity_delete_scope(None, None, None, None)

    where, params = activity_delete_scope(7, "dns_query", None, None)
    assert where == " WHERE device_id = ? AND event_type = ?"
    assert params == (7, "dns_query")
