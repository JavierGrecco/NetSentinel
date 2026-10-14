"""Auditoría TLS puntual de endpoints autorizados, sin solicitar contenido HTTP."""

from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import time
from typing import Any

# The outer deadline includes interpreter startup, which is outside the socket timeout.
_CHILD_PROCESS_STARTUP_GRACE_SECONDS = 1.0
_MAX_TIMEOUT_SECONDS = 3.0
_HOST_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_LEGACY_TLS_VERSIONS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}


def _normalise_host(host: str) -> str:
    """Acepta un nombre de host o IP; no acepta URL, rutas ni credenciales."""
    value = host.strip().rstrip(".")
    if not value or len(value) > 253 or any(ord(char) <= 32 for char in value):
        raise ValueError("Ingresá un nombre de host o una dirección IP, sin URL ni ruta.")
    if any(char in value for char in "/\\?#@[]"):
        raise ValueError("Ingresá solo el host o la IP, sin esquema, ruta ni credenciales.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        if ":" in value:
            raise ValueError("La dirección IP o el nombre de host no es válido.")
        try:
            value = value.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("El nombre de host no es válido.") from exc
        labels = value.split(".")
        if not all(_HOST_LABEL.fullmatch(label) for label in labels):
            raise ValueError("El nombre de host no es válido.")
        return value
    if getattr(address, "scope_id", None):
        raise ValueError("Las direcciones IPv6 con identificador de interfaz no están admitidas.")
    return str(address)


def _name_parts(value: Any) -> str | None:
    """Convierte los nombres X.509 de la biblioteca ssl en texto legible."""
    if not value:
        return None
    parts: list[str] = []
    for rdn in value:
        for item in rdn:
            if len(item) == 2:
                key, field_value = item
                parts.append(f"{key}={field_value}")
    return ", ".join(parts) if parts else None


def _result(host: str, port: int, status: str, summary: str, *,
            findings: list[dict[str, str]] | None = None,
            certificate: dict[str, Any] | None = None,
            tls: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "host": host,
        "port": port,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "summary": summary,
        "certificate": certificate,
        "tls": tls,
        "findings": findings or [],
        "notice": (
            "Inspección de una sola conexión TLS; no se solicitaron páginas ni contenido HTTP. "
            "El resultado no sustituye una auditoría de seguridad completa."
        ),
    }


def _certificate_failure(host: str, port: int, exc: ssl.SSLCertVerificationError) -> dict[str, Any]:
    verify_code = getattr(exc, "verify_code", None)
    message = str(getattr(exc, "verify_message", "") or "").lower()
    if verify_code == 10 or "expired" in message:
        code, severity = "certificate_expired", "critical"
        summary = "El certificado TLS está vencido y el sistema no confía en esta conexión."
        title = "Certificado vencido"
    elif verify_code == 9 or "not yet valid" in message:
        code, severity = "certificate_not_yet_valid", "high"
        summary = "El certificado TLS todavía no está dentro de su período de validez."
        title = "Certificado aún no válido"
    elif verify_code == 62 or "hostname mismatch" in message:
        code, severity = "certificate_name_mismatch", "high"
        summary = "El nombre del certificado no coincide con el host consultado."
        title = "El nombre no coincide"
    else:
        code, severity = "certificate_untrusted", "high"
        summary = "No se pudo validar la cadena de confianza del certificado TLS."
        title = "Certificado no confiable"
    return _result(
        host, port, "warning", summary,
        findings=[{"code": code, "severity": severity, "title": title, "detail": summary}],
    )


def _inspect_tls_endpoint_direct(host: str, port: int = 443, timeout: float = _MAX_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Valida un certificado TLS y muestra metadatos del handshake, sin hacer una petición HTTP."""
    normalised_host = _normalise_host(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("El puerto debe ser un número entre 1 y 65535.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= _MAX_TIMEOUT_SECONDS:
        raise ValueError("El tiempo límite debe ser mayor que cero y no superar 3 segundos.")

    # Use a single monotonic budget for TCP setup and the TLS handshake.
    # DNS implementations may block outside socket timeouts, so the parent
    # process still enforces the hard wall-clock deadline.
    deadline = time.monotonic() + float(timeout)
    try:
        context = ssl.create_default_context()
        with socket.create_connection((normalised_host, port), timeout=float(timeout)) as connection:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise socket.timeout("TLS inspection deadline exceeded")
            connection.settimeout(remaining)
            with context.wrap_socket(connection, server_hostname=normalised_host) as secured:
                peer_certificate = secured.getpeercert()
                tls_version = secured.version()
                cipher_info = secured.cipher()
    except ssl.SSLCertVerificationError as exc:
        return _certificate_failure(normalised_host, port, exc)
    except (socket.timeout, TimeoutError):
        summary = "La conexión superó el tiempo límite de 3 segundos."
        return _result(
            normalised_host, port, "timeout", summary,
            findings=[{"code": "connection_timeout", "severity": "warning", "title": "Tiempo agotado", "detail": summary}],
        )
    except ssl.SSLError:
        summary = "El endpoint no completó un intercambio TLS compatible. Verificá el puerto y la configuración TLS del servicio."
        return _result(
            normalised_host, port, "warning", summary,
            findings=[{"code": "tls_handshake_failed", "severity": "high", "title": "Falló el handshake TLS", "detail": summary}],
        )
    except OSError:
        summary = "No se pudo conectar al endpoint. Verificá el host, el puerto y la disponibilidad del servicio."
        return _result(
            normalised_host, port, "error", summary,
            findings=[{"code": "endpoint_unreachable", "severity": "warning", "title": "Endpoint inaccesible", "detail": summary}],
        )

    if not isinstance(peer_certificate, dict) or not peer_certificate:
        summary = "La conexión TLS se completó, pero el sistema no devolvió metadatos del certificado."
        return _result(
            normalised_host, port, "warning", summary,
            findings=[{"code": "certificate_metadata_unavailable", "severity": "medium", "title": "Metadatos no disponibles", "detail": summary}],
            tls={"version": tls_version, "cipher": cipher_info[0] if cipher_info else None,
                 "cipher_bits": cipher_info[2] if cipher_info and len(cipher_info) > 2 else None},
        )

    certificate: dict[str, Any] = {
        "subject": _name_parts(peer_certificate.get("subject")),
        "issuer": _name_parts(peer_certificate.get("issuer")),
        "valid_from": None,
        "valid_until": None,
        "days_remaining": None,
        "dns_names": [
            str(value) for kind, value in peer_certificate.get("subjectAltName", ())
            if kind in {"DNS", "IP Address"}
        ][:20],
    }
    findings: list[dict[str, str]] = []
    status = "ok"
    summary = "El certificado fue validado y la conexión TLS se estableció correctamente."

    try:
        not_before = peer_certificate.get("notBefore")
        not_after = peer_certificate.get("notAfter")
        if not_before:
            certificate["valid_from"] = datetime.fromtimestamp(
                ssl.cert_time_to_seconds(not_before), tz=timezone.utc
            ).isoformat(timespec="seconds")
        if not_after:
            expiry = datetime.fromtimestamp(ssl.cert_time_to_seconds(not_after), tz=timezone.utc)
            certificate["valid_until"] = expiry.isoformat(timespec="seconds")
            days_remaining = int((expiry - datetime.now(timezone.utc)).total_seconds() // 86400)
            certificate["days_remaining"] = days_remaining
            if days_remaining <= 7:
                status = "warning"
                summary = f"El certificado está validado, pero vence en {max(days_remaining, 0)} días."
                findings.append({
                    "code": "certificate_expiring_soon",
                    "severity": "high" if days_remaining >= 0 else "critical",
                    "title": "Certificado próximo a vencer",
                    "detail": summary,
                })
            elif days_remaining <= 30:
                status = "warning"
                summary = f"El certificado está validado, pero vence en {days_remaining} días."
                findings.append({
                    "code": "certificate_expiring_soon",
                    "severity": "medium",
                    "title": "Certificado próximo a vencer",
                    "detail": summary,
                })
    except (OverflowError, TypeError, ValueError):
        summary = "El handshake TLS se validó, pero no se pudo interpretar la fecha del certificado."
        status = "warning"
        findings.append({
            "code": "certificate_date_unreadable",
            "severity": "medium",
            "title": "Fecha de certificado no interpretable",
            "detail": summary,
        })

    if tls_version in _LEGACY_TLS_VERSIONS:
        status = "warning"
        legacy_summary = f"El servicio negoció {tls_version}, una versión TLS obsoleta."
        findings.append({
            "code": "legacy_tls_version",
            "severity": "high",
            "title": "Versión TLS obsoleta",
            "detail": legacy_summary,
        })
        summary = legacy_summary

    return _result(
        normalised_host, port, status, summary, findings=findings,
        certificate=certificate,
        tls={
            "version": tls_version,
            "cipher": cipher_info[0] if cipher_info else None,
            "cipher_bits": cipher_info[2] if cipher_info and len(cipher_info) > 2 else None,
        },
    )



def inspect_tls_endpoint(host: str, port: int = 443, timeout: float = _MAX_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Inspecciona TLS en un proceso terminable para limitar también una resolución DNS bloqueada."""
    normalised_host = _normalise_host(host)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("El puerto debe ser un número entre 1 y 65535.")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= _MAX_TIMEOUT_SECONDS:
        raise ValueError("El tiempo límite debe ser mayor que cero y no superar 3 segundos.")

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--inspect-child",
        normalised_host,
        str(port),
        str(float(timeout)),
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            # Keep the total operation bounded without charging child startup
            # and JSON serialization against the network timeout itself.
            timeout=float(timeout) + _CHILD_PROCESS_STARTUP_GRACE_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        summary = "La resolución DNS o la conexión TLS superó el límite total de tiempo."
        return _result(
            normalised_host, port, "timeout", summary,
            findings=[{"code": "inspection_timeout", "severity": "warning", "title": "Tiempo agotado", "detail": summary}],
        )
    except OSError:
        summary = "No se pudo iniciar el proceso aislado para inspeccionar TLS."
        return _result(
            normalised_host, port, "error", summary,
            findings=[{"code": "inspection_unavailable", "severity": "warning", "title": "Herramienta no disponible", "detail": summary}],
        )

    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if completed.returncode != 0 or not isinstance(payload, dict):
        summary = "La inspección TLS no devolvió un resultado válido."
        return _result(
            normalised_host, port, "error", summary,
            findings=[{"code": "inspection_failed", "severity": "warning", "title": "No se pudo completar la inspección", "detail": summary}],
        )
    if payload.get("host") != normalised_host or payload.get("port") != port:
        summary = "El resultado recibido no coincide con el endpoint consultado."
        return _result(
            normalised_host, port, "error", summary,
            findings=[{"code": "inspection_result_mismatch", "severity": "warning", "title": "Resultado no válido", "detail": summary}],
        )
    return payload


def _child_main() -> None:
    """Punto de entrada privado del proceso hijo; el protocolo de salida es JSON."""
    if len(sys.argv) != 5 or sys.argv[1] != "--inspect-child":
        raise SystemExit(2)
    try:
        report = _inspect_tls_endpoint_direct(
            sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
        )
    except (ValueError, TypeError):
        raise SystemExit(2)
    sys.stdout.write(json.dumps(report, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    _child_main()
