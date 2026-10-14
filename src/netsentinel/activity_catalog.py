"""Catálogo estable de fuentes, eventos y protocolos de actividad.

Este módulo no contiene lógica de captura ni depende de la base de datos.
"""
SESSION_SOURCES = {"router_dns", "router_flow", "device_agent"}
EVENT_SOURCES = SESSION_SOURCES
EVENT_TYPES = {
    "dns_query", "connection", "tls_sni", "app_usage", "blocked",
    "page_visit", "search_query", "email_metadata",
}
PROTOCOLS = {"tcp", "udp", "quic", "icmp", "other"}
