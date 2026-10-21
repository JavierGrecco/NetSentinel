#!/usr/bin/env python3
"""Crea un dispositivo ficticio en una base nueva y aislada de NetSentinel.

No descubre la red ni abre sockets. Se niega a usar el directorio habitual o
una base SQLite existente para evitar modificar datos de una instalación real.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _private_ipv4(value: str) -> str:
    """Acepta una dirección IPv4 literal de una red privada RFC 1918."""
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Indicá una IPv4 privada literal.") from exc
    private_ranges = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )
    if address.version != 4 or not any(address in network for network in private_ranges):
        raise argparse.ArgumentTypeError(
            "La IP del dispositivo sintético debe pertenecer a una red privada RFC 1918."
        )
    return str(address)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea un único activo de prueba en una base NetSentinel nueva y aislada."
    )
    parser.add_argument(
        "--device-ip",
        type=_private_ipv4,
        default="192.168.56.20",
        help="IPv4 privada ficticia del activo (por defecto: 192.168.56.20).",
    )
    args = parser.parse_args()

    configured_dir = os.environ.get("NETSENTINEL_DATA_DIR", "").strip()
    if not configured_dir:
        parser.error(
            "Por seguridad, definí NETSENTINEL_DATA_DIR con una carpeta nueva y exclusiva para la prueba."
        )

    target_dir = Path(configured_dir).expanduser().resolve()
    normal_dir = (Path.home() / ".netsentinel").resolve()
    if target_dir == normal_dir:
        parser.error(
            "Se rechazó el directorio habitual ~/.netsentinel. Usá otra carpeta solo para pruebas."
        )

    # Importar NetSentinel solo después de validar la ruta: no inicializar por
    # accidente la ubicación de datos predeterminada.
    from netsentinel import database
    from netsentinel.config import database_path
    from netsentinel.network_models import Neighbor

    db_path = database_path()
    if db_path.exists() or db_path.is_symlink():
        parser.error(
            f"Ya existe una base SQLite en {db_path}. No se modificó; elegí un directorio de prueba nuevo."
        )
    if target_dir.exists() and (
        not target_dir.is_dir() or any(target_dir.iterdir())
    ):
        parser.error(
            "El directorio de datos no está vacío. Elegí una carpeta exclusiva y nueva para la prueba."
        )

    database.initialize()
    result = database.record_scan(
        [
            Neighbor(
                ip_address=args.device_ip,
                mac_address="02:00:00:00:00:20",
                interface="synthetic-fixture",
                source="synthetic-test-fixture",
            )
        ],
        discovery={"kind": "synthetic_fixture", "network_scan_performed": False},
    )

    now = datetime.now(timezone.utc).replace(microsecond=0)
    first_seen = (now - timedelta(days=30)).isoformat()
    last_seen = now.isoformat()
    with database.connect() as db:
        row = db.execute(
            "SELECT id FROM devices WHERE mac_address = ?",
            ("02:00:00:00:00:20",),
        ).fetchone()
        if row is None:
            raise RuntimeError("No se pudo verificar el dispositivo sintético creado.")
        device_id = int(row["id"])
        db.execute(
            """UPDATE devices SET ip_address = ?, first_seen = ?, last_seen = ?,
               display_name = ?, notes = ? WHERE id = ?""",
            (
                args.device_ip,
                first_seen,
                last_seen,
                "Dispositivo sintético de prueba",
                "Activo ficticio creado localmente para probar importaciones. No representa un equipo real.",
                device_id,
            ),
        )
        db.execute(
            """UPDATE device_addresses SET first_seen = ?, last_seen = ?, interface = ?, source = ?
               WHERE device_id = ? AND ip_address = ?""",
            (
                first_seen,
                last_seen,
                "synthetic-fixture",
                "synthetic-test-fixture",
                device_id,
                args.device_ip,
            ),
        )

    print("Base sintética creada sin descubrir equipos ni abrir conexiones de red.")
    print(f"Base SQLite: {db_path}")
    print(f"Dispositivo de prueba: {args.device_ip} (ID {device_id})")
    print("El historial de direcciones sintético abarca 30 días y permite probar atribución temporal de Zeek sin red real.")
    print("No apuntes NETSENTINEL_DATA_DIR a tu instalación habitual.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
