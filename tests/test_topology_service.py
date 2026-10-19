"""Pruebas de integración del servicio de topología con la persistencia actual."""

from pathlib import Path

from netsentinel import database
from netsentinel.network_models import Neighbor
from netsentinel.topology_service import load_topology_for_scan


def _record_scan(path: Path, ip: str, source: str = "fixture") -> int:
    result = database.record_scan(
        [Neighbor(ip, "02:00:00:00:00:20", "en0", source)],
        path=path,
        discovery={
            "networks": [
                {
                    "network": "192.168.56.0/24",
                    "interface": "en0",
                    "local_address": "192.168.56.10",
                    "range_limited": False,
                }
            ],
            "scope": "Fixture sintética; no representa una red real.",
        },
    )
    return int(result["scan_id"])


def test_service_reads_the_exact_historical_observation(tmp_path: Path):
    path = tmp_path / "topology.sqlite3"
    database.initialize(path)
    old_scan_id = _record_scan(path, "192.168.56.20")
    _record_scan(path, "192.168.56.30")

    model = load_topology_for_scan(old_scan_id, path=path)

    assert model.scan_id == str(old_scan_id)
    assert model.evidence_available is True
    assert [item.ip_address for item in model.observations] == ["192.168.56.20"]
    assert [item.ip_address for item in model.relations] == ["192.168.56.20"]
    assert model.networks[0].cidr == "192.168.56.0/24"
    assert model.networks[0].interface == "en0"


def test_service_distinguishes_an_unknown_scan_from_empty_observations(tmp_path: Path):
    path = tmp_path / "topology.sqlite3"
    database.initialize(path)

    model = load_topology_for_scan(999, path=path)

    assert model.scan_id is None
    assert model.evidence_available is False
    assert model.observations == ()
    assert model.relations == ()
    assert "No se encontró la lectura solicitada." in model.warnings


def test_service_flags_a_corrupt_discovery_report(tmp_path: Path):
    path = tmp_path / "topology.sqlite3"
    database.initialize(path)
    scan_id = _record_scan(path, "192.168.56.20")

    with database.connect(path) as db:
        db.execute(
            "UPDATE scans SET discovery_json = ? WHERE id = ?",
            ("{not-valid-json", scan_id),
        )

    model = load_topology_for_scan(scan_id, path=path)

    assert model.evidence_available is True
    assert model.network_scope_available is False
    assert model.networks == ()
    assert model.relations == ()
    assert model.unlinked_observations == ()
    assert any("No se pudo interpretar el informe" in warning for warning in model.warnings)
