"""Aplicación FastAPI de NetSentinel."""

from __future__ import annotations

from contextlib import asynccontextmanager
import ipaddress
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit
from typing import AsyncIterator
import os

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from . import database
from .diagnostics import run_diagnostics
from .local_discovery import discover_local_network
from .monitoring import MonitorSupervisor, check_once, validate_spec
from .dns_tools import DNSLookupError, cached_reverse_lookup_ip, lookup_hostname
from .dns_config import get_dns_configuration
from . import activity_tracking


_supervisor = MonitorSupervisor()
_scan_lock = Lock()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database.initialize()
    scheduler_disabled = os.environ.get("NETSENTINEL_DISABLE_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}
    if not scheduler_disabled:
        _supervisor.start()
    try:
        yield
    finally:
        _supervisor.stop()


_RFC1918_HOST_NETWORKS = tuple(
    ipaddress.IPv4Network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_IPV6_UNIQUE_LOCAL = ipaddress.IPv6Network("fc00::/7")
_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _host_is_allowed(host: str | None) -> bool:
    """Allow loopback/private LAN IPs and explicit extra hostnames only."""
    if not host:
        return False
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        extras = {
            item.strip().rstrip(".").lower()
            for item in os.environ.get("NETSENTINEL_ALLOWED_HOSTS", "").split(",")
            if item.strip()
        }
        return normalized in extras
    if address.is_loopback:
        return True
    if isinstance(address, ipaddress.IPv4Address):
        return any(address in network for network in _RFC1918_HOST_NETWORKS)
    return address in _IPV6_UNIQUE_LOCAL


def _same_origin(origin: str, request: Request) -> bool:
    """Compare scheme, normalized host and effective port without trusting Origin."""
    try:
        parsed = urlsplit(origin)
        origin_host_value = parsed.hostname
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or not origin_host_value:
        return False
    request_host = (request.url.hostname or "").rstrip(".").lower()
    origin_host = origin_host_value.rstrip(".").lower()
    request_scheme = request.url.scheme.lower()
    origin_scheme = parsed.scheme.lower()
    if request_host != origin_host or request_scheme != origin_scheme:
        return False
    try:
        request_port = request.url.port or (443 if request_scheme == "https" else 80)
        origin_port = parsed.port or (443 if origin_scheme == "https" else 80)
    except ValueError:
        return False
    return request_port == origin_port


app = FastAPI(
    title="NetSentinel",
    description="Inventario local, descubrimiento bajo demanda, lista de confianza, eventos y diagnóstico de red.",
    version=__version__,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
_STATIC_DIR = Path(__file__).parent / "static"
_STATIC = _STATIC_DIR / "index.html"
_MONITORS_STATIC = _STATIC_DIR / "monitors.html"
_ACTIVITY_STATIC = _STATIC_DIR / "activity.html"


@app.middleware("http")
async def protect_local_app(request: Request, call_next):
    """Mitigate DNS-rebinding and browser CSRF attempts against the local control panel."""
    if not _host_is_allowed(request.url.hostname):
        return JSONResponse(status_code=400, content={"detail": "Host no permitido para NetSentinel."})

    if request.method.upper() in _MUTATING_METHODS:
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if fetch_site == "cross-site":
            return JSONResponse(status_code=403, content={"detail": "Solicitud entre sitios bloqueada."})
        origin = request.headers.get("origin")
        if origin and not _same_origin(origin, request):
            return JSONResponse(status_code=403, content={"detail": "Origen no permitido para esta operación."})

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    return response


class DeviceUpdate(BaseModel):
    trusted: bool | None = None
    display_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2000)


class EventUpdate(BaseModel):
    acknowledged: bool = True


class MonitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(min_length=1, max_length=16)
    target: str = Field(min_length=1, max_length=500)
    interval_seconds: int = Field(default=60, ge=15, le=86400)
    timeout_seconds: int = Field(default=3, ge=1, le=10)


class MonitorUpdate(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    interval_seconds: int | None = Field(default=None, ge=15, le=86400)
    timeout_seconds: int | None = Field(default=None, ge=1, le=10)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_STATIC)


@app.get("/monitors", include_in_schema=False)
def monitors_page() -> FileResponse:
    return FileResponse(_MONITORS_STATIC)


@app.get("/activity", include_in_schema=False)
def activity_page() -> FileResponse:
    return FileResponse(_ACTIVITY_STATIC)


@app.get("/tools", include_in_schema=False)
def tools_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "tools.html")


@app.get("/api/tools/dns/configuration")
def dns_configuration() -> dict:
    """Lee la configuración DNS local sin modificarla ni consultar dominios externos."""
    return get_dns_configuration()


@app.get("/api/tools/dns/lookup")
def dns_lookup(hostname: str = Query(min_length=1, max_length=253)) -> dict:
    """Resuelve registros A/AAAA mediante el resolvedor del sistema, a pedido del usuario."""
    try:
        return lookup_hostname(hostname)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail="No se pudo resolver el nombre con el DNS configurado en el sistema.") from exc


