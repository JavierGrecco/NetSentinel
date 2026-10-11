"""Descubrimiento local automático, limitado a subredes IPv4 privadas conectadas."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import ipaddress
import platform
import socket
import subprocess
from typing import Callable

import psutil

from .discovery import Neighbor, read_neighbor_table


MAX_NETWORKS = 2
MAX_HOSTS_PER_NETWORK = 254
MAX_WORKERS = 24
PING_TIMEOUT_SECONDS = 1.6

# Interfaces virtuales, túneles y enlaces entre dispositivos Apple no son redes LAN
# físicas adecuadas para un descubrimiento general del hogar/oficina.
_EXCLUDED_PREFIXES = (
    "lo", "awdl", "llw", "utun", "bridge", "vmnet", "vmenet", "docker",
    "vboxnet", "virbr", "tailscale", "wg", "tun", "tap", "gif", "stf",
    "anpi", "ap", "p2p",
)


@dataclass(frozen=True, slots=True)
class ScanSubnet:
    network: ipaddress.IPv4Network
    interface: str
    local_address: str
    range_limited: bool = False


def detect_scan_subnets(
    interface_addresses: dict | None = None,
    interface_stats: dict | None = None,
) -> list[ScanSubnet]:
    """Detecta como máximo dos subredes privadas activas sin pedir datos al usuario.

    Para una red mayor que /24 solo se examina el bloque /24 donde está la IP local.
    No incluye loopback, link-local, túneles ni interfaces virtuales conocidas.
    """
    addresses = interface_addresses if interface_addresses is not None else psutil.net_if_addrs()
    stats = interface_stats if interface_stats is not None else psutil.net_if_stats()
    candidates: list[tuple[int, str, ScanSubnet]] = []
    seen_networks: set[str] = set()

    for interface, entries in addresses.items():
        name = interface.strip()
        lowered = name.lower()
        if any(lowered.startswith(prefix) for prefix in _EXCLUDED_PREFIXES):
            continue
        status = stats.get(interface)
        if status is not None and not status.isup:
            continue

        for entry in entries:
            if entry.family != socket.AF_INET or not entry.address or not entry.netmask:
                continue
            try:
                local_ip = ipaddress.IPv4Address(entry.address)
                if (
                    not local_ip.is_private
                    or local_ip.is_loopback
                    or local_ip.is_link_local
                    or local_ip.is_multicast
                    or local_ip.is_unspecified
                ):
                    continue
                actual_network = ipaddress.IPv4Network(f"{local_ip}/{entry.netmask}", strict=False)
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError):
                continue

            if actual_network.prefixlen >= 31:
                continue

            limited = actual_network.num_addresses > 256
            target_network = (
                ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
                if limited
                else actual_network
            )
            key = str(target_network)
            if key in seen_networks:
                continue
            seen_networks.add(key)

            # Prefer common physical interface names where several adapters exist.
            preferred = 0 if lowered.startswith(("en", "eth", "wlan", "wi-fi", "ethernet", "wlp", "eno", "ens")) else 1
            candidates.append((
                preferred,
                name,
                ScanSubnet(target_network, name, str(local_ip), limited),
            ))

    candidates.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in candidates[:MAX_NETWORKS]]


def _ping_once(address: str, system: str | None = None) -> bool:
    """Envía como máximo un ping a una dirección generada desde la subred local."""
    actual_system = system or platform.system()
    if actual_system == "Windows":
        command = ["ping", "-n", "1", "-w", "600", address]
    elif actual_system == "Darwin":
        command = ["ping", "-n", "-c", "1", "-W", "500", address]
    else:
        command = ["ping", "-n", "-c", "1", "-W", "1", address]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=PING_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def discover_local_network(
    *,
    neighbor_reader: Callable[[], tuple[list[Neighbor], list[str]]] | None = None,
    ping_function: Callable[[str], bool] | None = None,
) -> tuple[list[Neighbor], list[str], dict]:
    """Detecta las subredes locales, las sondea de forma acotada y filtra el inventario.

    La llamada debe hacerse por acción explícita del usuario: el barrido genera tráfico
    en las redes privadas locales detectadas, pero no modifica equipos ni consulta Internet.
    """
    errors: list[str] = []
    try:
        subnets = detect_scan_subnets()
    except Exception as exc:
        subnets = []
        errors.append(f"No se pudieron detectar las redes locales: {type(exc).__name__}.")

    report = {
        "networks": [
            {
                "network": str(item.network),
                "interface": item.interface,
                "local_address": item.local_address,
                "range_limited": item.range_limited,
            }
            for item in subnets
        ],
        "addresses_checked": 0,
        "ping_responses": 0,
        "scope": "Solo subredes IPv4 privadas detectadas automáticamente; máximo dos segmentos y hasta 254 direcciones por segmento.",
    }
    if not subnets:
        errors.append(
            "No se encontró una subred IPv4 privada activa en una interfaz compatible. "
            "No se envió ningún ping de descubrimiento."
        )
        return [], errors, report

    addresses: list[str] = []
    for subnet in subnets:
        addresses.extend(str(host) for host in subnet.network.hosts())
    # Defensive second limit; the current per-subnet policy already bounds this to 508.
    addresses = addresses[: MAX_NETWORKS * MAX_HOSTS_PER_NETWORK]
    report["addresses_checked"] = len(addresses)

    ping = ping_function or _ping_once
    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="netsentinel-discovery") as executor:
        responses = list(executor.map(ping, addresses))
    report["ping_responses"] = sum(bool(value) for value in responses)

    reader = neighbor_reader or read_neighbor_table
    try:
        neighbors, read_errors = reader()
    except Exception as exc:
        neighbors, read_errors = [], [f"No se pudo leer la tabla local de vecinos: {type(exc).__name__}."]
    errors.extend(read_errors)

    networks = [item.network for item in subnets]
    filtered: dict[tuple[str, str], Neighbor] = {}
    for item in neighbors:
        try:
            address = ipaddress.ip_address(item.ip_address.split("%", 1)[0])
        except ValueError:
            continue
        if not isinstance(address, ipaddress.IPv4Address):
            continue
        if not any(address in network for network in networks):
            continue
        filtered[(str(address), item.mac_address)] = Neighbor(
            str(address),
            item.mac_address,
            item.interface,
            "automatic-local-network",
        )

    results = sorted(
        filtered.values(),
        key=lambda item: (int(ipaddress.IPv4Address(item.ip_address)), item.mac_address),
    )
    return results, errors, report
