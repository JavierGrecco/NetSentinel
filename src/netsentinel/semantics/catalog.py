"""Catálogo versionable de conceptos y perfiles de formatos conocidos."""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .models import FieldDefinition, SourceProfile, ValueKind


def _frozen(values: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(values))


FIELD_DEFINITIONS: Mapping[str, FieldDefinition] = MappingProxyType({
    "observed_at": FieldDefinition(
        "observed_at", ValueKind.TIMESTAMP,
        "Instante al que se refiere la observación; no es el momento de importación.",
        dimension="time",
        semantic_scope="source observation time",
    ),
    "event_type": FieldDefinition("event_type", ValueKind.TEXT, "Clase del evento observado."),
    "domain": FieldDefinition("domain", ValueKind.TEXT, "Nombre DNS asociado al evento."),
    "source_ip": FieldDefinition(
        "source_ip", ValueKind.IP_ADDRESS, "Dirección IP del extremo de origen.",
        semantic_scope="origin endpoint",
    ),
    "source_port": FieldDefinition(
        "source_port", ValueKind.INTEGER, "Puerto de transporte del extremo de origen.",
        dimension="port", canonical_unit="1",
        minimum=0, maximum=65535,
    ),
    "destination_ip": FieldDefinition(
        "destination_ip", ValueKind.IP_ADDRESS, "Dirección IP del extremo de destino.",
        semantic_scope="destination endpoint",
    ),
    "destination_port": FieldDefinition(
        "destination_port", ValueKind.INTEGER, "Puerto de transporte del extremo de destino.",
        dimension="port", canonical_unit="1",
        minimum=0, maximum=65535,
    ),
    "protocol": FieldDefinition("protocol", ValueKind.TEXT, "Protocolo de transporte observado."),
    "bytes_sent": FieldDefinition(
        "bytes_sent", ValueKind.INTEGER,
        "Contador de bytes enviados desde el origen; la capa de medición depende de la fuente.",
        dimension="data_size", canonical_unit="B",
        semantic_scope="preserve source byte layer; do not mix IP and payload bytes"
        minimum=0, maximum=9_223_372_036_854_775_807,
    ),
    "bytes_received": FieldDefinition(
        "bytes_received", ValueKind.INTEGER,
        "Contador de bytes recibidos hacia el origen; la capa de medición depende de la fuente.",
        dimension="data_size", canonical_unit="B",
        semantic_scope="preserve source byte layer; do not mix IP and payload bytes",
        minimum=0, maximum=9_223_372_036_854_775_807,
    ),
    "packets_sent": FieldDefinition(
        "packets_sent", ValueKind.INTEGER, "Paquetes enviados desde el origen.",
        dimension="count", canonical_unit="{packet}"
        minimum=0, maximum=9_223_372_036_854_775_807,
    ),
    "packets_received": FieldDefinition(
        "packets_received", ValueKind.INTEGER, "Paquetes recibidos hacia el origen.",
        dimension="count", canonical_unit="{packet}",
        minimum=0, maximum=9_223_372_036_854_775_807,
    ),
    "network_interface": FieldDefinition("network_interface", ValueKind.TEXT, "Interfaz de red observada."),
    "source_event_id": FieldDefinition("source_event_id", ValueKind.TEXT, "Identificador de origen preservado."),
    "app_name": FieldDefinition("app_name", ValueKind.TEXT, "Nombre de aplicación declarado por la fuente."),
    "blocked": FieldDefinition("blocked", ValueKind.BOOLEAN, "Indicador explícito de bloqueo."),
    "page_url": FieldDefinition(
        "page_url", ValueKind.TEXT, "URL saneada asociada a una visita.",
        sensitive=True,
    ),
    "search_engine": FieldDefinition("search_engine", ValueKind.TEXT, "Motor de búsqueda declarado."),
    "search_terms": FieldDefinition(
        "search_terms", ValueKind.TEXT, "Términos de búsqueda importados explícitamente.",
        sensitive=True,
    ),
    "email_provider": FieldDefinition("email_provider", ValueKind.TEXT, "Proveedor de correo."),
    "email_from": FieldDefinition("email_from", ValueKind.TEXT, "Remitente de un evento de auditoría."),
    "email_to": FieldDefinition("email_to", ValueKind.TEXT, "Destinatarios de un evento de auditoría."),
    "email_subject": FieldDefinition(
        "email_subject", ValueKind.TEXT, "Asunto importado desde metadatos autorizados.",
        sensitive=True,
    ),
})


