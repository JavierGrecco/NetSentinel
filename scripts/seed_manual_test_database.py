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
    parser.add_argument(
        "--include-topology",
        action="store_true",
        help="Añade una única lectura y observación de topología marcadas como sintéticas; no son un escaneo real.",
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

    # Insertamos solo el activo ficticio y su historial de IP. No creamos una
    # lectura, una observación ni un evento de descubrimiento que pueda parecer real.
    now = datetime.now(timezone.utc).replace(microsecond=0)
    first_seen = (now - timedelta(days=30)).isoformat()
    last_seen = now.isoformat()
    with database.connect() as db:
        cursor = db.execute(
            """INSERT INTO devices
               (mac_address, ip_address, interface, first_seen, last_seen,
                display_name, notes, mac_locally_administered)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                "02:00:00:00:00:20",
                args.device_ip,
                "synthetic-fixture",
                first_seen,
                last_seen,
                "Dispositivo sintético de prueba",
                "Activo ficticio creado localmente para probar importaciones. No representa un equipo real.",
            ),
        )
        device_id = int(cursor.lastrowid)
        db.execute(
            """INSERT INTO device_addresses
               (device_id, ip_address, first_seen, last_seen, interface, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                device_id,
                args.device_ip,
                first_seen,
                last_seen,
                "synthetic-fixture",
                "synthetic-test-fixture",
            ),
        )

    if args.include_topology:
        # Este modo optativo crea una lectura explícitamente sintética para
        # revisar el explorador LAN. No ejecuta comandos ni consulta la red.
        from netsentinel.network_models import Neighbor

        network = ipaddress.ip_network(f"{args.device_ip}/24", strict=False)
        local_address = next(
            str(candidate)
            for candidate in network.hosts()
            if str(candidate) != args.device_ip
        )
        database.record_scan(
            [
                Neighbor(
                    ip_address=args.device_ip,
                    mac_address="02:00:00:00:00:20",
                    interface="synthetic-fixture",
                    source="synthetic-test-fixture",
                )
            ],
            errors=[],
            discovery={
                "networks": [
                    {
                        "network": network.with_prefixlen,
                        "interface": "synthetic-fixture",
                        "local_address": local_address,
                        "range_limited": False,
                    }
                ],
                "scope": "Solo fixture sintética; no representa una red real.",
                "kind": "synthetic_fixture",
                "network_scan_performed": False,
            },
        )
        print("Se añadió una lectura sintética explícita para probar el explorador LAN.")
    else:
        print("No se crearon lecturas, observaciones ni eventos de descubrimiento.")

    print(f"Base SQLite: {db_path}")
    print(f"Dispositivo de prueba: {args.device_ip} (ID {device_id})")
    print("El historial de IP de prueba abarca 30 días para permitir atribución temporal de Zeek.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
