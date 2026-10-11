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



def test_reverse_lookup_uses_ipv6_sockaddr(monkeypatch):
    def resolve(sockaddr, flags):
        assert sockaddr == ("2001:db8::1", 0, 0, 0)
        assert flags == socket.NI_NAMEREQD
        return ("host.example.com", "0")
    monkeypatch.setattr(socket, "getnameinfo", resolve)
    result = reverse_lookup_ip("2001:0db8::1")
    assert result["ip"] == "2001:db8::1"
    assert result["hostname"] == "host.example.com"


def test_reverse_lookup_reports_missing_ptr(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("not found")
    monkeypatch.setattr(socket, "getnameinfo", fail)
    with pytest.raises(OSError):
        reverse_lookup_ip("192.0.2.99")



def test_reverse_lookup_classifies_missing_ptr(monkeypatch):
    from netsentinel.dns_tools import DNSLookupError

    def fail(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "not found")

    monkeypatch.setattr(socket, "getnameinfo", fail)
    with pytest.raises(DNSLookupError) as error:
        reverse_lookup_ip("192.0.2.99")
    assert error.value.kind == "not_found"


def test_reverse_lookup_classifies_temporary_resolver_failure(monkeypatch):
    from netsentinel.dns_tools import DNSLookupError

    def fail(*args, **kwargs):
        raise socket.gaierror(socket.EAI_AGAIN, "temporary failure")

    monkeypatch.setattr(socket, "getnameinfo", fail)
    with pytest.raises(DNSLookupError) as error:
        reverse_lookup_ip("192.0.2.99")
    assert error.value.kind == "temporary"
