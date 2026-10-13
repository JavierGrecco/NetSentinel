import ipaddress
from types import SimpleNamespace
import socket

from netsentinel.discovery import Neighbor
from netsentinel.local_discovery import (
    ScanSubnet,
    detect_scan_subnets,
    discover_local_network,
)


def _entry(address, netmask="255.255.255.0"):
    return SimpleNamespace(family=socket.AF_INET, address=address, netmask=netmask)


def test_detects_private_ipv4_subnet_without_user_input():
    addresses = {
        "en0": [_entry("192.168.1.84")],
        "awdl0": [_entry("169.254.20.2")],
        "utun4": [_entry("10.8.0.2")],
        "lo0": [_entry("127.0.0.1")],
    }
    stats = {name: SimpleNamespace(isup=True) for name in addresses}
    result = detect_scan_subnets(addresses, stats)
    assert len(result) == 1
    assert result[0].network == ipaddress.IPv4Network("192.168.1.0/24")
    assert result[0].interface == "en0"



def test_common_linux_container_interfaces_are_not_scanned():
    interfaces = {
        "br-2d2c4d4e": [_entry("172.18.0.1")],
        "br0": [_entry("172.18.2.1")],
        "veth123456": [_entry("172.18.1.2")],
        "docker0": [_entry("172.17.0.1")],
        "podman0": [_entry("10.88.0.1")],
        "cni0": [_entry("10.244.0.1")],
        "flannel.1": [_entry("10.244.1.1")],
        "lxcbr0": [_entry("10.0.3.1")],
        "ovs-system": [_entry("10.200.0.1")],
        "virbr0": [_entry("192.168.122.1")],
    }
    stats = {name: SimpleNamespace(isup=True) for name in interfaces}

    assert detect_scan_subnets(interfaces, stats) == []


def test_container_bridge_does_not_become_second_scan_target():
    interfaces = {
        "en0": [_entry("192.168.1.20")],
        "br-a1b2c3d4": [_entry("172.18.0.1")],
        "br0": [_entry("172.20.0.1")],
        "veth0abc": [_entry("172.19.0.1")],
        "podman0": [_entry("10.88.0.1")],
    }
    stats = {name: SimpleNamespace(isup=True) for name in interfaces}

    result = detect_scan_subnets(interfaces, stats)

    assert [(str(item.network), item.interface) for item in result] == [
        ("192.168.1.0/24", "en0")
    ]

def test_duplicate_subnet_keeps_preferred_physical_interface_even_if_seen_later():
    addresses = {
        # Interface enumeration order is platform-dependent; the preferred
        # physical adapter must not be discarded because a less-preferred alias
        # happened to expose the same subnet first.
        "mystery0": [_entry("192.168.1.2")],
        "Ethernet": [_entry("192.168.1.3")],
    }
    stats = {name: SimpleNamespace(isup=True) for name in addresses}

    result = detect_scan_subnets(addresses, stats)

    assert len(result) == 1
    assert result[0].network == ipaddress.IPv4Network("192.168.1.0/24")
    assert result[0].interface == "Ethernet"
    assert result[0].local_address == "192.168.1.3"


def test_only_rfc1918_ranges_are_eligible_for_discovery():
    addresses = {
        "en0": [_entry("192.0.2.10")],       # Documentation range
        "en1": [_entry("100.64.1.10")],      # Carrier-grade NAT shared space
        "en2": [_entry("198.18.0.10")],      # Benchmarking range
        "en3": [_entry("203.0.113.10")],     # Documentation range
    }
    stats = {name: SimpleNamespace(isup=True) for name in addresses}
    assert detect_scan_subnets(addresses, stats) == []


def test_large_subnet_is_limited_to_local_slash_24():
    result = detect_scan_subnets(
        {"en0": [_entry("10.42.17.8", "255.255.0.0")]},
        {"en0": SimpleNamespace(isup=True)},
    )
    assert len(result) == 1
    assert result[0].network == ipaddress.IPv4Network("10.42.17.0/24")
    assert result[0].range_limited is True


def test_down_interfaces_are_ignored():
    result = detect_scan_subnets(
        {"en0": [_entry("192.168.1.15")]},
        {"en0": SimpleNamespace(isup=False)},
    )
    assert result == []


def test_discovery_pings_only_detected_network_and_filters_unrelated_neighbors(monkeypatch):
    network = ScanSubnet(ipaddress.IPv4Network("192.168.4.0/30"), "en0", "192.168.4.1")
    monkeypatch.setattr("netsentinel.local_discovery.detect_scan_subnets", lambda: [network])
    pinged = []
    neighbors = [
        Neighbor("192.168.4.2", "00:11:22:33:44:55", "en0", "arp"),
        Neighbor("192.168.5.9", "00:11:22:33:44:66", "en0", "arp"),
        Neighbor("fe80::1", "00:11:22:33:44:77", "awdl0", "ndp"),
    ]
    found, errors, report = discover_local_network(
        neighbor_reader=lambda: (neighbors, []),
        ping_function=lambda ip: pinged.append(ip) or ip == "192.168.4.2",
    )
    assert set(pinged) == {"192.168.4.1", "192.168.4.2"}
    assert len(found) == 1
    assert found[0].ip_address == "192.168.4.2"
    assert found[0].source == "automatic-local-network"
    assert errors == []
    assert report["addresses_checked"] == 2
    assert report["ping_responses"] == 1
    assert report["duration_seconds"] >= 0


def test_no_private_network_means_no_pings(monkeypatch):
    monkeypatch.setattr("netsentinel.local_discovery.detect_scan_subnets", lambda: [])
    pinged = []
    found, errors, report = discover_local_network(
        neighbor_reader=lambda: ([], []),
        ping_function=lambda ip: pinged.append(ip) or True,
    )
    assert found == []
    assert errors
    assert pinged == []
    assert report["addresses_checked"] == 0
