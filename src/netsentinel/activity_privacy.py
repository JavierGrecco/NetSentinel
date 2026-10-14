"""Normalización y protección de datos de actividad antes de guardarlos o exportarlos.

Este módulo contiene reglas puras: no abre conexiones, no consulta la red y no
guarda información. Mantiene los límites de privacidad en un solo lugar para que
la API, la importación y las futuras fuentes de actividad apliquen los mismos criterios.
"""
from __future__ import annotations

import ipaddress
import re
from email.utils import getaddresses
from urllib.parse import parse_qsl, unquote, unquote_plus, urlencode, urlsplit, urlunsplit

SENSITIVE_QUERY_KEY = re.compile(
    r"(?:access.?token|refresh.?token|id.?token|client.?secret|client.?assertion|"
    r"password|passwd|secret|authorization|bearer|api.?key|private.?key|"
    r"username|email|phone|session|sid|csrf|nonce|signature|"
    r"redirect.?uri|return.?url|return.?to|returnto|relay.?state|saml.?request|callback|"
    r"(^|_)(?:token|auth|code|state|otp|jwt|key|user|account|customer|continue|next)(_|$))",
    re.IGNORECASE,
)
SEARCH_QUERY_KEYS = {"q", "query", "text", "wd", "word", "search_query", "search"}
TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ttclid",
    "twclid", "li_fat_id", "mkt_tok", "vero_id", "s_cid", "_ga", "_gl", "_hsenc", "_hsmi",
}
_PATH_EMAIL = re.compile(r"^[^/\s@]+@[^/\s@]+\.[^/\s@]+$")
_PATH_PHONE = re.compile(r"^[+()0-9.\-\s]+$")
_PATH_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_PATH_OPAQUE = re.compile(r"^[A-Za-z0-9._~-]+$")

def _domain(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    raw = value.strip().rstrip(".")
    if len(raw) > 253 or any(ch in raw for ch in "/\\@?#") or "://" in raw:
        raise ValueError("El campo domain acepta solo un nombre DNS, no una URL ni una ruta.")
    try:
        # IP literals are represented in destination_ip, not as DNS names.
        ipaddress.ip_address(raw)
    except ValueError:
        pass
    else:
        raise ValueError("Usá destination_ip para direcciones IP; domain debe ser un nombre DNS.")
    try:
        normalized = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("El nombre DNS no es válido.") from exc
    labels = normalized.split(".")
    if any(
        not label or len(label) > 63
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    ):
        raise ValueError("El nombre DNS contiene etiquetas no válidas.")
    return normalized


def _normalized_query_key(value: str) -> str | None:
    """Normalize encoded parameter names, rejecting keys that remain ambiguous."""
    normalized = value.lower()
    for _ in range(8):
        if not re.search(r"%[0-9a-f]{2}", normalized, re.IGNORECASE):
            break
        try:
            decoded = unquote_plus(normalized, errors="strict")
        except UnicodeDecodeError:
            return None
        if decoded == normalized:
            break
        normalized = decoded
    # Do not allow a deeply encoded sensitive name to evade redaction.
    if re.search(r"%[0-9a-f]{2}", normalized, re.IGNORECASE):
        return None
    return re.sub(r"[^a-z0-9_]", "", normalized)


def _sensitive_path_segment(value: str) -> bool:
    """Redact common PII and fail closed on paths hidden by nested encoding."""
    decoded = value
    for _ in range(8):
        try:
            expanded = unquote(decoded, errors="strict")
        except UnicodeDecodeError:
            return bool(re.search(r"%[0-9a-f]{2}", decoded, re.IGNORECASE))
        if expanded == decoded:
            break
        decoded = expanded
    # A segment still carrying valid escapes cannot be inspected reliably.
    if re.search(r"%[0-9a-f]{2}", decoded, re.IGNORECASE):
        return True
    if _PATH_EMAIL.fullmatch(decoded) or _PATH_UUID.fullmatch(decoded):
        return True
    if _PATH_PHONE.fullmatch(decoded) and sum(ch.isdigit() for ch in decoded) >= 10:
        return True
    if (
        len(decoded) >= 32
        and _PATH_OPAQUE.fullmatch(decoded)
        and any(ch.isalpha() for ch in decoded)
        and any(ch.isdigit() for ch in decoded)
    ):
        return True
    return False


def _safe_url_path(path: str) -> str:
    """Replace recognizable email/phone/UUID/opaque-token segments with a marker."""
    if not path:
        return "/"
    segments = path.split("/")
    return "/".join("%5Bredacted%5D" if _sensitive_path_segment(segment) else segment for segment in segments)


_NON_PUBLIC_IPV4_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/3",
    )
)
_IPV4_SPECIAL_192_0_0_0_24 = ipaddress.ip_network("192.0.0.0/24")
_IPV4_GLOBAL_EXCEPTIONS = {
    ipaddress.ip_address("192.0.0.9"),
    ipaddress.ip_address("192.0.0.10"),
}
_NON_PUBLIC_IPV6_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "::/96",           # Deprecated IPv4-compatible prefix; mapped IPv4 handled separately.
        "fc00::/7",        # Unique-local.
        "fe80::/10",       # Link-local.
        "ff00::/8",        # Multicast.
        "2001:db8::/32",   # Documentation.
        "3fff::/20",       # Documentation.
        "2001:2::/48",     # Benchmarking.
        "100::/64",        # Discard-only.
        "2001::/32",       # Teredo transition.
        "2002::/16",       # 6to4 transition.
        "64:ff9b:1::/48",  # Local-use NAT64.
        "100:0:0:1::/64",  # Dummy prefix.
        "2001:10::/28",    # Deprecated ORCHID.
        "5f00::/16",       # Segment-routing special use.
    )
)
_NON_PUBLIC_HOST_SUFFIXES = frozenset(
    {"localhost", "local", "lan", "localdomain", "test", "example", "invalid", "arpa"}
)


