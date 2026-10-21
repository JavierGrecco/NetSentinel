"""Geolocalización conservadora de IP que ya aparecen en eventos locales.

La ubicación procede de bases MaxMind instaladas por la persona usuaria. No se
transmiten IP, dominios ni eventos a APIs externas. La geolocalización de IP es
aproximada: no identifica una vivienda, una persona ni necesariamente el origen
físico del equipo que utiliza una dirección.
"""
from __future__ import annotations

import ipaddress
import math
import os
from pathlib import Path
from typing import Any

from . import geolocation_repository
from .config import data_dir

try:
    import maxminddb as _maxminddb
except ImportError:  # Dependencia opcional; la aplicación principal no la necesita.
    _maxminddb = None


def city_database_path() -> Path:
    """Ruta de la base GeoLite2-City local, sin descarga automática."""
    configured = os.environ.get("NETSENTINEL_GEOIP_CITY_DB")
    if configured:
        return Path(configured).expanduser()
    return data_dir() / "GeoLite2-City.mmdb"


def asn_database_path() -> Path:
    """Ruta opcional de GeoLite2-ASN local."""
    configured = os.environ.get("NETSENTINEL_GEOIP_ASN_DB")
    if configured:
        return Path(configured).expanduser()
    return data_dir() / "GeoLite2-ASN.mmdb"


def _open_reader(path: Path) -> tuple[Any | None, str]:
    """Abre una base conocida y devuelve un estado sin filtrar rutas ni errores internos."""
    if _maxminddb is None:
        return None, "library_missing"
    if not path.is_file():
        return None, "database_missing"
    try:
        return _maxminddb.open_database(str(path)), "available"
    except Exception:
        return None, "database_invalid"


def _text_name(value: Any) -> str:
    """Obtiene un nombre legible sin asumir que el registro contiene traducción inglesa."""
    if isinstance(value, dict):
        value = value.get("en") or next(iter(value.values()), "")
    return value.strip()[:160] if isinstance(value, str) else ""


def _coordinates(record: dict[str, Any]) -> tuple[float, float] | None:
    location = record.get("location")
    if not isinstance(location, dict):
        return None
    try:
        latitude = float(location.get("latitude"))
        longitude = float(location.get("longitude"))
    except (TypeError, ValueError):
        return None
    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    return latitude, longitude


def get_world_map_data(*, limit: int = 250) -> dict[str, Any]:
    """Prepara el mapa con IP públicas observadas; nunca inventa coordenadas ni flujos."""
    bounded_limit = max(1, min(int(limit), 500))
    snapshot = geolocation_repository.get_destination_ip_observations(
        limit=bounded_limit
    )
    city_reader, city_status = _open_reader(city_database_path())
    asn_reader, asn_status = _open_reader(asn_database_path())

    grouped: dict[str, dict[str, Any]] = {}
    invalid_ip_events = 0
    non_public_events = 0
    raw_public_events = 0

    for row in snapshot.get("destination_ips", []):
        raw_ip = row.get("ip")
        try:
            address = ipaddress.ip_address(str(raw_ip))
        except ValueError:
            invalid_ip_events += int(row.get("event_count") or 0)
            continue
        event_count = max(0, int(row.get("event_count") or 0))
        if not address.is_global:
            non_public_events += event_count
            continue

        ip_text = address.compressed
        raw_public_events += event_count
        item = grouped.get(ip_text)
        if item is None:
            item = {
                "ip": ip_text,
                "event_count": 0,
                "last_seen": "",
                "sample_domain": "",
                "country": "",
                "country_iso": "",
                "city": "",
                "latitude": None,
                "longitude": None,
                "asn": None,
                "asn_organization": "",
                "location_status": "database_unavailable",
            }
            grouped[ip_text] = item
        item["event_count"] += event_count
        last_seen = str(row.get("last_seen") or "")
        if last_seen > item["last_seen"]:
            item["last_seen"] = last_seen
        sample_domain = str(row.get("sample_domain") or "").strip().lower()
        if sample_domain and not item["sample_domain"]:
            item["sample_domain"] = sample_domain[:253]

    destinations = [grouped[key] for key in sorted(grouped)]
    for item in destinations:
        address = item["ip"]
        city_record = None
        if city_reader is not None:
            try:
                candidate = city_reader.get(address)
                if isinstance(candidate, dict):
                    city_record = candidate
            except Exception:
                city_record = None

        if city_record is None:
            item["location_status"] = (
                "not_found" if city_status == "available" else "database_unavailable"
            )
        else:
            coords = _coordinates(city_record)
            if coords is None:
                item["location_status"] = "no_coordinates"
            else:
                item["latitude"], item["longitude"] = coords
                country = city_record.get("country")
                if not isinstance(country, dict):
                    country = {}
                city = city_record.get("city")
                if not isinstance(city, dict):
                    city = {}
                item["country"] = _text_name(country.get("names"))
                item["country_iso"] = (
                    country.get("iso_code", "")
                    if isinstance(country.get("iso_code", ""), str)
                    else ""
                )[:2].upper()
                item["city"] = _text_name(city.get("names"))
                item["location_status"] = "located"

        if asn_reader is not None:
            try:
                asn_record = asn_reader.get(address)
                if isinstance(asn_record, dict):
                    asn = asn_record.get("autonomous_system_number")
                    item["asn"] = int(asn) if isinstance(asn, int) and asn > 0 else None
                    item["asn_organization"] = _text_name(
                        asn_record.get("autonomous_system_organization")
                    )
            except (TypeError, ValueError, OSError):
                # La geolocalización continúa aunque la base ASN tenga un registro defectuoso.
                pass
            except Exception:
                pass

    if city_reader is not None:
        try:
            city_reader.close()
        except Exception:
            pass
    if asn_reader is not None:
        try:
            asn_reader.close()
        except Exception:
            pass

    mapped_count = sum(item["location_status"] == "located" for item in destinations)
    return {
        "source": "activity_events.destination_ip",
        "summary": {
            "total_events": int(snapshot.get("total_events", 0)),
            "events_with_destination_ip": int(snapshot.get("events_with_destination_ip", 0)),
            "events_without_destination_ip": int(snapshot.get("events_without_destination_ip", 0)),
            "unique_destination_ips": int(snapshot.get("unique_destination_ips", 0)),
            "public_destination_ips_in_sample": len(destinations),
            "mapped_destination_ips": mapped_count,
            "unmapped_public_destination_ips": len(destinations) - mapped_count,
            "non_public_ip_events_skipped": non_public_events,
            "invalid_ip_events_skipped": invalid_ip_events,
            "public_destination_ip_events_in_sample": raw_public_events,
            "limit": bounded_limit,
            "limited": bool(snapshot.get("limited", False)),
        },
        "databases": {
            "geoip_library_available": _maxminddb is not None,
            "city_status": city_status,
            "asn_status": asn_status,
            "city_configured": city_status == "available",
            "asn_configured": asn_status == "available",
        },
        "destinations": destinations,
        "notes": [
            "La ubicación es aproximada y describe el registro GeoIP de una IP pública, no una ubicación física exacta.",
            "Solo se muestran direcciones que ya estaban guardadas como IP de destino en eventos locales.",
            "Los dominios sin destination_ip no se resuelven retroactivamente: una consulta DNS actual no prueba qué IP se usó al registrar el evento.",
            "No se envían IP ni dominios a servicios externos.",
        ],
    }