_CSV_CANONICAL_FIELDS = tuple(FIELD_DEFINITIONS)
_CSV_ALIASES = {
    "date": "observed_at",
    "datetime": "observed_at",
    "timestamp": "observed_at",
    "date_time": "observed_at",
    "date_and_time": "observed_at",
    "received_datetime": "observed_at",
    "received_date_time": "observed_at",
    "sent_datetime": "observed_at",
    "sent_date_time": "observed_at",
    "received_time": "observed_at",
    "sent_time": "observed_at",
    "time": "observed_at",
    "eventtype": "event_type",
    "provider": "email_provider",
    "mail_provider": "email_provider",
    "email_service": "email_provider",
    "service": "email_provider",
    "from": "email_from",
    "from_address": "email_from",
    "from_email": "email_from",
    "sender": "email_from",
    "sender_address": "email_from",
    "senderaddress": "email_from",
    "sender_email": "email_from",
    "sender_email_address": "email_from",
    "to": "email_to",
    "to_address": "email_to",
    "to_email": "email_to",
    "recipient": "email_to",
    "recipient_address": "email_to",
    "recipientaddress": "email_to",
    "recipient_email": "email_to",
    "recipients": "email_to",
    "subject": "email_subject",
    "subject_line": "email_subject",
    "message_subject": "email_subject",
    "subject_or_message_id": "email_subject",
    "src_ip": "source_ip",
    "source_address": "source_ip",
    "src_address": "source_ip",
    "src_port": "source_port",
    "interface": "network_interface",
    "ifname": "network_interface",
    "interface_name": "network_interface",
    "event_id": "source_event_id",
    "event_identifier": "source_event_id",
    "record_id": "source_event_id",
}
_CSV_IGNORED = {
    "id": "Proveedor metadata no incorporado al contrato de Actividad.",
    "message_id": "Identificador de mensaje ajeno al identificador de evento de red.",
    "messageid": "Identificador de mensaje ajeno al identificador de evento de red.",
    "message_trace_id": "Identificador de trazabilidad del proveedor no modelado.",
    "messagetraceid": "Identificador de trazabilidad del proveedor no modelado.",
    "status": "Estado del flujo de correo no equivalente a event_type.",
    "delivery_status": "Estado de entrega no equivalente a disponibilidad de red.",
    "direction": "Dirección del correo no equivalente al origen/destino de una conexión.",
    "size": "Magnitud ambigua: no indica bytes de red ni su capa de medición.",
    "message_size": "Tamaño de mensaje; no equivale a bytes de tráfico de red.",
    "from_ip": "Campo del proveedor no incluido en el contrato actual.",
    "fromip": "Campo del proveedor no incluido en el contrato actual.",
    "to_ip": "Campo del proveedor no incluido en el contrato actual.",
    "toip": "Campo del proveedor no incluido en el contrato actual.",
    "sender_ip": "Campo del proveedor no incluido en el contrato actual.",
    "senderip": "Campo del proveedor no incluido en el contrato actual.",
    "recipient_ip": "Campo del proveedor no incluido en el contrato actual.",
    "recipientip": "Campo del proveedor no incluido en el contrato actual.",
    "delivery_step": "Paso interno del proveedor no incluido en el contrato.",
    "event": "Nombre ambiguo; no se interpreta como event_type sin contexto.",
    "route": "Ruta del proveedor no equivalente a un extremo de red.",
    "internet_message_id": "Identificador de mensaje, no de evento de red.",
    "internetmessageid": "Identificador de mensaje, no de evento de red.",
    "network_message_id": "Identificador de mensaje, no de evento de red.",
    "networkmessageid": "Identificador de mensaje, no de evento de red.",
    "trace_id": "Identificador de trazabilidad del proveedor no modelado.",
    "traceid": "Identificador de trazabilidad del proveedor no modelado.",
}
_CSV_BLOCKED = {
    "url": "La columna podría contener URLs completas o rutas sensibles.",
    "full_url": "No se importan URLs completas.",
    "path": "No se importan rutas completas.",
    "query_string": "No se importan parámetros de consulta que podrían contener tokens.",
    "username": "No se importan nombres de usuario.",
    "user": "No se importan identificadores de usuario.",
    "password": "No se importan contraseñas.",
    "passwd": "No se importan contraseñas.",
    "token": "No se importan tokens.",
    "cookie": "No se importan cookies.",
    "authorization": "No se importan cabeceras de autorización.",
    "payload": "No se importan cargas útiles.",
    "body": "No se importan cuerpos de mensajes.",
    "message": "No se importa contenido de mensajes.",
    "email_body": "No se importan cuerpos de correo.",
    "message_body": "No se importan cuerpos de mensajes.",
    "body_text": "No se importa texto de cuerpos.",
    "body_html": "No se importa HTML de cuerpos.",
    "content": "No se importa contenido completo.",
    "email_message": "No se importan mensajes completos.",
    "request_body": "No se importan cuerpos de solicitudes.",
    "response_body": "No se importan cuerpos de respuestas.",
    "attachment": "No se importan adjuntos.",
    "attachments": "No se importan adjuntos.",
    "attachment_content": "No se importa contenido de adjuntos.",
    "message_content": "No se importa contenido de mensajes.",
}
_ZEEK_ALIASES = {
    "ts": "observed_at",
    "uid": "source_event_id",
    "id.orig_h": "source_ip",
    "id.orig_p": "source_port",
    "id.resp_h": "destination_ip",
    "id.resp_p": "destination_port",
    "proto": "protocol",
    "orig_ip_bytes": "bytes_sent",
    "resp_ip_bytes": "bytes_received",
    "orig_pkts": "packets_sent",
    "resp_pkts": "packets_received",
}
_ZEEK_BLOCKED = {
    "orig_bytes": "Zeek mide bytes de carga útil; no son equivalentes a orig_ip_bytes.",
    "resp_bytes": "Zeek mide bytes de carga útil; no son equivalentes a resp_ip_bytes.",
}

