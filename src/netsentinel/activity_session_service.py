"""Coordinación de sesiones autorizadas e ingestión de metadatos.

Las ventanas temporales limitan cuándo se acepta telemetría. El token se muestra una
sola vez; solo su hash se conserva. Este servicio no depende de la API HTTP.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from . import activity_event_service, activity_repository, database
from .activity_catalog import SESSION_SOURCES


class InvalidCollectorToken(PermissionError):
    """El secreto de una sesión de recopilación no coincide."""


def _now() -> datetime:
    """Devuelve la hora actual con zona horaria UTC."""
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    """Serializa una fecha en UTC con la precisión usada en la base de datos."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _cleanup(db) -> int:
    """Aplica retención y vence sesiones sin cambiar el esquema."""
    return activity_repository.cleanup(db, now=_now())


def start_session(
    device_id: int, duration_minutes: int, source_mode: str
) -> dict[str, Any]:
    """Abre una ventana temporal y devuelve un token que se muestra una sola vez."""
    if not 5 <= int(duration_minutes) <= 720:
        raise ValueError("La duración debe estar entre 5 minutos y 12 horas.")
    if not isinstance(source_mode, str):
        raise ValueError("Fuente elegible: router_dns, router_flow o device_agent.")
    source_mode = source_mode.strip().lower()
    if source_mode not in SESSION_SOURCES:
        raise ValueError("Fuente elegible: router_dns, router_flow o device_agent.")

    now = _now()
    started_at = _iso(now)
    ends_at = _iso(now + timedelta(minutes=int(duration_minutes)))
    collector_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(collector_token.encode("utf-8")).hexdigest()
    with database.connect() as db:
        _cleanup(db)
        result = activity_repository.start_session(
            db,
            device_id=device_id,
            source_mode=source_mode,
            started_at=started_at,
            ends_at=ends_at,
            token_hash=token_hash,
        )
    result["collector_token"] = collector_token
    result["token_note"] = (
        "Copiá este token ahora. Solo se almacena su hash y no volverá a mostrarse."
    )
    return result


def stop_session(session_id: int) -> dict[str, Any] | None:
    """Cierra una sesión activa o devuelve None si no existe."""
    now = _iso(_now())
    with database.connect() as db:
        _cleanup(db)
        return activity_repository.stop_session(db, session_id, now=now)


def ingest_event(
    session_id: int, device_id: int, collector_token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Valida la sesión y guarda solo eventos dentro de la ventana autorizada."""
    event = activity_event_service.normalize_event(payload)
    now = _iso(_now())
    supplied_hash = hashlib.sha256(collector_token.encode("utf-8")).hexdigest()
    with database.connect() as db:
        _cleanup(db)
        session = activity_repository.get_session_for_device(db, session_id, device_id)
        if session is None:
            raise LookupError("No existe una sesión para ese dispositivo.")
        if not hmac.compare_digest(session["collector_token_hash"], supplied_hash):
            raise InvalidCollectorToken("El token de recopilación no es válido.")
        if session["status"] != "active" or session["ends_at"] <= now:
            raise PermissionError(
                "La sesión no está activa; iniciá otra ventana de seguimiento."
            )
        if event["source"] != session["source_mode"]:
            raise ValueError(
                "La fuente del evento no coincide con la fuente elegida para esta sesión."
            )

        # No aceptar telemetría atrasada que la siguiente lectura tendría que borrar.
        retention_days = activity_repository.get_retention_days(db)
        retention_cutoff = _iso(_now() - timedelta(days=retention_days))
        if event["observed_at"] < retention_cutoff:
            raise ValueError(
                f"La fecha queda fuera de la retención configurada de {retention_days} día(s). "
                "No se guardó el evento."
            )

        return activity_repository.insert_event(
            db, session_id, device_id, event, received_at=now
        )
