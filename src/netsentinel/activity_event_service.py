"""Validación y normalización de eventos antes de admitirlos en NetSentinel.

Este módulo valida los metadatos entrantes. No abre bases de datos ni expone rutas HTTP.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

from .activity_catalog import EVENT_SOURCES, EVENT_TYPES, PROTOCOLS
from .activity_privacy import _domain, _email_address_list, _safe_page_url


def _now() -> datetime:
    """Devuelve la hora actual en UTC."""
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    """Serializa la fecha en UTC con la precisión histórica del servicio."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _parse_timestamp(value: str | None) -> str:
    if value is None or value == "":
        return _iso(_now())
    if not isinstance(value, str):
        raise ValueError("La fecha debe ser ISO 8601, por ejemplo 2026-10-11T18:30:00Z.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("La fecha debe ser ISO 8601, por ejemplo 2026-10-11T18:30:00Z.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now = _now()
    if parsed < now - timedelta(days=365):
        raise ValueError("La fecha no puede tener más de 365 días de antigüedad.")
    if parsed > now + timedelta(minutes=5):
        raise ValueError("La fecha del evento no puede estar más de cinco minutos en el futuro.")
    return _iso(parsed)


def normalize_event(payload: dict[str, Any], *, source_override: str | None = None) -> dict[str, Any]:
    """Valida un evento de metadatos; rechaza silenciosamente no es una opción."""
    event_type = str(payload.get("event_type", "")).strip().lower()
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Tipo de evento no admitido. Usá: {', '.join(sorted(EVENT_TYPES))}.")
    source = source_override or str(payload.get("source", "")).strip().lower()
    if source not in EVENT_SOURCES and source != "manual_import":
        raise ValueError("Fuente no admitida.")
    domain = _domain(payload.get("domain"))
    page_url = _safe_page_url(payload.get("page_url"))
    search_engine = payload.get("search_engine")
    search_engine = str(search_engine).strip()[:40] if search_engine not in (None, "") else None
    if search_engine and any(ord(ch) < 32 for ch in search_engine):
        raise ValueError("search_engine no puede contener caracteres de control.")
    search_terms = payload.get("search_terms")
    search_terms = " ".join(str(search_terms).split())[:500] if search_terms not in (None, "") else None
    email_provider = payload.get("email_provider")
    email_provider = " ".join(str(email_provider).split())[:60] if email_provider not in (None, "") else None
    if email_provider and any(ord(ch) < 32 for ch in email_provider):
        raise ValueError("email_provider no puede contener caracteres de control.")
    email_from_list = _email_address_list(payload.get("email_from"), field="email_from", required=event_type == "email_metadata")
    email_to_list = _email_address_list(payload.get("email_to"), field="email_to", required=event_type == "email_metadata")
    email_subject = payload.get("email_subject")
    if email_subject not in (None, ""):
        raw_subject = str(email_subject)
        if any(ord(ch) < 32 and not ch.isspace() for ch in raw_subject):
            raise ValueError("email_subject contiene caracteres de control.")
        email_subject = " ".join(raw_subject.split())[:200]
    else:
        email_subject = None
    if event_type == "email_metadata":
        if source_override != "manual_import":
            raise ValueError("Los metadatos de correo solo se admiten mediante importación explícita de registros autorizados.")
        if len(email_from_list) != 1 or not email_to_list:
            raise ValueError("El evento email_metadata requiere un emisor y al menos un destinatario.")
    if event_type == "page_visit" and not page_url:
        raise ValueError("El evento page_visit requiere page_url.")
    if event_type == "search_query" and (not search_engine or not search_terms):
        raise ValueError("El evento search_query requiere search_engine y search_terms.")
    if page_url and not domain:
        page_host = urlsplit(page_url).hostname
        if page_host:
            try:
                domain = _domain(page_host)
            except ValueError:
                try:
                    ipaddress.ip_address(page_host)
                    domain = None
                except ValueError:
                    raise
    destination_ip = payload.get("destination_ip")
    if destination_ip is not None and str(destination_ip).strip():
        try:
            destination_ip = str(ipaddress.ip_address(str(destination_ip).strip()))
        except ValueError as exc:
            raise ValueError("destination_ip debe ser una dirección IPv4 o IPv6 válida.") from exc
    else:
        destination_ip = None
    port = payload.get("destination_port")
    if port in ("", None):
        port = None
    else:
        try:
            port = int(port)
        except (ValueError, TypeError) as exc:
            raise ValueError("destination_port debe ser un entero entre 1 y 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("destination_port debe ser un entero entre 1 y 65535.")
    protocol = payload.get("protocol")
    protocol = str(protocol).strip().lower() if protocol not in (None, "") else None
    if protocol is not None and protocol not in PROTOCOLS:
        raise ValueError(f"Protocolo no admitido. Usá: {', '.join(sorted(PROTOCOLS))}.")
    app_name = payload.get("app_name")
    app_name = str(app_name).strip()[:100] if app_name not in (None, "") else None
    if app_name and any(ord(ch) < 32 for ch in app_name):
        raise ValueError("app_name no puede contener caracteres de control.")
    if event_type in {"dns_query", "tls_sni"} and not domain:
        raise ValueError(f"El evento {event_type} requiere un nombre DNS.")
    if event_type == "connection" and not (destination_ip or domain):
        raise ValueError("Una conexión requiere destination_ip o domain.")
    if event_type == "app_usage" and not app_name:
        raise ValueError("El evento app_usage requiere app_name.")
    if event_type == "email_metadata" and source != "manual_import":
        raise ValueError("La actividad de correo no se admite desde fuentes de red en tiempo real.")
    blocked_value = payload.get("blocked", False)
    if isinstance(blocked_value, str):
        normalized_blocked = blocked_value.strip().lower()
        if normalized_blocked not in {"", "0", "1", "true", "false", "yes", "no"}:
            raise ValueError("blocked debe ser verdadero o falso.")
        blocked = normalized_blocked in {"1", "true", "yes"}
    else:
        blocked = bool(blocked_value)
    return {
        "observed_at": _parse_timestamp(payload.get("observed_at")),
        "event_type": event_type,
        "source": source,
        "domain": domain,
        "destination_ip": destination_ip,
        "destination_port": port,
        "protocol": protocol,
        "app_name": app_name,
        "page_url": page_url,
        "search_engine": search_engine,
        "search_terms": search_terms,
        "email_provider": email_provider,
        "email_from": "; ".join(email_from_list) if email_from_list else None,
        "email_to": "; ".join(email_to_list) if email_to_list else None,
        "email_subject": email_subject,
        "blocked": int(blocked or event_type == "blocked"),
    }
