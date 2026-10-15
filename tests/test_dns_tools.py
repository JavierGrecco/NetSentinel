import json
import subprocess
import socket

import pytest

import netsentinel.dns_tools as dns_tools
from netsentinel.dns_tools import DNSLookupError, lookup_hostname


def test_lookup_hostname_deduplicates_and_sorts_addresses(monkeypatch):
    calls = []
    monkeypatch.setattr(
        dns_tools,
        "_run_resolver_child",
        lambda operation, value: calls.append((operation, value)) or {
            "addresses": ["2001:db8::2", "192.0.2.9", "192.0.2.9", "2001:0db8::2"],
        },
    )
    result = lookup_hostname("Example.COM.")
    assert result["hostname"] == "example.com"
    assert result["count"] == 2
    assert [item["ip"] for item in result["addresses"]] == ["192.0.2.9", "2001:db8::2"]
    assert [item["family"] for item in result["addresses"]] == ["IPv4", "IPv6"]
    assert result["source"] == "system-resolver"
    assert result["timeout_seconds"] == dns_tools.DNS_RESOLVER_TIMEOUT_SECONDS
    assert calls == [("forward", "example.com")]


@pytest.mark.parametrize("hostname", [
    "", "https://example.com", "example.com:443", "user@example.com",
    "example.com/path", "example.com..", "192.0.2.1", "-bad.example", "bad..example",
])
def test_lookup_hostname_rejects_invalid_input(hostname):
    with pytest.raises(ValueError):
        lookup_hostname(hostname)


def test_lookup_hostname_rejects_name_that_exceeds_dns_limit_after_idna():
    hostname = ".".join(["é" * 48] * 5)
    encoded = ".".join(label.encode("idna").decode("ascii") for label in hostname.split("."))
    assert len(hostname) <= 253
    assert all(len(label) <= 63 for label in encoded.split("."))
    assert len(encoded) > 253

    with pytest.raises(ValueError, match="nombre de host"):
        dns_tools._normalize_hostname(hostname)


@pytest.mark.parametrize(
    ("error_code", "expected_kind"),
    [
        (socket.EAI_NONAME, "not_found"),
        (socket.EAI_AGAIN, "temporary"),
    ],
)
def test_lookup_hostname_classifies_child_resolver_errors(monkeypatch, error_code, expected_kind):
    def child_result(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            2,
            stdout=json.dumps({"error": "gaierror", "errno": error_code}),
            stderr="",
        )

    monkeypatch.setattr(dns_tools.subprocess, "run", child_result)
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("example.com")
    assert error.value.kind == expected_kind


def test_lookup_hostname_enforces_terminable_timeout(monkeypatch):
    calls = {}

    def timeout_child(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(dns_tools.subprocess, "run", timeout_child)
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("example.com")
    assert error.value.kind == "temporary"
    assert "no respondió a tiempo" in str(error.value)
    assert calls["command"][0] == dns_tools.sys.executable
    assert calls["command"][1] == "-c"
    assert calls["command"][-2:] == ["forward", "example.com"]
    assert calls["kwargs"]["timeout"] == dns_tools.DNS_RESOLVER_TIMEOUT_SECONDS
    assert calls["kwargs"]["capture_output"] is True
    assert calls["kwargs"]["check"] is False


def test_lookup_hostname_rejects_malformed_child_output(monkeypatch):
    monkeypatch.setattr(
        dns_tools.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, stdout="not-json", stderr=""),
    )
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("example.com")
    assert error.value.kind == "resolver_error"


def test_lookup_hostname_rejects_non_ip_child_addresses(monkeypatch):
    monkeypatch.setattr(dns_tools, "_run_resolver_child", lambda *_args: {"addresses": ["not-an-ip"]})
    with pytest.raises(DNSLookupError) as error:
        lookup_hostname("example.com")
    assert error.value.kind == "resolver_error"



def test_reverse_lookup_normalizes_valid_ptr_target(monkeypatch):
    monkeypatch.setattr(
        dns_tools, "_run_resolver_child", lambda *_args: {"hostname": "Mail.Example.COM."}
    )

    result = dns_tools.reverse_lookup_ip("192.0.2.10")

    assert result["hostname"] == "mail.example.com"
    assert result["record_type"] == "PTR"
    assert result["source"] == "system-resolver"


@pytest.mark.parametrize("hostname", ["bad..example", "not a hostname", "192.0.2.10"])
def test_reverse_lookup_rejects_malformed_ptr_target_as_resolver_error(monkeypatch, hostname):
    monkeypatch.setattr(
        dns_tools, "_run_resolver_child", lambda *_args: {"hostname": hostname}
    )

    with pytest.raises(DNSLookupError) as error:
        dns_tools.reverse_lookup_ip("192.0.2.10")

    assert error.value.kind == "resolver_error"
    assert "resolvedor DNS devolvió un error" in str(error.value)
