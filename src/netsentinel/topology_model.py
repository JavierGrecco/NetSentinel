"""Modelo puro para construir una topología a partir de una lectura guardada.

No consulta SQLite ni conoce la interfaz. Usa las observaciones asociadas a la
lectura elegida; nunca completa una lectura histórica con direcciones actuales.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import ipaddress
from typing import Any


_RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


@dataclass(frozen=True, slots=True)
class TopologyNetwork:
    """Subred privada registrada en la lectura, con el contexto conocido."""

    id: str
    cidr: str
    interface: str | None = None
    local_address: str | None = None
    range_limited: bool = False


@dataclass(frozen=True, slots=True)
class TopologyObservation:
    """Observación de un dispositivo guardada por una lectura concreta."""

    device_id: str
    ip_address: str
    observed_at: str | None
    source: str | None
    mac_address: str | None = None
    display_name: str | None = None
    manufacturer: str | None = None
    trusted: bool | None = None


@dataclass(frozen=True, slots=True)
class TopologyRelation:
    """Pertenencia observada entre un dispositivo, una IP y una subred."""

    device_id: str
    network_id: str
    ip_address: str
    kind: str = "observed-subnet-membership"
    sources: tuple[str, ...] = ()
    observed_at: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopologyModel:
    """Lectura y evidencia para topología, con alcance histórico explícito.

    evidence_available describe si se recuperaron las observaciones de la lectura.
    network_scope_available describe si el informe de redes se pudo interpretar.
    Son dimensiones distintas: conocer los dispositivos no garantiza conocer el
    rango de red donde deben agruparse.
    """

    scan_id: str | None
    captured_at: str | None
    evidence_available: bool
    network_scope_available: bool = False
    networks: tuple[TopologyNetwork, ...] = ()
    observations: tuple[TopologyObservation, ...] = ()
    relations: tuple[TopologyRelation, ...] = ()
    unlinked_observations: tuple[TopologyObservation, ...] = ()
    warnings: tuple[str, ...] = ()


def _text(value: Any) -> str | None:
    """Devuelve texto limpio o None para valores vacíos/no textuales."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _scan_identifier(scan: Mapping[str, Any] | None) -> str | None:
    if not isinstance(scan, Mapping):
        return None
    value = scan.get("id")
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def _is_rfc1918(network: ipaddress.IPv4Network | ipaddress.IPv6Network) -> bool:
    return network.version == 4 and any(
        network.subnet_of(private) for private in _RFC1918_NETWORKS
    )


def _read_networks(
    scan: Mapping[str, Any],
) -> tuple[tuple[TopologyNetwork, ...], tuple[str, ...]]:
    if scan.get("discovery_available") is False:
        return (), ("No se pudo interpretar el informe de descubrimiento guardado.",)

    discovery = scan.get("discovery")
    raw_networks = discovery.get("networks") if isinstance(discovery, Mapping) else None
    if not isinstance(raw_networks, list):
        return (), ("La lectura no contiene una lista de subredes registrada.",)

    networks: list[TopologyNetwork] = []
    seen: set[tuple[str, str | None]] = set()
    warnings: list[str] = []
    for item in raw_networks:
        if not isinstance(item, Mapping):
            warnings.append("Se ignoró una entrada de subred con formato inválido.")
            continue
        if item.get("range_limited") is True:
            warnings.append(
                "Al menos una subred tuvo alcance de descubrimiento limitado; "
                "las ausencias no son concluyentes."
            )
        raw_cidr = _text(item.get("network"))
        if raw_cidr is None:
            warnings.append("Se ignoró una subred sin rango registrado.")
            continue
        try:
            parsed = ipaddress.ip_network(raw_cidr, strict=False)
        except ValueError:
            warnings.append("Se ignoró una subred con un rango IP inválido.")
            continue
        if not _is_rfc1918(parsed):
            # La topología LAN actual solo representa rangos privados IPv4.
            continue
        cidr = parsed.with_prefixlen
        interface = _text(item.get("interface"))
        identity = (cidr, interface)
        if identity in seen:
            continue
        seen.add(identity)
        network_id = f"subnet:{cidr}" if interface is None else f"subnet:{cidr}@{interface}"
        networks.append(
            TopologyNetwork(
                id=network_id,
                cidr=cidr,
                interface=interface,
                local_address=_text(item.get("local_address")),
                range_limited=item.get("range_limited") is True,
            )
        )
    # Una ordenación estable evita que el grafo cambie solo porque cambió
    # el orden en que el sistema operativo informó sus interfaces.
    networks.sort(key=lambda network: (network.cidr, network.interface or ""))
    return tuple(networks), tuple(dict.fromkeys(warnings))