def _has_noncanonical_ipv4_host_syntax(hostname: str) -> bool:
    """Detect WHATWG-style numeric host spellings that Python's ipaddress rejects."""
    host = str(hostname or "").strip().rstrip(".").lower()
    final_label = host.rsplit(".", 1)[-1]
    # Browsers canonicalize forms such as 127.1, 2130706433, 0177.0.0.1
    # and 0x7f000001 to IPv4 literals before navigation events are delivered.
    return bool(
        re.fullmatch(r"[0-9]+", final_label)
        or re.fullmatch(r"0x[0-9a-f]*", final_label)
    )


def _is_non_public_navigation_host(hostname: str) -> bool:
    """Return whether a navigation host is local or a documented special-use address."""
    host = str(hostname or "").strip().rstrip(".").lower()
    if not host or any(
        host == suffix or host.endswith("." + suffix)
        for suffix in _NON_PUBLIC_HOST_SUFFIXES
    ):
        return True

    try:
        # Zone identifiers do not change the scope classification of an IPv6 address.
        address = ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        # Regular public DNS names remain eligible; we never resolve them here.
        return False

    if isinstance(address, ipaddress.IPv4Address):
        if any(address in network for network in _NON_PUBLIC_IPV4_NETWORKS):
            return True
        return (
            address in _IPV4_SPECIAL_192_0_0_0_24
            and address not in _IPV4_GLOBAL_EXCEPTIONS
        )

    # IPv4-mapped IPv6 literals must inherit the classification of the mapped IPv4.
    mapped_ipv4 = address.ipv4_mapped
    if mapped_ipv4 is not None:
        return _is_non_public_navigation_host(str(mapped_ipv4))
    return any(address in network for network in _NON_PUBLIC_IPV6_NETWORKS)


def _safe_page_url(value: str | None) -> str | None:
    """Normalize HTTP(S) URLs and redact known sensitive query keys and recognizable path identifiers."""
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    if len(raw) > 4096 or any(ord(ch) < 32 for ch in raw):
        raise ValueError("page_url supera el límite o contiene caracteres de control.")
    try:
        parsed = urlsplit(raw)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("page_url no es una URL válida.") from exc
    if scheme not in {"http", "https"} or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("page_url debe ser una URL HTTP(S) sin credenciales embebidas.")
    try:
        # A final dot is insignificant for an IP literal, just as it is in browser URL parsing.
        normalized_host = str(ipaddress.ip_address(hostname.rstrip("."))).lower()
    except ValueError:
        try:
            normalized_host = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("El host de page_url no es válido.") from exc
        if _has_noncanonical_ipv4_host_syntax(normalized_host):
            raise ValueError(
                "page_url contiene un host IPv4 ambiguo o no canónico; "
                "no se admiten destinos locales, privados o de uso especial con formatos alternativos."
            )
    if len(normalized_host) > 253:
        raise ValueError("El host de page_url es demasiado largo.")
    if _is_non_public_navigation_host(normalized_host):
        raise ValueError(
            "page_url no puede apuntar a destinos locales, privados o de uso especial."
        )
    netloc = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    if port is not None and port != (443 if scheme == "https" else 80):
        netloc += f":{port}"
    try:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True, max_num_fields=200)
    except ValueError as exc:
        raise ValueError("page_url contiene demasiados parámetros de consulta.") from exc
    safe_pairs = []
    for key, item_value in query_pairs:
        normalized_key = _normalized_query_key(key)
        if (
            normalized_key is None
            or SENSITIVE_QUERY_KEY.search(normalized_key)
            or normalized_key in TRACKING_QUERY_KEYS
            or normalized_key.startswith("utm_")
            or normalized_key in SEARCH_QUERY_KEYS
        ):
            continue
        safe_pairs.append((key, item_value))
    safe = urlunsplit((scheme, netloc, _safe_url_path(parsed.path), urlencode(safe_pairs, doseq=True), ""))
    if len(safe) > 2048:
        raise ValueError("page_url supera los 2048 caracteres permitidos.")
    return safe


def _email_address_list(value: str | None, *, field: str, required: bool) -> list[str]:
    if value is None or not str(value).strip():
        if required:
            raise ValueError(f"{field} es obligatorio para el evento de correo.")
        return []
    raw = str(value).strip()
    if len(raw) > 1500 or any(ord(ch) < 32 for ch in raw):
        raise ValueError(f"{field} supera el límite o contiene caracteres de control.")
    addresses = getaddresses([raw.replace(";", ",")])
    normalized: list[str] = []
    for _display, address in addresses:
        address = address.strip()
        if not address or "@" not in address:
            continue
        local, domain = address.rsplit("@", 1)
        if not local or len(local) > 64 or not domain or "." not in domain or len(address) > 254:
            continue
        try:
            domain = domain.encode("idna").decode("ascii").lower()
        except UnicodeError:
            continue
        if any(ch.isspace() for ch in local) or any(ch in local for ch in "<>,;"):
            continue
        address = f"{local}@{domain}"
        if address not in normalized:
            normalized.append(address)
    if not normalized and required:
        raise ValueError(f"{field} no contiene una dirección de correo válida.")
    if len(normalized) > 10:
        raise ValueError(f"{field} admite como máximo 10 direcciones por evento.")
    return normalized
