"""Exportación canónica y verificación local de manifiestos de auditoría forense.

El SHA-256 embebido detecta cambios accidentales si se compara con una huella guardada
por separado. No es una firma ni demuestra autoría: quien edite el manifiesto puede
calcular otra huella, por lo que la confianza exige un anclaje externo independiente.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import sys
from pathlib import Path
from typing import Any

MANIFEST_FORMAT = "netsentinel-forensic-audit-manifest"
MANIFEST_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Serializa los mismos datos de forma estable entre ejecuciones."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def build_audit_manifest(
    *,
    case: dict[str, Any],
    events: list[dict[str, Any]],
    exported_at: str,
) -> dict[str, Any]:
    """Genera un manifiesto autocontenido con eventos en orden cronológico."""
    statuses = [event.get("integrity_status") for event in events]
    valid_count = statuses.count("valid")
    invalid_count = statuses.count("invalid")
    missing_count = statuses.count("missing")
    overall_status = (
        "invalid" if invalid_count else "missing" if missing_count else "valid"
    )
    payload: dict[str, Any] = {
        "format": MANIFEST_FORMAT,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "exported_at": exported_at,
        "case": {
            key: case.get(key)
            for key in ("id", "case_number", "title", "status", "created_at", "updated_at")
        },
        "integrity": {
            "status": overall_status,
            "event_count": len(events),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "missing_count": missing_count,
        },
        "events": events,
    }
    payload["manifest_sha256"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return payload


def verify_audit_manifest(manifest: object) -> bool:
    """Comprueba formato soportado y el digest canónico del contenido del manifiesto."""
    if not isinstance(manifest, dict):
        return False
    if (
        manifest.get("format") != MANIFEST_FORMAT
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or not isinstance(manifest.get("case"), dict)
        or not isinstance(manifest.get("integrity"), dict)
        or not isinstance(manifest.get("events"), list)
    ):
        return False
    expected = manifest.get("manifest_sha256")
    if not isinstance(expected, str) or not _SHA256_RE.fullmatch(expected):
        return False
    payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    try:
        calculated = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    return hmac.compare_digest(expected, calculated)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica el SHA-256 interno de un manifiesto NetSentinel Forense. "
            "Esto no comprueba una firma digital ni autentica su origen."
        )
    )
    parser.add_argument("manifest", type=Path, help="Ruta del archivo JSON exportado")
    args = parser.parse_args(argv)
    try:
        with args.manifest.open("r", encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"No se pudo leer un manifiesto JSON válido: {exc}", file=sys.stderr)
        return 2
    if not verify_audit_manifest(manifest):
        print(
            "Manifiesto inválido: el formato no es compatible o el SHA-256 no coincide.",
            file=sys.stderr,
        )
        return 1
    integrity = manifest["integrity"]
    print(
        "Digest del manifiesto verificado: "
        f"{manifest['manifest_sha256']} "
        f"({integrity.get('event_count', '?')} eventos; "
        f"cadena {integrity.get('status', 'desconocida')})."
    )
    print(
        "Esta comprobación no verifica una firma externa ni prueba la autenticidad "
        "del archivo o de su origen."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
