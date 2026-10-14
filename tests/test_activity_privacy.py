"""Pruebas unitarias para el saneamiento de datos de actividad."""
from __future__ import annotations

import pytest

from netsentinel.activity_privacy import (
    _domain,
    _email_address_list,
    _safe_page_url,
)


def test_domain_is_normalized_without_accepting_a_url() -> None:
    """Un dominio queda en formato canónico y no puede incluir una ruta."""
    assert _domain("  ExAmPlE.com.  ") == "example.com"
    with pytest.raises(ValueError, match="solo un nombre DNS"):
        _domain("https://example.com/path")
    with pytest.raises(ValueError, match="nombre DNS"):
        _domain("example.com..")


def test_domain_rejects_name_that_exceeds_dns_limit_after_idna() -> None:
    hostname = ".".join(["é" * 48] * 5)
    encoded = ".".join(label.encode("idna").decode("ascii") for label in hostname.split("."))
    assert len(hostname) <= 253
    assert all(len(label) <= 63 for label in encoded.split("."))
    assert len(encoded) > 253

    with pytest.raises(ValueError, match="nombre DNS"):
        _domain(hostname)


def test_page_url_redacts_sensitive_query_values_and_fragment() -> None:
    """No se conserva el token ni el fragmento del navegador."""
    assert _safe_page_url(
        "https://example.com/course?ref=unit-1&access_token=secret#section"
    ) == "https://example.com/course?ref=unit-1"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/private",
        "http://192.168.1.10/status",
        "http://router.local/status",
        "http://2130706433/",
        "https://" + ".".join(["é" * 48] * 5) + "/profile",
    ],
)
def test_page_url_rejects_local_or_ambiguous_hosts(url: str) -> None:
    """Las formas locales y los hosts IPv4 ambiguos no se registran."""
    with pytest.raises(ValueError):
        _safe_page_url(url)


def test_email_addresses_reject_invalid_idna_domains() -> None:
    hostname = ".".join(["é" * 48] * 5)
    with pytest.raises(ValueError, match="no contiene una dirección"):
        _email_address_list(
            f"operator@{hostname}", field="email_to", required=True
        )


def test_email_addresses_are_normalized_and_limited_to_metadata() -> None:
    """Se guardan direcciones, nunca cuerpos ni contenido del mensaje."""
    assert _email_address_list(
        "Ana <ana@example.com>; Bob <bob@example.org>",
        field="email_to",
        required=True,
    ) == ["ana@example.com", "bob@example.org"]
