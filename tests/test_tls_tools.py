from datetime import datetime, timedelta, timezone
import json
import socket
import ssl
import subprocess
import sys

import pytest

from netsentinel import tls_tools


def _certificate(days_until_expiry=90):
    now = datetime.now(timezone.utc)
    return {
        "subject": ((("commonName", "example.com"),),),
        "issuer": ((("commonName", "Example Test CA"),),),
        "notBefore": (now - timedelta(days=10)).strftime("%b %d %H:%M:%S %Y GMT"),
        "notAfter": (now + timedelta(days=days_until_expiry)).strftime("%b %d %H:%M:%S %Y GMT"),
        "subjectAltName": (("DNS", "example.com"), ("DNS", "www.example.com")),
    }


class _RawSocket:
    def __init__(self):
        self.timeout = None

    def settimeout(self, value):
        self.timeout = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _TLSConnection:
    def __init__(self, certificate=None):
        self.certificate = certificate if certificate is not None else _certificate()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def getpeercert(self):
        return self.certificate

    def version(self):
        return "TLSv1.3"

    def cipher(self):
        return ("TLS_AES_256_GCM_SHA384", "TLSv1.3", 256)


class _TLSContext:
    def __init__(self, connection=None, error=None):
        self.connection = connection or _TLSConnection()
        self.error = error
        self.server_name = None

    def wrap_socket(self, _socket, server_hostname):
        self.server_name = server_hostname
        if self.error:
            raise self.error
        return self.connection


def _mock_success(monkeypatch, certificate=None):
    raw = _RawSocket()
    context = _TLSContext(_TLSConnection(certificate))
    calls = {}

    def connect(address, timeout):
        calls["address"] = address
        calls["timeout"] = timeout
        return raw

    monkeypatch.setattr(tls_tools.socket, "create_connection", connect)
    monkeypatch.setattr(tls_tools.ssl, "create_default_context", lambda: context)
    return calls, context, raw


@pytest.mark.parametrize("host", [
    "", "https://example.com", "example.com/path", "user@example.com",
    "example.com:443", "-bad.example", "bad..example", "example.com?token=x",
])
def test_tls_inspection_rejects_url_paths_credentials_and_invalid_hosts(host):
    with pytest.raises(ValueError):
        tls_tools.inspect_tls_endpoint(host)


def test_tls_inspection_validates_certificate_and_reports_handshake(monkeypatch):
    calls, context, raw = _mock_success(monkeypatch)

    result = tls_tools._inspect_tls_endpoint_direct("Example.COM.", port=8443, timeout=2.5)

    assert result["status"] == "ok"
    assert result["host"] == "example.com"
    assert result["port"] == 8443
    assert result["certificate"]["subject"] == "commonName=example.com"
    assert result["certificate"]["issuer"] == "commonName=Example Test CA"
    assert "www.example.com" in result["certificate"]["dns_names"]
    assert result["certificate"]["days_remaining"] >= 89
    assert result["tls"] == {
        "version": "TLSv1.3",
        "cipher": "TLS_AES_256_GCM_SHA384",
        "cipher_bits": 256,
    }
    assert calls == {"address": ("example.com", 8443), "timeout": 2.5}
    assert raw.timeout == 2.5
    assert context.server_name == "example.com"
    assert "HTTP" in result["notice"]
    assert result["findings"] == []


def test_tls_inspection_warns_about_certificate_expiring_soon(monkeypatch):
    _mock_success(monkeypatch, certificate=_certificate(days_until_expiry=5))

    result = tls_tools._inspect_tls_endpoint_direct("example.com")

    assert result["status"] == "warning"
    assert result["certificate"]["days_remaining"] <= 5
    assert result["findings"][0]["code"] == "certificate_expiring_soon"
    assert result["findings"][0]["severity"] == "high"