def _observation(row: Mapping[str, Any]) -> TopologyObservation | None:
    raw_ip = _text(row.get("ip_address"))
    if raw_ip is None:
        return None
    try:
        normalised_ip = str(ipaddress.ip_address(raw_ip))
    except ValueError:
        return None

    raw_device_id = row.get("device_id")
    if raw_device_id is None or str(raw_device_id).strip() == "":
        # No usar una identidad derivada de memoria: no es estable entre ejecuciones.
        mac = _text(row.get("mac_address"))
        if mac is not None:
            device_id = "mac:" + mac.upper().replace("-", ":")
        else:
            device_id = "ip:" + normalised_ip
    else:
        device_id = "device:" + str(raw_device_id).strip()

    trusted = row.get("trusted")
    return TopologyObservation(
        device_id=device_id,
        ip_address=normalised_ip,
        observed_at=_text(row.get("observed_at")),
        source=_text(row.get("source")),
        mac_address=_text(row.get("mac_address")),
        display_name=_text(row.get("display_name")),
        manufacturer=_text(row.get("manufacturer")),
        trusted=trusted if isinstance(trusted, bool) else None,
    )


def build_topology_model(
    scan: Mapping[str, Any] | None,
    observations: Sequence[Mapping[str, Any]] | None,
) -> TopologyModel:
    """Construye una topología sin inventar enlaces ni completar datos históricos.

    Si observations es None, la fuente histórica no pudo recuperarse. Una lista
    vacía significa que la consulta sí respondió, pero no encontró observaciones.
    Esos estados se mantienen diferenciados.
    """
    scan_id = _scan_identifier(scan)
    if scan_id is None:
        return TopologyModel(
            scan_id=None,
            captured_at=None,
            evidence_available=False,
            warnings=("No se puede identificar la lectura seleccionada.",),
        )

    assert isinstance(scan, Mapping)
    captured_at = _text(scan.get("finished_at")) or _text(scan.get("started_at"))
    discovery = scan.get("discovery")
    network_scope_available = (
        scan.get("discovery_available") is not False
        and isinstance(discovery, Mapping)
        and isinstance(discovery.get("networks"), list)
    )
    networks, network_warnings = _read_networks(scan)
    scan_errors = scan.get("errors")
    if isinstance(scan_errors, list) and scan_errors:
        network_warnings = tuple(dict.fromkeys((
            *network_warnings,
            f"La lectura registró {len(scan_errors)} aviso(s); revisá su alcance antes de interpretar ausencias.",
        )))
    if scan.get("errors_available") is False:
        network_warnings = tuple(dict.fromkeys((
            *network_warnings,
            "No se pudieron interpretar los avisos guardados de la lectura.",
        )))

    if observations is None:
        return TopologyModel(
            scan_id=scan_id,
            captured_at=captured_at,
            evidence_available=False,
            network_scope_available=network_scope_available,
            networks=networks,
            warnings=tuple(dict.fromkeys((
                *network_warnings,
                "No se pudo recuperar la evidencia exacta de esta lectura.",
            ))),
        )

    warnings = list(network_warnings)
    normalised: list[TopologyObservation] = []
    for row in observations:
        if not isinstance(row, Mapping):
            warnings.append("Se ignoró una observación con formato inválido.")
            continue
        row_scan_id = row.get("scan_id")
        if row_scan_id is None or str(row_scan_id).strip() != scan_id:
            warnings.append("Se ignoró una observación que no corresponde a la lectura seleccionada.")
            continue
        item = _observation(row)
        if item is None:
            warnings.append("Se ignoró una observación con dirección IP inválida.")
            continue
        normalised.append(item)

    parsed_networks = tuple(
        (network, ipaddress.ip_network(network.cidr))
        for network in networks
    )
    relations_by_key: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    unlinked: list[TopologyObservation] = []
    if network_scope_available:
        for observation in normalised:
            address = ipaddress.ip_address(observation.ip_address)
            matched_networks = [
                network for network, parsed in parsed_networks
                if address.version == 4 and address in parsed
            ]
            if not matched_networks:
                unlinked.append(observation)
                continue
            for network in matched_networks:
                key = (observation.device_id, network.id, observation.ip_address)
                values = relations_by_key.setdefault(key, {"sources": set(), "times": set()})
                if observation.source:
                    values["sources"].add(observation.source)
                if observation.observed_at:
                    values["times"].add(observation.observed_at)

    relations = tuple(
        TopologyRelation(
            device_id=device_id,
            network_id=network_id,
            ip_address=ip_address_value,
            sources=tuple(sorted(values["sources"])),
            observed_at=tuple(sorted(values["times"])),
        )
        for (device_id, network_id, ip_address_value), values in sorted(relations_by_key.items())
    )
    return TopologyModel(
        scan_id=scan_id,
        captured_at=captured_at,
        evidence_available=True,
        network_scope_available=network_scope_available,
        networks=networks,
        observations=tuple(normalised),
        relations=relations,
        unlinked_observations=tuple(unlinked),
        warnings=tuple(dict.fromkeys(warnings)),
    )
