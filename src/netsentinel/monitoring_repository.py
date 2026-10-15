"""Fachada de compatibilidad para la persistencia de monitorización.

Las consultas y escrituras se delegan en repositorios especializados. Las
transiciones de check/incidente/evento viven juntas para conservar su atomicidad.
"""
from __future__ import annotations

from .monitoring_analytics_repository import (
    get_incidents,
    get_monitor_analytics,
    get_monitor_checks,
    get_monitor_latency_trend,
)
from .monitoring_config_repository import (
    create_monitor,
    delete_monitor,
    list_monitors,
    update_monitor,
)
from .monitoring_notifications_repository import (
    get_notification_log,
    record_notification,
)
from .monitoring_state_repository import (
    cleanup_monitor_history,
    record_monitor_check,
)

__all__ = (
    "cleanup_monitor_history",
    "create_monitor",
    "delete_monitor",
    "get_incidents",
    "get_monitor_analytics",
    "get_monitor_checks",
    "get_monitor_latency_trend",
    "get_notification_log",
    "list_monitors",
    "record_monitor_check",
    "record_notification",
    "update_monitor",
)
