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
            "https://[2001:0db8:0:0:0:0:0:1]:443/docs?lang=es#top",
            "https://[2001:db8::1]/docs?lang=es",
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
