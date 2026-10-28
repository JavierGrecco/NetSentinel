#!/usr/bin/env python3
"""Crea un dispositivo ficticio en una base nueva y aislada de NetSentinel.

No descubre la red ni abre sockets. Se niega a usar el directorio habitual o
una base SQLite existente para evitar modificar datos de una instalación real.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
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
    test_subnet = ipaddress.ip_network(f"{address}/24", strict=False)
    if address in {test_subnet.network_address, test_subnet.broadcast_address}:
        raise argparse.ArgumentTypeError(
            "Usá una dirección de equipo válida, no la dirección de red o difusión de la subred /24."
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
    parser.add_argument(
        "--include-findings-correlation",
        action="store_true",
        help="Añade un hallazgo sintético explícito para probar la correlación con Zeek; no es una observación real.",
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

    if args.include_findings_correlation:
        # Es un evento sintético optativo, distinto de una observación de red real.
        # El mensaje permite a la guía distinguir esta fixture de cualquier hallazgo real.
        with database.connect() as db:
            db.execute(
                """INSERT INTO events
                   (event_type, severity, device_id, created_at, message, acknowledged)
                   VALUES (?, ?, ?, ?, ?, 0)""",
                (
                    "new_device",
                    "warning",
                    device_id,
                    last_seen,
                    "Fixture sintética: evento de laboratorio para validar correlación Zeek; no representa una observación real.",
                ),
            )
        print("Se añadió un hallazgo sintético explícito para la prueba de correlación Zeek.")

    if args.include_topology:
        # Este modo optativo crea tres activos y una lectura claramente sintéticos.
        # Las filas se insertan directamente para no generar alertas de "dispositivo nuevo"
        # que puedan confundirse con hallazgos auténticos. No hay descubrimiento de red.
        network = ipaddress.ip_network(f"{args.device_ip}/24", strict=False)
        hosts = [str(candidate) for candidate in network.hosts()]
        extra_ips = [value for value in hosts if value != args.device_ip][:2]
        if len(extra_ips) != 2:
            parser.error("No se pudieron preparar tres direcciones de host dentro de la subred /24.")

        extra_specs = [
            ("02:00:00:00:00:21", extra_ips[0], "Equipo sintético adicional A"),
            ("02:00:00:00:00:22", extra_ips[1], "Equipo sintético adicional B"),
        ]
        device_by_ip = {args.device_ip: device_id}
        with database.connect() as db:
            for mac, ip_value, name in extra_specs:
                cursor = db.execute(
                    """INSERT INTO devices
                       (mac_address, ip_address, interface, first_seen, last_seen,
                        display_name, notes, mac_locally_administered)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        mac, ip_value, "synthetic-fixture", first_seen, last_seen,
                        name, "Activo de topología ficticio; no representa un equipo real.",
                    ),
                )
                extra_device_id = int(cursor.lastrowid)
                device_by_ip[ip_value] = extra_device_id
                db.execute(
                    """INSERT INTO device_addresses
                       (device_id, ip_address, first_seen, last_seen, interface, source)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        extra_device_id, ip_value, first_seen, last_seen,
                        "synthetic-fixture", "synthetic-test-fixture",
                    ),
                )

            scan_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            # La lectura y el historial de direcciones terminan en el mismo instante.
            # Así el fixture no sugiere que una observación quede fuera del intervalo del activo.
            for ip_value, candidate_id in device_by_ip.items():
                db.execute(
                    "UPDATE devices SET last_seen = ? WHERE id = ?",
                    (scan_time, candidate_id),
                )
                db.execute(
                    """UPDATE device_addresses SET last_seen = ?
                       WHERE device_id = ? AND ip_address = ?""",
                    (scan_time, candidate_id, ip_value),
                )
            local_address = next(value for value in hosts if value not in device_by_ip)
            discovery = {
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
            }
            cursor = db.execute(
                """INSERT INTO scans
                   (started_at, finished_at, source, devices_found, errors_json, discovery_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    scan_time, scan_time, "synthetic-test-fixture", len(device_by_ip),
                    "[]", json.dumps(discovery, ensure_ascii=False),
                ),
            )
            scan_id = int(cursor.lastrowid)
            db.executemany(
                """INSERT INTO observations
                   (scan_id, device_id, observed_at, ip_address, source)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (scan_id, candidate_id, scan_time, ip_value, "synthetic-test-fixture")
                    for ip_value, candidate_id in device_by_ip.items()
                ],
            )
        print("Se añadió una lectura sintética con tres activos para probar el explorador LAN.")
    else:
        print("No se crearon lecturas, observaciones ni eventos de descubrimiento.")

    print(f"Base SQLite: {db_path}")
    print(f"Dispositivo de prueba: {args.device_ip} (ID {device_id})")
    print("El historial de IP de prueba abarca 30 días para permitir atribución temporal de Zeek.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
