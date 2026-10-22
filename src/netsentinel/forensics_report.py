"""Construcción y verificación de informes de examen versionados.

Conserva la captura del expediente que recibió el examinador y marca el informe como
borrador sin firma. Su digest permite detectar cambios contra una referencia guardada,
pero no autentica al autor ni representa una firma digital.
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

from .forensics_case_manifest import verify_case_manifest

REPORT_FORMAT = "netsentinel-forensic-examination-report"
REPORT_SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Serializa los mismos datos de forma estable para comprobar su digest."""
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_without_digest(payload: dict[str, Any]) -> str:
    canonical_payload = dict(payload)
    canonical_payload.pop("report_sha256", None)
    return hashlib.sha256(_canonical_bytes(canonical_payload)).hexdigest()


def build_examination_report(
    *,
    report_id: str,
    version: int,
    fields: dict[str, Any],
    case_manifest: dict[str, Any],
    created_at: str,
    actor: str,
    amends_report_id: str | None,
) -> dict[str, Any]:
    """Crea una instantánea versionada, marcada explícitamente como borrador sin firma."""
    if not verify_case_manifest(case_manifest):
        raise ValueError("No se puede incluir un expediente base cuyo digest no sea verificable.")
    source_integrity = case_manifest.get("summary", {}).get("audit_chain_status", "unknown")
    report: dict[str, Any] = {
        "format": REPORT_FORMAT,
        "schema_version": REPORT_SCHEMA_VERSION,
        "report": {
            "id": report_id,
            "version": version,
            "status": "draft_unsigned",
            "title": fields["title"],
            "created_at": created_at,
            "created_by": actor,
            "amends_report_id": amends_report_id,
            "amendment_reason": fields.get("amendment_reason"),
            "authorization": {
                "status": "unsigned_pending_review",
                "authorizer_name": fields.get("authorizer_name"),
                "signature": None,
                "note": (
                    "Este documento es un borrador sin firma ni autorización verificada. "
                    "El nombre del autor o autorizador es declarado por quien carga los datos."
                ),
            },
        },
        "case": case_manifest["case"],
        "request": {
            "request_date": fields["request_date"],
            "requester_name": fields["requester_name"],
            "requester_organization": fields["requester_organization"],
            "authority_reference": case_manifest["case"].get("authority_reference"),
            "purpose": fields["purpose"],
            "scope_performed": fields["scope_performed"],
        },
        "examining_organization": fields["examining_organization"],
        "author_name": fields["author_name"],
        "examination": {
            "processes_performed": fields["processes_performed"],
            "results": fields["results"],
            "conclusions": fields.get("conclusions"),
            "conclusion_basis": fields.get("conclusion_basis"),
            "limitations": fields["limitations"],
            "deviations": fields.get("deviations"),
            "supporting_material": fields.get("supporting_material"),
        },
        "disposition": {
            "originals": fields["original_disposition"],
            "derivatives": fields["derivative_disposition"],
        },
        "source_case_manifest": case_manifest,
        "integrity": {
            "source_case_manifest_sha256": case_manifest["manifest_sha256"],
            "source_audit_chain_status": source_integrity,
            "source_audit_event_count": case_manifest.get("summary", {}).get("audit_event_count", 0),
            "source_evidence_count": case_manifest.get("summary", {}).get("evidence_count", 0),
            "warning": (
                None if source_integrity == "valid"
                else "La cadena de auditoría de la captura base no figura como válida. "
                "El informe conserva ese estado; no lo corrige ni lo oculta."
            ),
        },
        "verification_note": (
            "El digest SHA-256 ayuda a detectar cambios contra una copia de referencia. "
            "No es una firma digital, no autentica al autor y no demuestra por sí solo "
            "la integridad del sistema que produjo el documento."
        ),
    }
    report["report_sha256"] = _sha256_without_digest(report)
    return report


