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
