"""Validación y normalización de eventos antes de admitirlos en NetSentinel.

Este módulo valida los metadatos entrantes. No abre bases de datos ni expone rutas HTTP.
"""
from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta, timezone
import re
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


def _optional_ip(value: Any, field: str) -> str | None:
    """Normaliza una IP; vacío indica que la fuente no aportó el dato."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} debe ser una dirección IPv4 o IPv6 válida.")
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as exc:
        raise ValueError(f"{field} debe ser una dirección IPv4 o IPv6 válida.") from exc


def _optional_integer(value: Any, field: str, *, minimum: int, maximum: int) -> int | None:
    """Valida puertos y contadores sin redondear ni convertir booleanos en números."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError(f"{field} debe ser un entero entre {minimum} y {maximum}.")
    raw = str(value).strip()
    if not re.fullmatch(r"[0-9]+", raw) or len(raw) > len(str(maximum)):
        raise ValueError(f"{field} debe ser un entero entre {minimum} y {maximum}.")
    normalized = int(raw)
    if not minimum <= normalized <= maximum:
        raise ValueError(f"{field} debe ser un entero entre {minimum} y {maximum}.")
    return normalized


def _optional_metadata(value: Any, field: str, *, maximum: int) -> str | None:
    """Normaliza etiquetas de procedencia y rechaza caracteres de control."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} debe ser texto.")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{field} supera su límite o contiene caracteres de control.")
    normalized = " ".join(value.split())
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{field} supera su límite o contiene caracteres de control.")
    return normalized


def normalize_event(payload: dict[str, Any], *, source_override: str | None = None) -> dict[str, Any]:
    """Valida un evento de metadatos y conserva solo los campos que la fuente aporta."""
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
    source_ip = _optional_ip(payload.get("source_ip"), "source_ip")
    source_port = _optional_integer(payload.get("source_port"), "source_port", minimum=1, maximum=65535)
    destination_ip = _optional_ip(payload.get("destination_ip"), "destination_ip")
    destination_port = _optional_integer(payload.get("destination_port"), "destination_port", minimum=1, maximum=65535)
    max_counter = 9_223_372_036_854_775_807
    counters = {
        field: _optional_integer(payload.get(field), field, minimum=0, maximum=max_counter)
        for field in ("bytes_sent", "bytes_received", "packets_sent", "packets_received")
    }
    network_interface = _optional_metadata(payload.get("network_interface"), "network_interface", maximum=64)
    source_event_id = _optional_metadata(payload.get("source_event_id"), "source_event_id", maximum=160)
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
    blocked_value_present = "blocked" in payload
    blocked_value = payload.get("blocked")
    supplied_observation = payload.get("blocked_observation")
    allowed_observations = {
        "reported_true", "reported_false", "missing", "empty",
        "event_type_blocked", "legacy_unknown",
    }

    def parse_blocked_value(value: Any) -> tuple[bool, str]:
        if value is None:
            return False, "empty"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if not normalized:
                return False, "empty"
            if normalized not in {"0", "1", "true", "false", "yes", "no"}:
                raise ValueError("blocked debe ser verdadero o falso.")
            result = normalized in {"1", "true", "yes"}
            return result, "reported_true" if result else "reported_false"
        if isinstance(value, bool):
            return value, "reported_true" if value else "reported_false"
        if isinstance(value, int) and value in (0, 1):
            result = bool(value)
            return result, "reported_true" if result else "reported_false"
        # Evita convertir valores truthy arbitrarios en un indicador de bloqueo.
        raise ValueError("blocked debe ser verdadero o falso.")

    if "blocked_observation" in payload:
        if not isinstance(supplied_observation, str):
            raise ValueError("blocked_observation debe ser un estado de procedencia admitido.")
        blocked_observation = supplied_observation.strip().lower()
        if blocked_observation not in allowed_observations:
            raise ValueError("blocked_observation debe ser un estado de procedencia admitido.")

        if blocked_value_present:
            blocked, parsed_observation = parse_blocked_value(blocked_value)
            # A normalized export carries the compatibility boolean alongside the
            # original observation state. False is a valid projection for missing
            # and empty values, but an empty raw value cannot substantiate an
            # explicit reported_false claim.
            if blocked_observation == "reported_false" and parsed_observation != "reported_false":
                raise ValueError("blocked_observation no coincide con el valor informado en blocked.")
        else:
            # The status is sufficient to reconstruct the legacy boolean in CSV.
            blocked = blocked_observation in {"reported_true", "event_type_blocked"}

        if blocked_observation == "event_type_blocked" and event_type != "blocked":
            raise ValueError("event_type_blocked requiere event_type=blocked.")

        if event_type == "blocked":
            if blocked_observation == "reported_false":
                raise ValueError("event_type=blocked no puede declarar blocked=false.")
            if blocked_observation in {"missing", "empty"}:
                # The event type itself is positive evidence when the boolean
                # column was omitted or empty.
                blocked_observation = "event_type_blocked"
                blocked = True
            elif blocked_observation == "event_type_blocked":
                if blocked_value_present and parsed_observation == "reported_false":
                    raise ValueError("event_type=blocked no puede declarar blocked=false.")
                blocked = True

        if blocked_observation in {"reported_true", "event_type_blocked"} and not blocked:
            raise ValueError("blocked contradice blocked_observation.")
        if blocked_observation in {"reported_false", "missing", "empty"} and blocked:
            raise ValueError("blocked contradice blocked_observation.")
    elif blocked_value_present:
        blocked, blocked_observation = parse_blocked_value(blocked_value)
    else:
        blocked, blocked_observation = False, "missing"

    if event_type == "blocked" and "blocked_observation" not in payload:
        if blocked_observation == "reported_false":
            raise ValueError("event_type=blocked no puede declarar blocked=false.")
        if blocked_observation in {"missing", "empty"}:
            blocked_observation = "event_type_blocked"
        blocked = True
    return {
        "observed_at": _parse_timestamp(payload.get("observed_at")),
        "event_type": event_type,
        "source": source,
        "domain": domain,
        "source_ip": source_ip,
        "source_port": source_port,
        "destination_ip": destination_ip,
        "destination_port": destination_port,
        "protocol": protocol,
        **counters,
        "network_interface": network_interface,
        "source_event_id": source_event_id,
        "app_name": app_name,
        "page_url": page_url,
        "search_engine": search_engine,
        "search_terms": search_terms,
        "email_provider": email_provider,
        "email_from": "; ".join(email_from_list) if email_from_list else None,
        "email_to": "; ".join(email_to_list) if email_to_list else None,
        "email_subject": email_subject,
        "blocked": int(blocked),
        "blocked_observation": blocked_observation,
    }
