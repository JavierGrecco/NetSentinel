#!/usr/bin/env python3
"""Genera archivos de prueba sintéticos para recorridos manuales de NetSentinel.

El script solo escribe archivos locales. No abre sockets, no consulta DNS y no
inicia la aplicación ni escribe en su base SQLite.
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT = Path("netsentinel-test-artifacts/manual-scenarios")
CSV_FIELDS = [
    "observed_at",
    "event_type",
    "domain",
    "destination_ip",
    "destination_port",
    "protocol",
    "app_name",
    "blocked",
    "page_url",
    "search_engine",
    "search_terms",
]
ZEEK_FIELDS = [
    "ts",
    "uid",
    "id.orig_h",
    "id.orig_p",
    "id.resp_h",
    "id.resp_p",
    "proto",
    "orig_ip_bytes",
    "resp_ip_bytes",
    "orig_pkts",
    "resp_pkts",
]


def _iso_utc(value: datetime) -> str:
    """Serializa una hora en UTC en el formato aceptado por el importador CSV."""
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _validate_device_ip(value: str) -> str:
    """Acepta solo una dirección IP literal, sin hostname ni resolución DNS."""
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "Indicá una dirección IP literal del dispositivo que vas a seleccionar en NetSentinel."
        ) from exc


def _csv_text(rows: list[dict[str, Any]]) -> str:
    """Produce CSV estable, UTF-8 y con finales de línea compatibles entre sistemas."""
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build_scenarios(device_ip: str, now: datetime | None = None) -> dict[str, str]:
    """Construye todos los escenarios en memoria sin acceso a red ni a la base de datos."""
    normalized_device_ip = _validate_device_ip(device_ip)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc).replace(microsecond=0)

    activity_rows = [
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=50)),
            "event_type": "dns_query",
            "domain": "dns-probe.invalid",
            "destination_ip": "1.1.1.1",
            "destination_port": "53",
            "protocol": "udp",
            "app_name": "Resolvedor de prueba",
            "blocked": "0",
        },
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=40)),
            "event_type": "connection",
            "domain": "web-probe.invalid",
            "destination_ip": "1.1.1.1",
            "destination_port": "443",
            "protocol": "tcp",
            "app_name": "Navegador de prueba",
            "blocked": "0",
        },
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=30)),
            "event_type": "tls_sni",
            "domain": "tls-probe.invalid",
            "destination_ip": "203.0.113.10",
            "destination_port": "443",
            "protocol": "tcp",
            "app_name": "Cliente TLS sintético",
            "blocked": "0",
        },
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=20)),
            "event_type": "blocked",
            "domain": "policy-probe.invalid",
            "destination_ip": "198.51.100.20",
            "destination_port": "443",
            "protocol": "tcp",
            "app_name": "Prueba de política",
            "blocked": "1",
        },
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=10)),
            "event_type": "app_usage",
            "app_name": "Aplicación simulada",
            "blocked": "0",
        },
        {
            "observed_at": _iso_utc(current - timedelta(minutes=5, seconds=5)),
            "event_type": "search_query",
            "search_engine": "Motor de prueba",
            "search_terms": "consulta ficticia sin datos personales",
            "blocked": "0",
        },
    ]
    activity_csv = _csv_text(activity_rows)

    # Los eventos Zeek también se usan en el laboratorio de correlación de Hallazgos.
    # Dejamos margen amplio dentro de la ventana fija de ±300 segundos, incluso si
    # la persona genera los archivos y siembra la base con algunos minutos de diferencia.
    # La IP pública de ejemplo solo ejercita GeoIP; no implica relación con un dominio.
    base_ts = int(current.timestamp()) - 60
    zeek_records = [
        {
            "ts": base_ts - 45,
            "uid": "CManualScenario001",
            "id.orig_h": normalized_device_ip,
            "id.orig_p": 51514,
            "id.resp_h": "1.1.1.1",
            "id.resp_p": 443,
            "proto": "tcp",
            "orig_ip_bytes": 128,
            "resp_ip_bytes": 256,
            "orig_pkts": 2,
            "resp_pkts": 3,
        },
        {
            "ts": base_ts - 30,
            "uid": "CManualScenario002",
            "id.orig_h": normalized_device_ip,
            "id.orig_p": 51515,
            "id.resp_h": "203.0.113.53",
            "id.resp_p": 53,
            "proto": "udp",
            "orig_ip_bytes": 0,
            "resp_ip_bytes": 0,
            "orig_pkts": 0,
            "resp_pkts": 0,
        },
        {
            "ts": base_ts - 15,
            "uid": "CManualScenario003",
            "id.orig_h": "198.51.100.42",
            "id.orig_p": 443,
            "id.resp_h": normalized_device_ip,
            "id.resp_p": 51516,
            "proto": "tcp",
            "orig_pkts": 4,
            "resp_pkts": 5,
        },
    ]
    zeek_jsonl = "\n".join(
        json.dumps(record, sort_keys=True, separators=(",", ":"))
        for record in zeek_records
    ) + "\n"

    # Formato nativo conn.log con campos ausentes marcados por el guion de Zeek.
    tsv_records = [
        [
            str(base_ts - 45), "CManualScenario101", normalized_device_ip, "51514",
            "198.51.100.10", "443", "tcp", "128", "256", "2", "3",
        ],
        [
            str(base_ts - 30), "CManualScenario102", normalized_device_ip, "51515",
            "203.0.113.53", "53", "udp", "-", "0", "-", "0",
        ],
    ]
    tsv_lines = [
        r"#separator \x09",
        "#set_separator ,",
        "#empty_field (empty)",
        "#unset_field -",
        "#path conn",
        "#open " + current.strftime("%Y-%m-%d-%H-%M-%S"),
        "#fields " + "\t".join(ZEEK_FIELDS),
        "#types " + "\t".join(["time", "string", "addr", "port", "addr", "port", "enum", "count", "count", "count", "count"]),
    ]
    tsv_lines.extend("\t".join(row) for row in tsv_records)
    tsv_lines.append("#close " + current.strftime("%Y-%m-%d-%H-%M-%S"))
    zeek_tsv = "\n".join(tsv_lines) + "\n"

    sensitive_csv = (
        "observed_at,event_type,message_body\n"
        f"{_iso_utc(current - timedelta(seconds=5))},email_metadata,SYNTHETIC_BODY_MUST_BE_REJECTED\n"
    )
    duplicate_header_csv = (
        "observed_at,date,event_type,domain\n"
        f"{_iso_utc(current - timedelta(seconds=5))},{_iso_utc(current - timedelta(seconds=5))},dns_query,dns-probe.invalid\n"
    )
    invalid_zeek_jsonl = zeek_jsonl.splitlines()[0] + "\n{this is not valid JSON}\n"

    readme = f"""ESCENARIOS SINTETICOS DE NETSENTINEL
