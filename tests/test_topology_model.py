"""Regresiones para la proyección aislada de topología basada en evidencia."""

from netsentinel.topology_model import build_topology_model


def scan(scan_id=7, networks=None):
    return {
        "id": scan_id,
        "started_at": "2026-10-19T10:00:00+00:00",
        "finished_at": "2026-10-19T10:00:02+00:00",
        "discovery": {
            "networks": networks if networks is not None else [
                {
                    "network": "192.168.56.12/24",
                    "interface": "en0",
                    "local_address": "192.168.56.10",
                }
            ]
        },
    }


def observation(scan_id=7, **overrides):
    values = {
        "scan_id": scan_id,
        "device_id": 12,
        "ip_address": "192.168.56.20",
        "observed_at": "2026-10-19T10:00:01+00:00",
        "source": "system-neighbor-table",
        "mac_address": "02:00:00:00:00:20",
        "display_name": "Notebook de prueba",
        "manufacturer": None,
        "trusted": False,
    }
    values.update(overrides)
    return values


def test_uses_only_the_selected_scan_and_registered_private_subnets():
    model = build_topology_model(
        scan(),
        [
            observation(),
            observation(ip_address="8.8.8.8", source="test-public"),
            observation(ip_address="192.168.90.20", source="test-outside-range"),
            observation(scan_id=8, ip_address="192.168.56.31", source="other-scan"),
        ],
    )

    assert model.evidence_available is True
    assert model.scan_id == "7"
    assert [network.cidr for network in model.networks] == ["192.168.56.0/24"]
    assert len(model.relations) == 1
    assert model.relations[0].kind == "observed-subnet-membership"
    assert model.relations[0].ip_address == "192.168.56.20"
    assert {item.ip_address for item in model.unlinked_observations} == {
        "8.8.8.8",
        "192.168.90.20",
    }
    assert any("no corresponde a la lectura seleccionada" in warning for warning in model.warnings)


def test_missing_historical_evidence_is_not_a_confirmed_zero():
    model = build_topology_model(scan(), None)

    assert model.evidence_available is False
    assert model.observations == ()
    assert model.relations == ()
    assert any("No se pudo recuperar la evidencia exacta" in warning for warning in model.warnings)


def test_empty_but_successfully_loaded_evidence_is_distinct_from_unavailable():
    model = build_topology_model(scan(), [])

    assert model.evidence_available is True
    assert model.observations == ()
    assert model.relations == ()
    assert model.warnings == ()


def test_same_device_with_multiple_addresses_keeps_one_stable_identity():
    model = build_topology_model(
        scan(networks=[
            {"network": "192.168.56.0/24", "interface": "en0"},
            {"network": "10.2.0.0/24", "interface": "en1"},
        ]),
        [
            observation(ip_address="192.168.56.20"),
            observation(ip_address="10.2.0.20", source="second-interface"),
        ],
    )

    assert len({item.device_id for item in model.observations}) == 1
    assert {relation.ip_address for relation in model.relations} == {
        "192.168.56.20",
        "10.2.0.20",
    }
    assert len(model.relations) == 2


def test_duplicate_observations_share_a_relation_without_losing_sources():
    model = build_topology_model(
        scan(),
        [
            observation(source="neighbor-table", observed_at="2026-10-19T10:00:01+00:00"),
            observation(source="authorized-adapter", observed_at="2026-10-19T10:00:02+00:00"),
        ],
    )

    assert len(model.observations) == 2
    assert len(model.relations) == 1
    assert model.relations[0].sources == ("authorized-adapter", "neighbor-table")
    assert model.relations[0].observed_at == (
        "2026-10-19T10:00:01+00:00",
        "2026-10-19T10:00:02+00:00",
    )


def test_rejects_public_and_invalid_ranges_without_fabricating_network_nodes():
    model = build_topology_model(
        scan(networks=[
            {"network": "8.8.8.0/24"},
            {"network": "not-a-cidr"},
            {"network": "192.168.56.0/24"},
        ]),
        [observation()],
    )

    assert [network.cidr for network in model.networks] == ["192.168.56.0/24"]
    assert len(model.relations) == 1
    assert any("rango IP inválido" in warning for warning in model.warnings)


def test_scan_without_id_cannot_be_presented_as_a_valid_historical_view():
    model = build_topology_model(
        {"started_at": "2026-10-19T10:00:00+00:00", "discovery": {"networks": []}},
        [observation()],
    )

    assert model.scan_id is None
    assert model.evidence_available is False
    assert model.relations == ()
    assert any("identificar la lectura seleccionada" in warning for warning in model.warnings)


def test_missing_observation_ip_is_reported_and_ignored():
    model = build_topology_model(scan(), [observation(ip_address="not-an-ip")])

    assert model.evidence_available is True
    assert model.observations == ()
    assert model.relations == ()
    assert any("dirección IP inválida" in warning for warning in model.warnings)


def test_same_cidr_on_different_interfaces_keeps_distinct_network_context():
    model = build_topology_model(
        scan(networks=[
            {"network": "192.168.56.0/24", "interface": "en0"},
            {"network": "192.168.56.0/24", "interface": "en1"},
        ]),
        [observation()],
    )

    assert len(model.networks) == 2
    assert {network.interface for network in model.networks} == {"en0", "en1"}
    assert len(model.relations) == 2
    assert len({relation.network_id for relation in model.relations}) == 2


def test_limited_discovery_scope_is_visible_in_model_warnings():
    model = build_topology_model(
        scan(networks=[
            {
                "network": "192.168.56.0/24",
                "interface": "en0",
                "range_limited": True,
            },
        ]),
        [observation()],
    )

    assert any("alcance de descubrimiento limitado" in warning for warning in model.warnings)
    assert any("ausencias no son concluyentes" in warning for warning in model.warnings)


def test_scan_errors_warn_before_treating_missing_devices_as_changes():
    partial_scan = scan()
    partial_scan["errors"] = ["El sistema omitió una parte del rango solicitado."]

    model = build_topology_model(partial_scan, [observation()])

    assert any("registró 1 aviso(s)" in warning for warning in model.warnings)
