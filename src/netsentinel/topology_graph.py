"""Proyección neutral del modelo de topología hacia nodos y relaciones.

Este módulo no conoce Cytoscape, HTML, SQLite ni FastAPI. Su trabajo es
explicar los elementos del grafo y su procedencia; la interfaz decidirá cómo
dibujarlos sin cambiar el significado de los datos.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import quote

from .topology_model import TopologyModel, TopologyNetwork, TopologyObservation


@dataclass(frozen=True, slots=True)
class TopologyGraphObservation:
    """Procedencia de una dirección registrada en la lectura seleccionada."""

    ip_address: str
    sources: tuple[str, ...] = ()
    observed_at: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopologyGraphNode:
    """Nodo que puede representar un dispositivo observado o una subred conocida."""

    id: str
    kind: str
    label: str
    detail: str = ""
    device_id: str | None = None
    network_id: str | None = None
    ip_addresses: tuple[str, ...] = ()
    observations: tuple[TopologyGraphObservation, ...] = ()
    mac_address: str | None = None
    manufacturer: str | None = None
    trusted: bool | None = None
    interface: str | None = None
    context_label: str | None = None


@dataclass(frozen=True, slots=True)
class TopologyGraphEdge:
    """Relación del grafo con un significado explícito y su evidencia."""

    id: str
    source: str
    target: str
    kind: str
    label: str
    ip_address: str
    sources: tuple[str, ...] = ()
    observed_at: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopologyGraphStats:
    """Contadores; None significa que no hay evidencia suficiente para contarlos."""

    observed_devices: int | None
    known_subnets: int | None
    observed_memberships: int | None
    unlinked_devices: int | None


@dataclass(frozen=True, slots=True)
class TopologyGraph:
    """Resultado listo para representar, pero independiente de cualquier biblioteca."""

    scan_id: str | None
    captured_at: str | None
    evidence_available: bool
    nodes: tuple[TopologyGraphNode, ...]
    edges: tuple[TopologyGraphEdge, ...]
    stats: TopologyGraphStats
    warnings: tuple[str, ...] = ()
    network_scope_available: bool = False


def _stable_id(prefix: str, *parts: str) -> str:
    """Crea un ID determinista; no depende del orden ni de la dirección de memoria."""
    return prefix + ":" + ":".join(quote(part, safe="") for part in parts)


def _device_label(observations: tuple[TopologyObservation, ...]) -> tuple[str, str]:
    """Elige una etiqueta legible y separa de ella las direcciones observadas."""
    display_name = next(
        (item.display_name for item in observations if item.display_name),
        None,
    )
    mac_address = next(
        (item.mac_address for item in observations if item.mac_address),
        None,
    )
    device_id = observations[0].device_id
    if display_name:
        label = display_name
    elif mac_address:
        label = mac_address
    else:
        label = "Dispositivo " + device_id.removeprefix("device:")
    addresses = tuple(sorted({item.ip_address for item in observations}))
    return label, ", ".join(addresses)


def _network_node(network: TopologyNetwork) -> TopologyGraphNode:
    interface_detail = "Interfaz " + network.interface if network.interface else ""
    local_detail = "Dirección local " + network.local_address if network.local_address else ""
    detail = " · ".join(part for part in (interface_detail, local_detail) if part)
    return TopologyGraphNode(
        id=network.id,
        kind="subnet",
        label=network.cidr,
        detail=detail,
        network_id=network.id,
        interface=network.interface,
    )


def build_topology_graph(model: TopologyModel) -> TopologyGraph:
    """Convierte el modelo de evidencia a nodos/enlaces sin fabricar relaciones.

    Un equipo observado fuera de las subredes registradas sigue siendo visible,
    pero queda sin enlaces. Una fuente histórica no disponible devuelve un grafo
    vacío y contadores desconocidos: no se representa como una red vacía confirmada.
    """
    if not model.evidence_available:
        return TopologyGraph(
            scan_id=model.scan_id,
            captured_at=model.captured_at,
            evidence_available=False,
            nodes=(),
            edges=(),
            stats=TopologyGraphStats(
                observed_devices=None,
                known_subnets=None,
                observed_memberships=None,
                unlinked_devices=None,
            ),
            warnings=model.warnings,
            network_scope_available=model.network_scope_available,
        )

    grouped: dict[str, list[TopologyObservation]] = defaultdict(list)
    for observation in model.observations:
        grouped[observation.device_id].append(observation)

    nodes: list[TopologyGraphNode] = (
        [_network_node(network) for network in model.networks]
        if model.network_scope_available
        else []
    )
    for device_id in sorted(grouped):
        observations = tuple(sorted(
            grouped[device_id],
            key=lambda item: (item.ip_address, item.observed_at or "", item.source or ""),
        ))
        label, detail = _device_label(observations)
        # Estos atributos proceden del registro actual de inventario, no de
        # una fotografía histórica inmutable de la ficha.
        context = "Ficha actual del inventario"
        nodes.append(TopologyGraphNode(
            id=device_id,
            kind="device",
            label=label,
            detail=detail,
            device_id=device_id,
            ip_addresses=tuple(sorted({item.ip_address for item in observations})),
            observations=address_evidence,
            mac_address=next((item.mac_address for item in observations if item.mac_address), None),
            manufacturer=next((item.manufacturer for item in observations if item.manufacturer), None),
            trusted=next((item.trusted for item in observations if item.trusted is not None), None),
            context_label=context,
        ))

    edges: list[TopologyGraphEdge] = []
    observed_device_ids = set(grouped)
    linked_device_ids: set[str] = set()
    for relation in (model.relations if model.network_scope_available else ()):
        # Defensive validation: do not create dangling edges if a malformed
        # model is passed from future code or an incomplete fixture.
        if relation.device_id not in observed_device_ids:
            continue
        if not any(network.id == relation.network_id for network in model.networks):
            continue
        edges.append(TopologyGraphEdge(
            id=_stable_id("membership", relation.device_id, relation.network_id, relation.ip_address),
            source=relation.device_id,
            target=relation.network_id,
            kind=relation.kind,
            label=relation.ip_address,
            ip_address=relation.ip_address,
            sources=relation.sources,
            observed_at=relation.observed_at,
        ))
        linked_device_ids.add(relation.device_id)

    nodes.sort(key=lambda node: (node.kind, node.label.casefold(), node.id))
    edges.sort(key=lambda edge: (edge.source, edge.target, edge.ip_address, edge.id))
    return TopologyGraph(
        scan_id=model.scan_id,
        captured_at=model.captured_at,
        evidence_available=True,
        nodes=tuple(nodes),
        edges=tuple(edges),
        stats=TopologyGraphStats(
            observed_devices=len(grouped),
            known_subnets=len(model.networks) if model.network_scope_available else None,
            observed_memberships=len(edges) if model.network_scope_available else None,
            unlinked_devices=(
                len(observed_device_ids - linked_device_ids)
                if model.network_scope_available else None
            ),
        ),
        warnings=model.warnings,
        network_scope_available=model.network_scope_available,
    )
