"""Regression tests for URL privacy normalization in imported browser metadata."""

import pytest

from netsentinel.activity_tracking import _safe_page_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        (
            "HTTPS://Example.COM:443/docs?lang=es&access%255Ftoken=secret&state=oauth-state"
            "&redirect_uri=https%3A%2F%2Fid.example%2Fcallback%3Femail%3Da%2540b.com"
            "&utm_source=mail&fbclid=click-id#section",
            "https://example.com/docs?lang=es",
        ),
        (
            "https://example.com/feed?gclid=ad-click&_gl=analytics&_ga=analytics-id"
            "&ttclid=tiktok-click&sort=recent",
            "https://example.com/feed?sort=recent",
        ),
        (
            "https://example.com/users/jane%40example.com/profile?view=public",
            "https://example.com/users/%5Bredacted%5D/profile?view=public",
        ),
        (
            "https://example.com/contact/%2B549112223344?view=compact",
            "https://example.com/contact/%5Bredacted%5D?view=compact",
        ),
        (
            "https://example.com/sessions/550e8400-e29b-41d4-a716-446655440000",
            "https://example.com/sessions/%5Bredacted%5D",
        ),
        (
            "https://example.com/reset/eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ABCDEFGHIJKLMNOPQRST0123456789.ABCDEFGHIJKLMNOPQRST0123456789",
            "https://example.com/reset/%5Bredacted%5D",
        ),
        (
            "https://[2001:4860:4860:0:0:0:0:8888]:443/docs?lang=es#top",
            "https://[2001:4860:4860::8888]/docs?lang=es",
        ),
        (
            "https://www.google.com/search?q=private+search&lang=es",
            "https://www.google.com/search?lang=es",
        ),
    ],
)
def test_safe_page_url_redacts_sensitive_query_and_path_values(raw_url, expected):
    assert _safe_page_url(raw_url) == expected


@pytest.mark.parametrize(
    "raw_url",
    [
        "javascript:alert(1)",
        "file:///Users/example/private.txt",
        "https://alice:password@example.com/profile",
        "https://example.com/with" + chr(10) + "control",
    ],
)
def test_safe_page_url_rejects_non_http_or_credential_urls(raw_url):
    with pytest.raises(ValueError):
        _safe_page_url(raw_url)


def test_safe_page_url_rejects_excessive_query_fields():
    raw_url = "https://example.com/?" + "&".join(f"k{i}=v" for i in range(201))
    with pytest.raises(ValueError, match="parámetros"):
        _safe_page_url(raw_url)


def test_safe_page_url_keeps_unrecognized_path_segments_and_non_sensitive_query_values():
    # Arbitrary usernames cannot be identified reliably, so the application documents this limit.
    raw_url = "https://example.com/profile/javier?tab=overview&sort=recent"
    assert _safe_page_url(raw_url) == raw_url

@pytest.mark.parametrize(
    "raw_url",
    [
        "http://0.0.0.0/status",
        "http://10.0.0.1/admin",
        "https://127.0.0.1/",
        "http://169.254.10.20/",
        "http://172.20.0.1/",
        "https://192.0.2.10/docs",
        "https://192.88.99.1/",
        "http://192.168.1.1/admin",
        "http://198.18.0.1/benchmark",
        "http://198.51.100.10/docs",
        "http://203.0.113.20/docs",
        "http://224.0.0.1/",
        "http://100.64.0.1/",
        "https://localhost/",
        "https://printer.local/status",
        "https://router.lan/",
        "https://service.localdomain/",
        "https://host.test/",
        "https://host.example/",
        "https://host.invalid/",
        "https://home.arpa/",
        "http://[::]/",
        "http://[::1]/",
        "https://[fc00::1]/",
        "https://[fe81::1]/",
        "https://[ff02::1]/",
        "https://[2001:db8::1]/",
        "https://[3fff::1]/",
        "https://[2001:2::1]/",
        "https://[100::1]/",
        "https://[2001::1]/",
        "https://[2002::1]/",
        "https://[64:ff9b:1::1]/",
        "https://[100:0:0:1::1]/",
        "https://[2001:10::1]/",
        "https://[5f00::1]/",
        "https://[::ffff:c0a8:101]/",
        "https://[::ffff:192.168.1.1]/",
    ],
)
def test_safe_page_url_rejects_local_private_and_special_use_hosts(raw_url):
    with pytest.raises(ValueError, match="destinos locales, privados o de uso especial"):
        _safe_page_url(raw_url)


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("https://8.8.8.8/docs", "https://8.8.8.8/docs"),
        ("https://192.0.0.9/docs", "https://192.0.0.9/docs"),
        ("https://192.0.0.10/docs", "https://192.0.0.10/docs"),
        ("https://100.63.255.255/docs", "https://100.63.255.255/docs"),
        ("https://100.128.0.1/docs", "https://100.128.0.1/docs"),
        ("https://[2001:4860:4860::8888]/docs", "https://[2001:4860:4860::8888]/docs"),
        ("https://example.com/docs", "https://example.com/docs"),
        ("https://test.example.com/docs", "https://test.example.com/docs"),
    ],
)
def test_safe_page_url_preserves_public_hosts_and_explicit_global_exceptions(raw_url, expected):
    assert _safe_page_url(raw_url) == expected