@pytest.mark.parametrize(
    ("verify_code", "expected_code"),
    [(10, "certificate_expired"), (9, "certificate_not_yet_valid"), (62, "certificate_name_mismatch"), (20, "certificate_untrusted")],
)
def test_tls_inspection_reports_certificate_verification_failure(monkeypatch, verify_code, expected_code):
    raw = _RawSocket()

    class VerificationError(ssl.SSLCertVerificationError):
        def __init__(self, code):
            super().__init__("verification failed")
            self.verify_code = code
            self.verify_message = "certificate verification failed"

    error = VerificationError(verify_code)
    context = _TLSContext(error=error)
    monkeypatch.setattr(tls_tools.socket, "create_connection", lambda *_args, **_kwargs: raw)
    monkeypatch.setattr(tls_tools.ssl, "create_default_context", lambda: context)

    result = tls_tools.inspect_tls_endpoint("example.com")

    assert result["status"] == "warning"
    assert result["findings"][0]["code"] == expected_code
    assert "certificate verification failed" not in result["summary"]


def test_tls_inspection_reports_timeout_without_raw_exception(monkeypatch):
    monkeypatch.setattr(
        tls_tools.socket, "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("secret technical detail")),
    )

    result = tls_tools.inspect_tls_endpoint("example.com")

    assert result["status"] == "timeout"
    assert result["findings"][0]["code"] == "connection_timeout"
    assert "secret technical detail" not in result["summary"]


@pytest.mark.parametrize("port", [0, -1, 65536, True, "443"])
def test_tls_inspection_rejects_invalid_port(port):
    with pytest.raises(ValueError):
        tls_tools.inspect_tls_endpoint("example.com", port=port)


def test_tls_inspection_supports_ip_addresses(monkeypatch):
    calls, context, _raw = _mock_success(monkeypatch, certificate=_certificate())

    result = tls_tools.inspect_tls_endpoint("192.0.2.10")

    assert result["host"] == "192.0.2.10"
    assert calls["address"] == ("192.0.2.10", 443)
    assert context.server_name == "192.0.2.10"



def test_tls_inspection_wrapper_enforces_child_process_deadline(monkeypatch):
    calls = {}
    report = {
        "host": "example.com",
        "port": 443,
        "status": "ok",
        "summary": "valid",
        "certificate": None,
        "tls": {"version": "TLSv1.3"},
        "findings": [],
    }

    def fake_run(command, **kwargs):
        calls["command"] = command
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(report), stderr="")

    monkeypatch.setattr(tls_tools.subprocess, "run", fake_run)
    result = tls_tools.inspect_tls_endpoint("Example.COM.")

    assert result == report
    assert calls["command"][0] == sys.executable
    assert calls["command"][1] == str(__import__("pathlib").Path(tls_tools.__file__).resolve())
    assert calls["command"][2] == "--inspect-child"
    assert calls["command"][-2:] == ["443", "3.0"]
    assert calls["kwargs"]["timeout"] == 3.0
    assert calls["kwargs"]["capture_output"] is True
    assert calls["kwargs"]["check"] is False


def test_tls_inspection_wrapper_returns_timeout_if_dns_child_hangs(monkeypatch):
    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    monkeypatch.setattr(tls_tools.subprocess, "run", timeout_run)
    result = tls_tools.inspect_tls_endpoint("example.com", timeout=0.5)

    assert result["status"] == "timeout"
    assert result["findings"][0]["code"] == "inspection_timeout"
    assert "resolución DNS" in result["summary"]


@pytest.mark.parametrize(
    ("returncode", "stdout"),
    [(1, '{"host":"example.com","port":443}'), (0, "not-json")],
)
def test_tls_inspection_wrapper_rejects_invalid_child_results(monkeypatch, returncode, stdout):
    monkeypatch.setattr(
        tls_tools.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=""),
    )
    result = tls_tools.inspect_tls_endpoint("example.com")

    assert result["status"] == "error"
    assert result["findings"][0]["code"] == "inspection_failed"