_SOURCE_PROFILES: Mapping[str, SourceProfile] = {
    "activity_csv": SourceProfile(
        name="activity_csv",
        description="CSV de metadatos admitidos por el contrato de Actividad.",
        aliases=_frozen({**{name: name for name in _CSV_CANONICAL_FIELDS}, **_CSV_ALIASES}),
        ignored_headers=_frozen(_CSV_IGNORED),
        blocked_headers=_frozen(_CSV_BLOCKED),
        field_scopes=_frozen({}),
        blocked_tokens=("body", "content", "payload", "attachment", "attachments"),
        block_message_without_id_or_subject=True,
    ),
    "zeek_conn_log": SourceProfile(
        name="zeek_conn_log",
        description="Zeek conn.log TSV o JSON Lines con campos conn documentados.",
        aliases=_frozen(_ZEEK_ALIASES),
        ignored_headers=_frozen({}),
        blocked_headers=_frozen(_ZEEK_BLOCKED),
        field_scopes=_frozen({
            "bytes_sent": "IP-layer octets from orig_ip_bytes",
            "bytes_received": "IP-layer octets from resp_ip_bytes",
            "observed_at": "Unix epoch seconds from Zeek ts",
        }),
    ),
}
SOURCE_PROFILES: Mapping[str, SourceProfile] = MappingProxyType(_SOURCE_PROFILES)


def get_field_definition(name: str) -> FieldDefinition | None:
    """Devuelve la definición canónica o None si el campo no forma parte del catálogo."""
    return FIELD_DEFINITIONS.get(name)


def get_source_profile(name: str) -> SourceProfile:
    """Devuelve un perfil de origen; los perfiles desconocidos se rechazan explícitamente."""
    try:
        return SOURCE_PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"Perfil de origen semántico desconocido: {name}.") from exc
