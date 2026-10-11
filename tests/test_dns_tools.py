import socket

import pytest

from netsentinel.dns_tools import lookup_hostname


def test_lookup_hostname_deduplicates_and_sorts_addresses(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::2", 0, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.9", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.9", 0)),
    ])
    result = lookup_hostname("Example.COM.")
    assert result["hostname"] == "example.com"
    assert result["count"] == 2
    assert [item["family"] for item in result["addresses"]] == ["IPv4", "IPv6"]
    assert result["source"] == "system-resolver"


@pytest.mark.parametrize("hostname", [
    "", "https://example.com", "example.com:443", "user@example.com",
    "example.com/path", "192.0.2.1", "-bad.example", "bad..example",
])
def test_lookup_hostname_rejects_invalid_input(hostname):
    with pytest.raises(ValueError):
        lookup_hostname(hostname)


def test_lookup_hostname_reports_resolver_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("not found")
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(OSError):
        lookup_hostname("missing.example")



def test_lookup_hostname_distinguishes_missing_name(monkeypatch):
    from netsentinel.dns_tools import DNSLookupError

    def fail(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "not found")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("missing.example")
    assert error.value.kind == "not_found"


def test_lookup_hostname_distinguishes_temporary_resolver_failure(monkeypatch):
    from netsentinel.dns_tools import DNSLookupError

    def fail(*args, **kwargs):
        raise socket.gaierror(socket.EAI_AGAIN, "temporary failure")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("example.com")
    assert error.value.kind == "temporary"
