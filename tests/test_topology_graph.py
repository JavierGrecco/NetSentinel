"""Pruebas de la proyección neutral del grafo, sin navegador ni Cytoscape."""

from netsentinel.topology_graph import build_topology_graph
from netsentinel.topology_model import build_topology_model


def _scan(networks=None, scan_id=42):
    return {
        "id": scan_id,
        "started_at": "2026-10-19T10:00:00+00:00",
        "finished_at": "2026-10-19T10:00:05+00:00",
        "discovery": {
            "networks": networks if networks is not None else [
                {
                    "network": "192.168.40.0/24",
                    "interface": "en0",
                    "local_address": "192.168.40.5",
                }
            ]
        },
    }


def _observation(
    ip="192.168.40.20",
    *,
    scan_id=42,
    device_id=7,
    display_name="Portátil",
    mac_address="02:00:00:00:00:07",
    source="neighbor-table",
    observed_at="2026-10-19T10:00:02+00:00",
):
    return {
        "scan_id": scan_id,
        "device_id": device_id,
        "ip_address": ip,
        "observed_at": observed_at,
        "source": source,
        "mac_address": mac_address,
        "display_name": display_name,
        "manufacturer": "Fabricante de prueba",
        "trusted": False,
    }


def _graph(scan=None, observations=None):
    model = build_topology_model(
        scan or _scan(),
        [_observation()] if observations is None else observations,
    )
    return build_topology_graph(model)


def test_graph_has_explicit_device_subnet_nodes_and_observed_relation():
    graph = _graph()

    device = next(node for node in graph.nodes if node.kind == "device")
    subnet = next(node for node in graph.nodes if node.kind == "subnet")

    assert device.id == "device:7"
    assert device.label == "Portátil"
    assert device.detail == "192.168.40.20"
    assert device.context_label == "Ficha actual del inventario"
    assert subnet.label == "192.168.40.0/24"
    assert subnet.detail == "Interfaz en0 · Dirección local 192.168.40.5"
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == device.id
    assert edge.target == subnet.id
    assert edge.kind == "observed-subnet-membership"
    assert edge.label == "192.168.40.20"
    assert edge.sources == ("neighbor-table",)
    assert graph.stats.observed_devices == 1
    assert graph.stats.known_subnets == 1
    assert graph.stats.observed_memberships == 1
    assert graph.stats.unlinked_devices == 0


def test_unlinked_observation_remains_visible_without_fabricated_edge():
    graph = _graph(observations=[_observation(ip="8.8.8.8")])

    device_nodes = [node for node in graph.nodes if node.kind == "device"]
    subnet_nodes = [node for node in graph.nodes if node.kind == "subnet"]

    assert len(device_nodes) == 1
    assert len(subnet_nodes) == 1
    assert graph.edges == ()
    assert graph.stats.observed_devices == 1
    assert graph.stats.unlinked_devices == 1


def test_multiple_addresses_share_one_device_node_but_keep_separate_relations():
    networks = [
        {"network": "192.168.40.0/24", "interface": "en0"},
        {"network": "10.7.0.0/24", "interface": "en1"},
    ]
    observations = [
        _observation(ip="192.168.40.20"),
        _observation(
            ip="10.7.0.20",
            source="authorized-test-source",
            observed_at="2026-10-19T10:00:04+00:00",
        ),
    ]
    graph = _graph(scan=_scan(networks), observations=observations)

    device_nodes = [node for node in graph.nodes if node.kind == "device"]
    assert len(device_nodes) == 1
    assert device_nodes[0].ip_addresses == ("10.7.0.20", "192.168.40.20")
    assert len(graph.edges) == 2
    assert {edge.ip_address for edge in graph.edges} == {"10.7.0.20", "192.168.40.20"}
    assert len({edge.id for edge in graph.edges}) == 2


def test_graph_ids_and_order_are_stable_when_input_order_changes():
    scan = _scan([
        {"network": "192.168.40.0/24", "interface": "en0"},
        {"network": "10.7.0.0/24", "interface": "en1"},
    ])
    first = [
        _observation(ip="192.168.40.20", device_id=7),
        _observation(ip="10.7.0.21", device_id=8, display_name="Servidor"),
    ]
    second = list(reversed(first))
    first_graph = _graph(scan=scan, observations=first)
    second_graph = _graph(scan=scan, observations=second)

    assert [(node.id, node.kind, node.label) for node in first_graph.nodes] == [
        (node.id, node.kind, node.label) for node in second_graph.nodes
    ]
    assert [(edge.id, edge.source, edge.target) for edge in first_graph.edges] == [
        (edge.id, edge.source, edge.target) for edge in second_graph.edges
    ]


def test_missing_evidence_returns_empty_graph_with_unknown_counts():
    model = build_topology_model(_scan(), None)
    graph = build_topology_graph(model)

    assert graph.evidence_available is False
    assert graph.nodes == ()
    assert graph.edges == ()
    assert graph.stats.observed_devices is None
    assert graph.stats.known_subnets is None
    assert graph.stats.observed_memberships is None
    assert graph.stats.unlinked_devices is None
    assert any("evidencia exacta" in warning for warning in graph.warnings)


def test_successful_empty_observation_result_has_known_zero_device_count():
    model = build_topology_model(_scan(), [])
    graph = build_topology_graph(model)

    assert graph.evidence_available is True
    assert graph.stats.observed_devices == 0
    assert graph.stats.known_subnets == 1
    assert graph.stats.observed_memberships == 0
    assert graph.stats.unlinked_devices == 0
    assert len(graph.nodes) == 1
    assert graph.nodes[0].kind == "subnet"


def test_unavailable_subnet_scope_keeps_observed_devices_but_counts_unknown():
    scan = _scan()
    scan["discovery_available"] = False
    model = build_topology_model(scan, [_observation()])
    graph = build_topology_graph(model)

    assert graph.evidence_available is True
    assert graph.network_scope_available is False
    assert [node.kind for node in graph.nodes] == ["device"]
    assert graph.edges == ()
    assert graph.stats.observed_devices == 1
    assert graph.stats.known_subnets is None
    assert graph.stats.observed_memberships is None
    assert graph.stats.unlinked_devices is None
    assert any("informe de descubrimiento guardado" in warning for warning in graph.warnings)


def test_discovery_limit_stays_with_the_interface_that_reported_it():
    graph = _graph(
        scan=_scan([
            {
                "network": "192.168.40.0/24",
                "interface": "en0",
                "range_limited": True,
            },
            {
                "network": "192.168.40.0/24",
                "interface": "en1",
                "range_limited": False,
            },
        ]),
        observations=[_observation()],
    )
    subnet_by_interface = {
        node.interface: node for node in graph.nodes if node.kind == "subnet"
    }

    assert subnet_by_interface["en0"].range_limited is True
    assert subnet_by_interface["en1"].range_limited is False
