from netsentinel.discovery import Neighbor, normalize_mac, parse_neighbor_output


def test_normalize_mac_accepts_colons_and_hyphens():
    assert normalize_mac("aa-bb-cc-dd-ee-ff") == "AA:BB:CC:DD:EE:FF"
    assert normalize_mac("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"


def test_normalize_mac_rejects_invalid_values():
    assert normalize_mac("not-a-mac") is None
    assert normalize_mac("01:02:03") is None


def test_parse_linux_ip_neigh():
    output = "192.168.1.1 dev en0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n"
    result = parse_neighbor_output(output, "Linux")
    assert len(result) == 1
    assert result[0].ip_address == "192.168.1.1"
    assert result[0].mac_address == "AA:BB:CC:DD:EE:FF"
    assert result[0].interface == "en0"


def test_parse_macos_arp_output():
    output = "? (192.168.0.1) at 00:11:22:33:44:55 on en0 ifscope [ethernet]\n"
    result = parse_neighbor_output(output, "Darwin")
    assert len(result) == 1
    assert result[0].ip_address == "192.168.0.1"
    assert result[0].interface == "en0"


def test_parse_windows_arp_output():
    output = "Interface: 192.168.1.20 --- 0x7\n  Internet Address      Physical Address      Type\n  192.168.1.1           aa-bb-cc-dd-ee-ff     dynamic\n"
    result = parse_neighbor_output(output, "Windows")
    assert len(result) == 1
    assert result[0].mac_address == "AA:BB:CC:DD:EE:FF"


def test_parser_deduplicates_same_ip_and_mac():
    output = "192.168.1.1 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE\n192.168.1.1 (192.168.1.1) at aa:bb:cc:dd:ee:ff on eth0\n"
    result = parse_neighbor_output(output, "Linux")
    assert len(result) == 1


def test_parse_ipv6_neighbor_and_preserve_source():
    output = "fe80::1 dev en0 lladdr 00:11:22:33:44:55 router STALE\n"
    result = parse_neighbor_output(output, "Linux", "ip-neigh-ipv6")
    assert len(result) == 1
    assert result[0].ip_address == "fe80::1"
    assert result[0].source == "ip-neigh-ipv6"


def test_parser_ignores_apple_peer_to_peer_interfaces():
    output = """fe80::c444:b4ff:fe6a:ddc0 dev awdl0 lladdr c6:44:b4:6a:dd:c0 STALE
fe80::1 dev llw0 lladdr 00:11:22:33:44:55 STALE
192.168.1.1 dev en0 lladdr aa:bb:cc:dd:ee:ff REACHABLE"""
    result = parse_neighbor_output(output, "Darwin")
    assert [(item.ip_address, item.interface) for item in result] == [("192.168.1.1", "en0")]


def test_parser_ignores_multicast_and_incomplete_neighbors():
    output = "192.168.1.10 dev eth0 lladdr 01:00:5e:00:00:01 REACHABLE\n192.168.1.11 dev eth0 FAILED\n"
    assert parse_neighbor_output(output, "Linux") == []


def test_ndp_output_is_parsed():
    output = "fe80::1%en0 00:11:22:33:44:55 en0 23h59m R\n"
    result = parse_neighbor_output(output, "Darwin", "ndp")
    assert len(result) == 1
    assert result[0].interface == "en0"


def test_one_provider_failure_does_not_stop_other_providers():
    from netsentinel.discovery import discover_from_providers

    class FailingProvider:
        name = "failing-fixture"

        def discover(self):
            raise RuntimeError("fixture error")

    class WorkingProvider:
        name = "working-fixture"

        def discover(self):
            from netsentinel.discovery import Neighbor
            return [Neighbor("192.168.1.5", "00:11:22:33:44:55", "eth0", self.name)], []

    neighbors, errors = discover_from_providers([FailingProvider(), WorkingProvider()])
    assert len(neighbors) == 1
    assert neighbors[0].source == "working-fixture"
    assert errors and "fixture error" in errors[0]


def test_duplicate_provider_results_are_merged():
    from netsentinel.discovery import discover_from_providers

    class Provider:
        def __init__(self, name, neighbor):
            self.name = name
            self.neighbor = neighbor

        def discover(self):
            return [self.neighbor], []

    one = Provider("first", Neighbor("192.168.1.5", "00:11:22:33:44:55", None, "first"))
    two = Provider("second", Neighbor("192.168.1.5", "00:11:22:33:44:55", "eth0", "second"))
    neighbors, errors = discover_from_providers([one, two])
    assert not errors
    assert len(neighbors) == 1
    assert neighbors[0].interface == "eth0"