====================================

Todos los archivos de esta carpeta son ejemplos inventados para pruebas.
No representan observaciones reales y no deben cargarse en la base habitual.

Contenido:
- activity.csv: seis eventos válidos para Actividad. Reimportarlo permite
  comprobar la detección de duplicados.
- activity-invalid-sensitive.csv: debe ser rechazado por su cabecera sensible.
- activity-invalid-duplicate-header.csv: debe ser rechazado por cabeceras
  que se convierten en el mismo campo tras normalizarse.
- zeek-conn.jsonl: tres registros JSON Lines con contadores presentes, cero
  informado, contadores ausentes y una conexión con el dispositivo como destino.
- zeek-conn.tsv: ejemplo nativo conn.log con directivas #separator/#fields/#types.
- zeek-invalid.jsonl: contiene una línea JSON incorrecta; no debe importar
  parcialmente la línea válida anterior.

La IP del dispositivo usada para los registros Zeek es {normalized_device_ip}.
Generado en UTC: {_iso_utc(current)}.

La IP pública 1.1.1.1 se usa solo para probar la representación GeoIP. Los
dominios *.invalid son ficticios y NO se afirma que resuelvan a esa IP. Es una
dirección anycast: la ubicación de la base GeoIP es aproximada y puede variar.
Las direcciones 192.0.2.0/24, 198.51.100.0/24 y 203.0.113.0/24 son bloques de
documentación y no deben mostrarse como destinos geográficos públicos reales.

Para los registros Zeek, elegí en la interfaz un dispositivo cuya dirección
histórica coincida con la IP indicada, y generá los archivos con --device-ip
usando esa dirección. Refrescá primero el inventario si la dirección no tiene
una observación reciente. La importación Zeek conserva el alcance temporal y
no asigna filas a un equipo solo porque el nombre se parezca.

El generador no hace consultas DNS, conexiones de red ni escrituras SQLite.
"""
    return {
        "activity.csv": activity_csv,
        "activity-invalid-sensitive.csv": sensitive_csv,
        "activity-invalid-duplicate-header.csv": duplicate_header_csv,
        "zeek-conn.jsonl": zeek_jsonl,
        "zeek-conn.tsv": zeek_tsv,
        "zeek-invalid.jsonl": invalid_zeek_jsonl,
        "README.txt": readme,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera CSV y registros Zeek sintéticos; no contacta la red ni modifica SQLite."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Directorio de salida (por defecto: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--device-ip",
        type=_validate_device_ip,
        default="192.168.56.20",
        help="IP literal que se incluirá en las conexiones Zeek (ajustala al dispositivo de prueba).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reemplaza los archivos de escenario que ya existan en el directorio.",
    )
    args = parser.parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    contents = build_scenarios(args.device_ip)
    existing = sorted(name for name in contents if (output_dir / name).exists())
    if existing and not args.force:
        parser.error(
            "Ya existen archivos de escenario y no se modificaron: "
            + ", ".join(existing)
            + ". Elegí otro --output-dir o agregá --force para reemplazarlos."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (output_dir / name).write_text(content, encoding="utf-8", newline="")
    print(f"Se generaron {len(contents)} archivos sintéticos en: {output_dir}")
    print("No se modificó la base SQLite ni se realizó ninguna conexión de red.")
    print("Usá estos archivos únicamente con una base de datos de prueba aislada.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
