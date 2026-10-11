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