@app.get("/api/tools/dns/reverse")
def dns_reverse_lookup(address: str = Query(min_length=1, max_length=64)) -> dict:
    """Consulta PTR para una IP ingresada explícitamente por el usuario."""
    try:
        return cached_reverse_lookup_ip(address)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail="No se pudo obtener un registro PTR con el DNS configurado en el sistema.") from exc


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "name": "NetSentinel", "version": __version__}


@app.get("/api/summary")
def summary() -> dict:
    return database.get_summary()


@app.get("/api/devices")
def devices(q: str = Query(default="", max_length=160)) -> list[dict]:
    return database.list_devices(query=q)


@app.get("/api/events")
def events(limit: int = Query(default=50, ge=1, le=200)) -> list[dict]:
    return database.get_events(limit=limit)


@app.get("/api/scans")
def scans(limit: int = Query(default=30, ge=1, le=100)) -> list[dict]:
    return database.get_scans(limit=limit)


@app.get("/api/devices/{device_id}/history")
def device_history(device_id: int, limit: int = Query(default=100, ge=1, le=500)) -> dict:
    """Consulta el historial de observaciones del inventario para un dispositivo."""
    result = database.get_device_history(device_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return result


@app.get("/api/devices/{device_id}/addresses")
def device_addresses(device_id: int) -> list[dict]:
    addresses = database.get_device_addresses(device_id)
    if addresses is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return addresses


@app.post("/api/scan")
def scan() -> dict:
    """Ejecuta un único descubrimiento local a la vez para evitar tráfico duplicado."""
    if not _scan_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Ya hay un descubrimiento de red en curso. Esperá a que termine antes de iniciar otro.",
        )
    try:
        neighbors, errors, discovery = discover_local_network()
        result = database.record_scan(neighbors, errors, discovery=discovery)
        result["discovery"] = discovery
        result["message"] = (
            "Se completó el descubrimiento automático de las subredes locales indicadas."
            if discovery["networks"]
            else "No se pudo identificar una subred privada adecuada para buscar dispositivos."
        )
        return result
    finally:
        _scan_lock.release()


@app.get("/api/devices/{device_id}/dns-reverse")
def device_dns_reverse_lookup(device_id: int) -> dict:
    """Consulta PTR de la dirección observada más recientemente, solo bajo demanda."""
    addresses = database.get_device_addresses(device_id)
    if addresses is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    if not addresses:
        raise HTTPException(status_code=404, detail="El dispositivo no tiene direcciones observadas para consultar.")
    address = addresses[0]["ip_address"]
    try:
        result = cached_reverse_lookup_ip(address)
        result["device_id"] = device_id
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DNSLookupError as exc:
        status_code = 404 if exc.kind == "not_found" else 503 if exc.kind == "temporary" else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail="No se pudo obtener un registro PTR para la dirección observada.") from exc


