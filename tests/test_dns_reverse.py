import pytest

import netsentinel.dns_tools as dns_tools
from netsentinel.dns_tools import DNSLookupError, reverse_lookup_ip


def test_reverse_lookup_normalizes_ip_and_hostname(monkeypatch):
    calls = []
    monkeypatch.setattr(
        dns_tools,
        "_run_resolver_child",
        lambda operation, value: calls.append((operation, value)) or {"hostname": "Router.Example.COM."},
    )
    result = reverse_lookup_ip("192.0.2.1")
    assert result["ip"] == "192.0.2.1"
    assert result["hostname"] == "router.example.com"
    assert result["record_type"] == "PTR"
    assert result["timeout_seconds"] == dns_tools.DNS_RESOLVER_TIMEOUT_SECONDS
    assert "no verifica" in result["note"]
    assert calls == [("reverse", "192.0.2.1")]


@pytest.mark.parametrize("address", ["", "example.com", "192.0.2.999", "https://192.0.2.1"])
def test_reverse_lookup_rejects_non_ip_input(address):
    with pytest.raises(ValueError):
        reverse_lookup_ip(address)


def test_reverse_lookup_normalizes_ipv6_address(monkeypatch):
    calls = []
    monkeypatch.setattr(
        dns_tools,
        "_run_resolver_child",
        lambda operation, value: calls.append((operation, value)) or {"hostname": "host.example.com"},
    )
    result = reverse_lookup_ip("2001:0db8::1")
    assert result["ip"] == "2001:db8::1"
    assert result["hostname"] == "host.example.com"
    assert calls == [("reverse", "2001:db8::1")]


def test_reverse_lookup_reports_missing_ptr(monkeypatch):
    monkeypatch.setattr(
        dns_tools,
        "_run_resolver_child",
        lambda *_args: (_ for _ in ()).throw(DNSLookupError(
            "No se encontró un registro PTR para esa dirección.", "not_found"
        )),
    )
    with pytest.raises(DNSLookupError) as error:
        reverse_lookup_ip("192.0.2.99")
    assert error.value.kind == "not_found"


def test_reverse_lookup_classifies_temporary_resolver_failure(monkeypatch):
    monkeypatch.setattr(
        dns_tools,
        "_run_resolver_child",
        lambda *_args: (_ for _ in ()).throw(DNSLookupError(
            "El resolvedor DNS no respondió a tiempo; probá nuevamente.", "temporary"
        )),
    )
    with pytest.raises(DNSLookupError) as error:
        reverse_lookup_ip("192.0.2.99")
    assert error.value.kind == "temporary"


def test_reverse_lookup_rejects_empty_child_hostname(monkeypatch):
    monkeypatch.setattr(dns_tools, "_run_resolver_child", lambda *_args: {"hostname": "."})
    with pytest.raises(DNSLookupError) as error:
        reverse_lookup_ip("192.0.2.99")
    assert error.value.kind == "resolver_error"