def verify_examination_report(report: object) -> bool:
    """Verifica el digest del informe, sus secciones y el expediente base incluido."""
    if not isinstance(report, dict):
        return False
    if report.get("format") != REPORT_FORMAT or report.get("schema_version") != REPORT_SCHEMA_VERSION:
        return False
    stored_digest = report.get("report_sha256")
    if not isinstance(stored_digest, str) or not _SHA256_RE.fullmatch(stored_digest):
        return False
    if not hmac.compare_digest(stored_digest, _sha256_without_digest(report)):
        return False

    report_meta = report.get("report")
    if not isinstance(report_meta, dict) or report_meta.get("status") != "draft_unsigned":
        return False
    authorization = report_meta.get("authorization")
    if (
        not isinstance(authorization, dict)
        or authorization.get("status") != "unsigned_pending_review"
        or authorization.get("signature") is not None
    ):
        return False

    source_manifest = report.get("source_case_manifest")
    if not verify_case_manifest(source_manifest):
        return False
    report_case = report.get("case")
    if not isinstance(report_case, dict) or report_case != source_manifest.get("case"):
        return False
    for key in ("request", "examination", "disposition", "integrity"):
        if not isinstance(report.get(key), dict):
            return False
    if not isinstance(report.get("examining_organization"), str):
        return False
    if not isinstance(report.get("author_name"), str):
        return False

    integrity = report["integrity"]
    return (
        integrity.get("source_case_manifest_sha256") == source_manifest.get("manifest_sha256")
        and integrity.get("source_audit_chain_status")
        == source_manifest.get("summary", {}).get("audit_chain_status", "unknown")
    )


def _markdown_text(value: Any) -> str:
    """Neutraliza estructura Markdown en los datos declarados del informe exportado."""
    if value is None:
        return "No informado"
    tick = chr(96)
    text = (str(value).replace("\\", "\\\\").replace(tick, "\\" + tick)
        .replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
        .replace("[", "\\[").replace("]", "\\]").replace("!", "\\!")
        .replace("(", "\\(").replace(")", "\\)").replace("*", "\\*").replace("_", "\\_"))
    safe_lines: list[str] = []
    for line in text.splitlines() or [""]:
        if re.match(r"^\s{0,3}(#{1,6}|>|[-+*]\s)", line):
            line = "\\" + line
        safe_lines.append(line)
    return "\n".join(safe_lines).strip() or "No informado"


def _markdown_table_cell(value: Any) -> str:
    """Mantiene los valores de las tablas en una sola fila de Markdown."""
    return _markdown_text(value).replace("\r", " ").replace("\n", " ")


