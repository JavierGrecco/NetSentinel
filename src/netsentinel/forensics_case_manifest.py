"""Exportación y verificación del expediente forense consolidado.

El manifiesto reúne metadatos declarados del caso, elementos registrados, comprobaciones
de SHA-256 y la auditoría encadenada. No contiene archivos de evidencia ni acredita por
sí solo la autenticidad del origen, la identidad del operador o una cadena de custodia
certificada. El digest detecta cambios respecto de una referencia conservada aparte.
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

from .forensics_audit_manifest import verify_audit_manifest

CASE_MANIFEST_FORMAT = "netsentinel-forensic-case-manifest"
CASE_MANIFEST_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Serializa el mismo contenido de forma estable entre ejecuciones."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def build_case_manifest(
    *,
    case: dict[str, Any],
    evidence: list[dict[str, Any]],
    audit_manifest: dict[str, Any],
    exported_at: str,
    reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construye una exportación autocontenida, sin incluir contenido de archivos."""
    evidence_entries: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    for source in evidence:
        entry = dict(source)
        entry_checks = entry.pop("integrity_checks", [])
        # Campos explícitos para que un cambio interno del modelo no filtre datos
        # privados ni agregue silenciosamente información al formato exportado.
        entry_fields = (
            "id",
            "case_id",
            "evidence_number",
            "label",
            "source_type",
            "original_name",
            "source_description",
            "received_from",
            "received_by",
            "received_at_original",
            "received_timezone",
            "size_bytes",
            "reported_sha256",
            "hash_source",
            "created_at",
            "hash_status",
            "last_integrity_check_status",
            "last_integrity_check_at",
            "last_calculated_sha256",
        )
        normalized_entry = {key: entry.get(key) for key in entry_fields}
        normalized_checks = [
            {
                key: check.get(key)
                for key in (
                    "id",
                    "case_id",
                    "evidence_id",
                    "checked_at",
                    "actor",
                    "copy_confirmed",
                    "algorithm",
                    "source_name",
                    "expected_sha256",
                    "calculated_sha256",
                    "size_bytes",
                    "status",
                    "tool_version",
                    "error_code",
                    "error_message",
                )
            }
            for check in entry_checks
        ]
        normalized_entry["integrity_checks"] = normalized_checks
        evidence_entries.append(normalized_entry)
        checks.extend(normalized_checks)

    audit_integrity = audit_manifest.get("integrity", {})
    audit_events = audit_manifest.get("events", [])
    report_entries = [
        {
            key: entry.get(key)
            for key in (
                "id", "case_id", "version", "title", "status", "created_at",
                "created_by", "amends_report_id", "report_sha256",
            )
        }
        for entry in (reports or [])
    ]
    payload: dict[str, Any] = {
        "format": CASE_MANIFEST_FORMAT,
        "schema_version": CASE_MANIFEST_SCHEMA_VERSION,
        "exported_at": exported_at,
        "case": {
            key: case.get(key)
            for key in (
                "id",
                "case_number",
                "title",
                "authority_reference",
                "objective",
                "scope",
                "examiner",
                "status",
                "created_at",
                "updated_at",
                "evidence_count",
            )
        },
        "evidence": evidence_entries,
        "reports": report_entries,
        # Conserva el manifiesto de auditoría original, incluida su propia huella.
        "audit_manifest": audit_manifest,
        "summary": {
            "evidence_count": len(evidence_entries),
            "report_count": len(report_entries),
            "evidence_with_reported_hash": sum(
                bool(item.get("reported_sha256")) for item in evidence_entries
            ),
            "evidence_without_reported_hash": sum(
                not item.get("reported_sha256") for item in evidence_entries
            ),
            "integrity_check_count": len(checks),
            "matching_check_count": sum(item.get("status") == "match" for item in checks),
            "mismatching_check_count": sum(item.get("status") == "mismatch" for item in checks),
            "failed_check_count": sum(item.get("status") == "failed" for item in checks),
            "audit_event_count": len(audit_events),
            "audit_chain_status": audit_integrity.get("status", "unknown"),
        },
    }
    payload["manifest_sha256"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return payload


def verify_case_manifest(manifest: object) -> bool:
    """Verifica el digest del expediente y el digest interno de su auditoría."""
    if not isinstance(manifest, dict):
        return False
    if (
        manifest.get("format") != CASE_MANIFEST_FORMAT
        or manifest.get("schema_version") != CASE_MANIFEST_SCHEMA_VERSION
        or not isinstance(manifest.get("case"), dict)
        or not isinstance(manifest.get("evidence"), list)
        or not all(isinstance(item, dict) for item in manifest["evidence"])
        or not isinstance(manifest.get("summary"), dict)
        or not isinstance(manifest.get("audit_manifest"), dict)
        or not verify_audit_manifest(manifest["audit_manifest"])
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
            "Comprueba el digest de un manifiesto consolidado de NetSentinel Forense. "
            "No es una firma digital ni autentica el origen de la evidencia."
        )
    )
    parser.add_argument("manifest", type=Path, help="Archivo JSON exportado")
    args = parser.parse_args(argv)
    try:
        with args.manifest.open("r", encoding="utf-8") as source:
            manifest = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError):
        print("No se pudo leer un manifiesto JSON válido.", file=sys.stderr)
        return 2

    if not verify_case_manifest(manifest):
        print(
            "Manifiesto inválido: el formato no es compatible o un digest no coincide.",
            file=sys.stderr,
        )
        return 1

    summary = manifest["summary"]
    chain_status = summary.get("audit_chain_status", "unknown")
    print(f"Digest del expediente verificado: {manifest['manifest_sha256']}")
    print(
        f"Evidencias: {summary.get('evidence_count', '?')}; "
        f"comprobaciones SHA-256: {summary.get('integrity_check_count', '?')}; "
        f"eventos de auditoría: {summary.get('audit_event_count', '?')}."
    )
    print(f"Estado de la cadena de auditoría incluida: {chain_status}.")
    print(
        "El digest no es una firma digital y no prueba por sí solo autenticidad, "
        "autoría ni una cadena de custodia certificada."
    )
    return 0 if chain_status == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
