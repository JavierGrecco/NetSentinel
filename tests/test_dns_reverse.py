import socket

import pytest

from netsentinel.dns_tools import reverse_lookup_ip


def test_reverse_lookup_normalizes_ip_and_hostname(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getnameinfo",
        lambda address, flags: ("Router.Example.COM.", "0"),
    )
    result = reverse_lookup_ip("192.0.2.1")
    assert result["ip"] == "192.0.2.1"
    assert result["hostname"] == "router.example.com"
    assert result["record_type"] == "PTR"
    assert "no verifica" in result["note"]


@pytest.mark.parametrize("address", ["", "example.com", "192.0.2.999", "https://192.0.2.1"])
def test_reverse_lookup_rejects_non_ip_input(address):
    with pytest.raises(ValueError):
        reverse_lookup_ip(address)


def test_reverse_lookup_reports_missing_ptr(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("not found")
    monkeypatch.setattr(socket, "getnameinfo", fail)
    with pytest.raises(OSError):
        reverse_lookup_ip("192.0.2.99")