def render_examination_report_markdown(report: dict[str, Any]) -> str:
    """Genera una versión legible a partir del JSON verificado, sin afirmar autorización."""
    if not verify_examination_report(report):
        raise ValueError("El informe no superó la verificación de integridad.")
    meta = report["report"]
    case = report["case"]
    request = report["request"]
    examination = report["examination"]
    disposition = report["disposition"]
    evidence = report["source_case_manifest"].get("evidence", [])
    tick = chr(96)
    lines = [
        "# " + _markdown_text(meta["title"]),
        "",
        "> **BORRADOR SIN FIRMA — NO ES UN INFORME AUTORIZADO.**",
        "",
        f"- Caso: {_markdown_text(case.get('case_number'))}",
        f"- Versión del informe: {meta['version']}",
        f"- Identificador del informe: {tick}{_markdown_text(meta['id'])}{tick}",
        f"- Generado en NetSentinel: {_markdown_text(meta['created_at'])}",
        f"- Organización examinadora declarada: {_markdown_text(report.get('examining_organization'))}",
        f"- Autor declarado: {_markdown_text(report.get('author_name'))}",
        f"- Estado de autorización: {_markdown_text(meta['authorization']['status'])}",
    ]
    if meta.get("amends_report_id"):
        lines.extend([
            f"- Versión anterior: {tick}{_markdown_text(meta['amends_report_id'])}{tick}",
            f"- Motivo de la enmienda: {_markdown_text(meta.get('amendment_reason'))}",
        ])
    lines.extend([
        "",
        "## Solicitud y alcance",
        "",
        f"- Fecha de solicitud: {_markdown_text(request.get('request_date'))}",
        f"- Solicitante: {_markdown_text(request.get('requester_name'))}",
        f"- Organización solicitante: {_markdown_text(request.get('requester_organization'))}",
        f"- Autoridad de referencia: {_markdown_text(request.get('authority_reference'))}",
        "",
        "### Propósito",
        "",
        _markdown_text(request.get("purpose")),
        "",
        "### Alcance efectivamente realizado",
        "",
        _markdown_text(request.get("scope_performed")),
        "",
        "## Elementos registrados en la captura base",
        "",
        "| Identificador | Descripción | Tipo | Hash informado | Última comprobación |",
        "|---|---|---|---|---|",
    ])
    for item in evidence:
        lines.append(
            "| " + " | ".join(_markdown_table_cell(value) for value in (
                item.get("evidence_number"),
                item.get("label"),
                item.get("source_type"),
                item.get("reported_sha256"),
                item.get("last_integrity_check_status"),
            )) + " |"
        )
    if not evidence:
        lines.append("| No hay elementos registrados | — | — | — | — |")
    lines.extend([
        "",
        "## Procedimientos realizados",
        "",
        _markdown_text(examination.get("processes_performed")),
        "",
        "## Resultados",
        "",
        _markdown_text(examination.get("results")),
        "",
        "## Conclusiones y fundamento",
        "",
        _markdown_text(examination.get("conclusions")),
        "",
        "### Base de las conclusiones",
        "",
        _markdown_text(examination.get("conclusion_basis")),
        "",
        "## Limitaciones",
        "",
        _markdown_text(examination.get("limitations")),
        "",
        "## Desviaciones de procedimiento",
        "",
        _markdown_text(examination.get("deviations")),
        "",
        "## Material de apoyo",
        "",
        _markdown_text(examination.get("supporting_material")),
        "",
        "## Disposición",
        "",
        "- Originales: " + _markdown_text(disposition.get("originals")),
        "- Derivados: " + _markdown_text(disposition.get("derivatives")),
        "",
        "## Integridad y trazabilidad",
        "",
        f"- Digest SHA-256 del informe: {tick}{report['report_sha256']}{tick}",
        f"- Digest SHA-256 del expediente base: {tick}{report['integrity']['source_case_manifest_sha256']}{tick}",
        f"- Estado de la cadena de auditoría en la captura base: **{_markdown_text(report['integrity']['source_audit_chain_status'])}**",
        f"- Eventos de auditoría en la captura base: {report['integrity']['source_audit_event_count']}",
        "",
    ])
    if report["integrity"].get("warning"):
        lines.extend(["**Advertencia de integridad:** " + _markdown_text(report["integrity"]["warning"]), ""])
    lines.extend([
        "## Autorización",
        "",
        "Autorizador declarado: " + _markdown_text(meta["authorization"].get("authorizer_name")),
        "",
        "**No hay firma digital ni autorización autenticada. Este archivo no debe tratarse como versión final aprobada.**",
        "",
        _markdown_text(report.get("verification_note")),
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica un informe de examen NetSentinel en JSON.")
    parser.add_argument("report", type=Path, help="Ruta del JSON del informe exportado.")
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"No se pudo leer el informe: {exc}", file=sys.stderr)
        return 2
    if not verify_examination_report(report):
        print("Informe no válido: digest o expediente base incorrecto.", file=sys.stderr)
        return 1
    print("Informe verificable en formato NetSentinel; estado: borrador sin firma.")
    print(f"SHA-256: {report['report_sha256']}")
    print(f"Caso: {report['case'].get('case_number', 'no identificado')}")
    print(f"Versión: {report['report']['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