@app.patch("/api/devices/{device_id}")
def edit_device(device_id: int, body: DeviceUpdate) -> dict:
    try:
        result = database.update_device(
            device_id,
            trusted=body.trusted,
            display_name=body.display_name,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el dispositivo.")
    return result


@app.patch("/api/events/{event_id}")
def edit_event(event_id: int, body: EventUpdate) -> dict[str, bool]:
    if body.acknowledged:
        updated = database.acknowledge_event(event_id)
    else:
        # No se ofrece reabrir eventos en esta primera versión.
        updated = False
    if not updated:
        raise HTTPException(status_code=404, detail="No se encontró el evento o no se admite el cambio solicitado.")
    return {"ok": True}


@app.get("/api/monitors")
def monitors() -> list[dict]:
    return database.list_monitors()


@app.get("/api/monitoring/summary")
def monitoring_summary(hours: int = Query(default=24, ge=1, le=168)) -> dict:
    """Resume los resultados medidos en las últimas horas (máximo siete días)."""
    return database.get_monitor_analytics(window_hours=hours)


@app.get("/api/export/monitoring.csv")
def export_monitoring_csv(hours: int = Query(default=24, ge=1, le=168)) -> Response:
    return Response(
        content=database.export_monitoring_csv(window_hours=hours),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="netsentinel-monitoring-report.csv"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/export/incidents.csv")
def export_incidents_csv(status: str | None = Query(default=None)) -> Response:
    if status not in {None, "open", "resolved"}:
        raise HTTPException(status_code=422, detail="El estado debe ser open o resolved.")
    return Response(
        content=database.export_incidents_csv(status=status),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-incidents.csv"', "Cache-Control": "no-store"},
    )


@app.get("/api/monitors/{monitor_id}/latency")
def monitor_latency_trend(monitor_id: int, hours: int = Query(default=24, ge=1, le=168)) -> dict:
    trend = database.get_monitor_latency_trend(monitor_id, window_hours=hours)
    if trend is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return trend


@app.get("/api/export/monitor-latency.csv")
def export_monitor_latency_csv(monitor_id: int = Query(ge=1),
                               hours: int = Query(default=24, ge=1, le=168)) -> Response:
    content = database.export_monitor_latency_csv(monitor_id, window_hours=hours)
    if content is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-latency-trend.csv"', "Cache-Control": "no-store"},
    )


@app.post("/api/monitors", status_code=201)
def add_monitor(body: MonitorCreate) -> dict:
    try:
        kind, target, interval, timeout = validate_spec(body.kind, body.target, body.interval_seconds, body.timeout_seconds)
        return database.create_monitor(body.name, kind, target, interval, timeout)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.patch("/api/monitors/{monitor_id}")
def edit_monitor(monitor_id: int, body: MonitorUpdate) -> dict:
    try:
        result = database.update_monitor(monitor_id, **body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return result


@app.delete("/api/monitors/{monitor_id}")
def remove_monitor(monitor_id: int) -> dict[str, bool]:
    if not database.delete_monitor(monitor_id):
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return {"ok": True}


@app.post("/api/monitors/{monitor_id}/check")
def run_monitor_check(monitor_id: int) -> dict:
    monitor = next((item for item in database.list_monitors() if item["id"] == monitor_id), None)
    if monitor is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    try:
        return check_once(monitor)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/api/monitors/{monitor_id}/checks")
def monitor_checks(monitor_id: int, limit: int = Query(default=30, ge=1, le=200)) -> list[dict]:
    checks = database.get_monitor_checks(monitor_id, limit=limit)
    if checks is None:
        raise HTTPException(status_code=404, detail="No se encontró el monitor.")
    return checks


@app.get("/api/incidents")
def incidents(limit: int = Query(default=50, ge=1, le=200), status: str | None = Query(default=None)) -> list[dict]:
    if status not in {None, "open", "resolved"}:
        raise HTTPException(status_code=422, detail="El estado debe ser open o resolved.")
    return database.get_incidents(limit=limit, status=status)


@app.get("/api/notifications")
def notifications(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    return {
        "webhook_configured": bool(os.environ.get("NETSENTINEL_WEBHOOK_URL", "").strip()),
        "history": database.get_notification_log(limit=limit),
    }


@app.post("/api/diagnostics")
def diagnostics() -> dict:
    return run_diagnostics()


@app.get("/api/export/devices.csv")
def export_devices_csv() -> Response:
    return Response(
        content=database.export_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-devices.csv"', "Cache-Control": "no-store"},
    )


@app.get("/api/export/backup.sqlite3")
def export_sqlite_backup() -> Response:
    return Response(
        content=database.export_sqlite_backup(),
        media_type="application/vnd.sqlite3",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-backup.sqlite3"', "Cache-Control": "no-store"},
    )


@app.get("/api/export/data.json")
def export_data_json() -> Response:
    return Response(
        content=database.export_json(),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="netsentinel-export.json"', "Cache-Control": "no-store"},
    )


# Sirve CSS y otros recursos desde el paquete local.
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
