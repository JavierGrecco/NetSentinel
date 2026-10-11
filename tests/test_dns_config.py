from pathlib import Path

import netsentinel.dns_config as dns_config


def test_clean_servers_validates_deduplicates_ipv4_and_ipv6():
    assert dns_config._clean_servers("192.168.1.1, 192.168.1.1; 2001:db8::1 invalid") == [
        "192.168.1.1",
        "2001:db8::1",
    ]


def test_read_resolv_conf_reads_nameserver_lines_and_ignores_comments(tmp_path: Path):
    config = tmp_path / "resolv.conf"
    config.write_text(
        "# generated file\n"
        "nameserver 192.168.1.1\n"
        "nameserver 2001:db8::53 # IPv6 resolver\n"
        "search example.test\n"
        "nameserver not-an-ip\n",
        encoding="utf-8",
    )
    assert dns_config._read_resolv_conf(config) == ["192.168.1.1", "2001:db8::53"]


def test_read_resolv_conf_handles_missing_file(tmp_path: Path):
    assert dns_config._read_resolv_conf(tmp_path / "missing.conf") == []


def test_get_dns_configuration_documents_empty_detection(monkeypatch):
    monkeypatch.setattr(dns_config.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(dns_config, "_read_resolv_conf", lambda: [])
    result = dns_config.get_dns_configuration()
    assert result["platform"] == "darwin"
    assert result["servers"] == []
    assert result["detected"] is False
    assert "VPN" in result["note"]


def test_get_dns_configuration_uses_windows_registry_reader(monkeypatch):
    monkeypatch.setattr(dns_config.platform, "system", lambda: "Windows")
    monkeypatch.setattr(dns_config, "_windows_dns_servers", lambda: ["192.0.2.53"])
    result = dns_config.get_dns_configuration()
    assert result["source"] == "windows-registry"
    assert result["servers"] == ["192.0.2.53"]
    assert result["detected"] is True


def test_windows_dns_reader_includes_ipv4_and_ipv6_interface_values(monkeypatch):
    import sys
    from types import SimpleNamespace

    class Key:
        def __init__(self, values=None, children=None):
            self.values = values or {}
            self.children = children or {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    hklm = object()
    registry = {
        r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters": Key(),
        r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters": Key(),
        r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces": Key(
            children={"ipv4-if": Key({"DhcpNameServer": "192.0.2.53"})}
        ),
        r"SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters\Interfaces": Key(
            children={"ipv6-if": Key({"NameServer": "2001:db8::53"})}
        ),
    }

    def open_key(_root, path):
        if path not in registry:
            raise OSError("missing key")
        return registry[path]

    def query_info_key(key):
        return (len(key.children), 0, 0)

    def enum_key(key, index):
        return list(key.children)[index]

    def query_value_ex(key, name):
        if name not in key.values:
            raise OSError("missing value")
        return key.values[name], 1

    original_open_key = open_key

    def open_key_with_child(root_or_key, path):
        if isinstance(root_or_key, Key) and path in root_or_key.children:
            return root_or_key.children[path]
        return original_open_key(root_or_key, path)

    fake_winreg = SimpleNamespace(
        HKEY_LOCAL_MACHINE=hklm,
        OpenKey=open_key_with_child,
        QueryInfoKey=query_info_key,
        EnumKey=enum_key,
        QueryValueEx=query_value_ex,
    )
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    assert dns_config._windows_dns_servers() == ["192.0.2.53", "2001:db8::53"]
