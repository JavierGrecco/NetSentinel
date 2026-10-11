import netsentinel.dns_tools as dns_tools


def test_cached_ptr_lookup_reuses_successful_result(monkeypatch):
    dns_tools.clear_ptr_cache()
    calls = []
    monkeypatch.setattr(
        dns_tools,
        "reverse_lookup_ip",
        lambda address: calls.append(address) or {
            "ip": address,
            "hostname": "router.example.test",
            "source": "system-resolver",
            "record_type": "PTR",
            "note": "PTR no verifica identidad.",
        },
    )
    first = dns_tools.cached_reverse_lookup_ip("192.0.2.1")
    second = dns_tools.cached_reverse_lookup_ip("192.0.2.1")
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert first["resolved_at"] == second["resolved_at"]
    assert calls == ["192.0.2.1"]
    dns_tools.clear_ptr_cache()


def test_cached_ptr_lookup_does_not_cache_failures(monkeypatch):
    dns_tools.clear_ptr_cache()
    calls = []

    def fail(address):
        calls.append(address)
        raise dns_tools.DNSLookupError("Temporal", "temporary")

    monkeypatch.setattr(dns_tools, "reverse_lookup_ip", fail)
    for _ in range(2):
        try:
            dns_tools.cached_reverse_lookup_ip("192.0.2.2")
        except dns_tools.DNSLookupError:
            pass
        else:
            raise AssertionError("La consulta debía propagar el error DNS")
    assert calls == ["192.0.2.2", "192.0.2.2"]
    dns_tools.clear_ptr_cache()


def test_cached_ptr_lookup_evicts_oldest_entry(monkeypatch):
    dns_tools.clear_ptr_cache()
    monkeypatch.setattr(dns_tools, "_PTR_CACHE_MAX_ENTRIES", 2)
    monkeypatch.setattr(
        dns_tools,
        "reverse_lookup_ip",
        lambda address: {"ip": address, "hostname": "host.example.test", "source": "system-resolver"},
    )
    for address in ("192.0.2.1", "192.0.2.2", "192.0.2.3"):
        dns_tools.cached_reverse_lookup_ip(address)
    assert len(dns_tools._ptr_cache) == 2
    assert "192.0.2.1" not in dns_tools._ptr_cache
    dns_tools.clear_ptr_cache()
