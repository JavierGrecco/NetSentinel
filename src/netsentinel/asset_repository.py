"""Persistencia de fichas lógicas y sus asociaciones manuales con registros observados.

Una ficha lógica no verifica la identidad física de un equipo. Una persona agrupa
explícitamente uno o varios registros del inventario y deja el motivo. Las asociaciones
se conservan como historial; no se fusionan dispositivos ni se reescriben observaciones.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .database_storage import connect, utc_now


def _clean_reason(reason: str | None) -> str:
    value = (reason or "").strip()
    if not 8 <= len(value) <= 280:
        raise ValueError("Indicá un motivo de asociación de entre 8 y 280 caracteres.")
    return value


def _asset_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "display_name": str(row["display_name"]),
        "notes": str(row["notes"] or ""),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _get_device_asset(db: Any, device_id: int) -> dict[str, Any] | None:
    row = db.execute(
        """SELECT a.id, a.display_name, a.notes, a.created_at, a.updated_at,
                  l.id AS link_id, l.linked_at, l.link_reason
           FROM asset_device_links l
           JOIN assets a ON a.id = l.asset_id
           WHERE l.device_id = ? AND l.unlinked_at IS NULL""",
        (device_id,),
    ).fetchone()
    if row is None:
        return None
    result = _asset_dict(row)
    result.update({
        "link_id": int(row["link_id"]),
        "linked_at": str(row["linked_at"]),
        "link_reason": str(row["link_reason"]),
        "association": "manual",
    })
    return result


def create_asset(
    display_name: str,
    notes: str = "",
    *,
    device_id: int | None = None,
    reason: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Crea una ficha lógica; opcionalmente enlaza un registro en la misma transacción."""
    name = display_name.strip()
    clean_notes = notes.strip()
    if not 1 <= len(name) <= 120:
        raise ValueError("El nombre de la ficha debe tener entre 1 y 120 caracteres.")
    if len(clean_notes) > 2000:
        raise ValueError("Las notas no pueden superar los 2000 caracteres.")
    clean_reason = _clean_reason(reason) if device_id is not None else None
    asset_id = str(uuid4())
    now = utc_now()
    with connect(path) as db:
        db.execute(
            """INSERT INTO assets (id, display_name, notes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (asset_id, name, clean_notes, now, now),
        )
        if device_id is not None:
            _set_device_asset(db, device_id, asset_id, clean_reason or "", now)
        row = db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return _asset_dict(row)


def update_asset(
    asset_id: str,
    *,
    display_name: str | None = None,
    notes: str | None = None,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Actualiza el rótulo y las notas, sin alterar el historial de asociaciones."""
    clean_name = None if display_name is None else display_name.strip()
    clean_notes = None if notes is None else notes.strip()
    if clean_name is not None and not 1 <= len(clean_name) <= 120:
        raise ValueError("El nombre de la ficha debe tener entre 1 y 120 caracteres.")
    if clean_notes is not None and len(clean_notes) > 2000:
        raise ValueError("Las notas no pueden superar los 2000 caracteres.")
    with connect(path) as db:
        row = db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if row is None:
            return None
        db.execute(
            """UPDATE assets SET display_name = ?, notes = ?, updated_at = ?
               WHERE id = ?""",
            (
                clean_name if clean_name is not None else row["display_name"],
                clean_notes if clean_notes is not None else row["notes"],
                utc_now(),
                asset_id,
            ),
        )
        updated = db.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return _asset_dict(updated)


def list_assets(path: Path | None = None) -> list[dict[str, Any]]:
    """Lista fichas lógicas y los registros que tienen asociados actualmente."""
    with connect(path) as db:
        assets = db.execute(
            """SELECT a.*, COUNT(l.id) AS device_count
               FROM assets a
               LEFT JOIN asset_device_links l
                 ON l.asset_id = a.id AND l.unlinked_at IS NULL
               GROUP BY a.id
               ORDER BY a.display_name COLLATE NOCASE, a.id"""
        ).fetchall()
        members = db.execute(
            """SELECT l.asset_id, l.device_id, l.linked_at, l.link_reason,
                      d.display_name AS device_name, d.mac_address, d.ip_address,
                      d.interface, d.mac_locally_administered, d.first_seen, d.last_seen
               FROM asset_device_links l
               JOIN devices d ON d.id = l.device_id
               WHERE l.unlinked_at IS NULL
               ORDER BY l.asset_id, d.display_name COLLATE NOCASE, d.id"""
        ).fetchall()
    result = {str(row["id"]): _asset_dict(row) | {
        "device_count": int(row["device_count"]),
        "devices": [],
    } for row in assets}
    for row in members:
        result[str(row["asset_id"])]["devices"].append({
            "device_id": int(row["device_id"]),
            "display_name": str(row["device_name"] or ""),
            "mac_address": str(row["mac_address"]),
            "ip_address": str(row["ip_address"]),
            "interface": row["interface"],
            "mac_locally_administered": bool(row["mac_locally_administered"]),
            "first_seen": str(row["first_seen"]),
            "last_seen": str(row["last_seen"]),
            "linked_at": str(row["linked_at"]),
            "link_reason": str(row["link_reason"]),
        })
    return list(result.values())


def get_device_asset(device_id: int, path: Path | None = None) -> dict[str, Any] | None:
    """Devuelve la ficha lógica vigente, o None si el registro no está agrupado."""
    with connect(path) as db:
        exists = db.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone()
        if exists is None:
            raise LookupError("No se encontró el registro del inventario.")
        return _get_device_asset(db, device_id)


def list_device_asset_history(device_id: int, path: Path | None = None) -> list[dict[str, Any]]:
    """Devuelve las asociaciones vigentes y finalizadas sin atribuir una identidad externa."""
    with connect(path) as db:
        exists = db.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone()
        if exists is None:
            raise LookupError("No se encontró el registro del inventario.")
        rows = db.execute(
            """SELECT l.id, l.asset_id, a.display_name, l.linked_at, l.unlinked_at,
                      l.link_reason, l.unlinked_reason
               FROM asset_device_links l
               JOIN assets a ON a.id = l.asset_id
               WHERE l.device_id = ?
               ORDER BY l.linked_at DESC, l.id DESC""",
            (device_id,),
        ).fetchall()
    return [{
        "link_id": int(row["id"]),
        "asset_id": str(row["asset_id"]),
        "asset_name": str(row["display_name"]),
        "linked_at": str(row["linked_at"]),
        "unlinked_at": row["unlinked_at"],
        "link_reason": str(row["link_reason"]),
        "unlinked_reason": row["unlinked_reason"],
        "association": "manual",
    } for row in rows]


def _set_device_asset(
    db: Any,
    device_id: int,
    asset_id: str | None,
    reason: str,
    now: str,
) -> dict[str, Any] | None:
    device = db.execute("SELECT 1 FROM devices WHERE id = ?", (device_id,)).fetchone()
    if device is None:
        raise LookupError("No se encontró el registro del inventario.")
    if asset_id is not None:
        target = db.execute("SELECT 1 FROM assets WHERE id = ?", (asset_id,)).fetchone()
        if target is None:
            raise LookupError("No se encontró la ficha lógica solicitada.")
    current = db.execute(
        """SELECT id, asset_id FROM asset_device_links
           WHERE device_id = ? AND unlinked_at IS NULL""",
        (device_id,),
    ).fetchone()
    if current is not None and asset_id is not None and str(current["asset_id"]) == asset_id:
        return _get_device_asset(db, device_id)
    if current is not None:
        db.execute(
            """UPDATE asset_device_links
               SET unlinked_at = ?, unlinked_reason = ?
               WHERE id = ? AND unlinked_at IS NULL""",
            (now, reason, int(current["id"])),
        )
    if asset_id is not None:
        db.execute(
            """INSERT INTO asset_device_links
               (asset_id, device_id, linked_at, link_reason)
               VALUES (?, ?, ?, ?)""",
            (asset_id, device_id, now, reason),
        )
        db.execute("UPDATE assets SET updated_at = ? WHERE id = ?", (now, asset_id))
    return _get_device_asset(db, device_id)


def set_device_asset(
    device_id: int,
    asset_id: str | None,
    reason: str,
    path: Path | None = None,
) -> dict[str, Any] | None:
    """Asocia o desasocia un registro, guardando cada transición como historial."""
    clean_reason = _clean_reason(reason)
    with connect(path) as db:
        return _set_device_asset(db, device_id, asset_id, clean_reason, utc_now())
