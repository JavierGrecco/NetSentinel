"""Descubrimiento pasivo a partir de tablas de vecinos del sistema operativo.

No hace barridos activos. Intenta leer las fuentes disponibles de forma independiente,
combina sus resultados y conserva la procedencia para auditoría y diagnóstico.
"""

from __future__ import annotations

import ipaddress
import platform
import re
import subprocess
from dataclasses import dataclass
from typing import Iterable, Protocol

from .network_models import Neighbor
from .vendor import is_unicast

_MAC = r"(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}"
_MAC_RE = re.compile(rf"^{_MAC}$")
# macOS peer-to-peer link interfaces are not ordinary home/office LAN inventory.
_NON_LAN_INTERFACE_PREFIXES = ("awdl", "llw")


def normalize_mac(value: str) -> str | None:
    """Normaliza una MAC a formato XX:XX:XX:XX:XX:XX y rechaza valores inválidos."""
    cleaned = value.strip().replace("-", ":").lower()
    if not _MAC_RE.fullmatch(cleaned):
        return None
    normalized = cleaned.upper()
    if not is_unicast(normalized) or normalized == "00:00:00:00:00:00":
        return None
    return normalized


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.split("%", 1)[0])
        return True
    except ValueError:
        return False


def parse_neighbor_output(
    output: str,
    system: str | None = None,
    source: str = "system-neighbor-table",
) -> list[Neighbor]:
    """Parsea salidas habituales de `ip neigh`, `arp -a` y `ndp -an`."""
    _ = system or platform.system()
    found: dict[tuple[str, str], Neighbor] = {}

    patterns = (
        # Linux/iproute2: IP dev IFACE lladdr MAC STATE
        (re.compile(rf"(?P<ip>[0-9a-fA-F:.]+(?:%[A-Za-z0-9_.-]+)?)\s+dev\s+(?P<iface>\S+).*?\blladdr\s+(?P<mac>{_MAC})", re.I), "ip-neigh"),
        # macOS/BSD arp: ? (IP) at MAC on IFACE
        (re.compile(rf"\((?P<ip>[0-9a-fA-F:.]+(?:%[A-Za-z0-9_.-]+)?)\)\s+at\s+(?P<mac>{_MAC})(?:\s+on\s+(?P<iface>\S+))?", re.I), "arp"),
        # Windows arp -a (IP MAC dynamic/static)
        (re.compile(rf"(?m)^\s*(?P<ip>[0-9a-fA-F:.]+(?:%[A-Za-z0-9_.-]+)?)\s+(?P<mac>{_MAC})(?:\s|$)", re.I), "arp"),
        # BSD/macOS ndp -an: IPv6%IFACE MAC IFACE ...
        (re.compile(rf"(?m)^\s*(?P<ip>[0-9a-fA-F:.]+(?:%[A-Za-z0-9_.-]+)?)\s+(?P<mac>{_MAC})\s+(?P<iface>\S+)\s+", re.I), "ndp"),
    )
    for pattern, detected_source in patterns:
        for match in pattern.finditer(output):
            mac = normalize_mac(match.group("mac"))
            ip = match.group("ip").split("%", 1)[0]
            if not mac or not _valid_ip(ip):
                continue
            interface = match.groupdict().get("iface")
            if interface and interface.lower().startswith(_NON_LAN_INTERFACE_PREFIXES):
                continue
            item_source = detected_source if source == "system-neighbor-table" else source
            neighbor = Neighbor(ip, mac, interface, item_source)
            key = (ip, mac)
            previous = found.get(key)
            if previous is None or (not previous.interface and interface):
                found[key] = neighbor
    return sorted(found.values(), key=lambda item: (ipaddress.ip_address(item.ip_address).version, int(ipaddress.ip_address(item.ip_address)), item.mac_address))


def _commands_for_system(system: str) -> Iterable[tuple[list[str], str]]:
    if system == "Windows":
        return ((["arp", "-a"], "arp"),)
    if system == "Darwin":
        return ((["arp", "-an"], "arp"), (["ndp", "-an"], "ndp"))
    if system in {"FreeBSD", "OpenBSD", "NetBSD"}:
        return ((["arp", "-an"], "arp"), (["ndp", "-an"], "ndp"))
    # `ip neigh` suele incluir IPv4 e IPv6; la consulta explícita permite a sistemas
    # que filtran familias devolver IPv6 de forma separada. Los fallbacks son opcionales.
    return (
        (["ip", "neigh", "show"], "ip-neigh"),
        (["ip", "-6", "neigh", "show"], "ip-neigh-ipv6"),
        (["arp", "-an"], "arp"),
    )


class DiscoveryProvider(Protocol):
    """Contrato mínimo para una fuente de descubrimiento intercambiable."""

    name: str

    def discover(self) -> tuple[list[Neighbor], list[str]]:
        """Devuelve vecinos observados y errores propios de la fuente."""
        ...


@dataclass(frozen=True, slots=True)
class CommandDiscoveryProvider:
    """Proveedor de solo lectura para un comando del sistema operativo."""

    command: tuple[str, ...]
    name: str
    timeout_seconds: float = 5.0

    def discover(self) -> tuple[list[Neighbor], list[str]]:
        try:
            result = subprocess.run(
                list(self.command),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            return [], [f"No está disponible la fuente opcional {self.name}: {self.command[0]}"]
        except subprocess.TimeoutExpired:
            return [], [f"La fuente {self.name} superó el límite de {self.timeout_seconds:g} segundos."]
        except OSError as exc:
            return [], [f"No se pudo consultar la fuente {self.name}: {exc}"]

        errors: list[str] = []
        if result.returncode != 0 and result.stderr.strip():
            errors.append(f"{self.name}: {result.stderr.strip()[:220]}")
        return parse_neighbor_output(result.stdout, platform.system(), self.name), errors


def default_providers(system: str | None = None) -> list[DiscoveryProvider]:
    """Construye los proveedores que tienen sentido para el sistema actual."""
    actual_system = system or platform.system()
    return [
        CommandDiscoveryProvider(tuple(command), name)
        for command, name in _commands_for_system(actual_system)
    ]


def discover_from_providers(
    providers: Iterable[DiscoveryProvider],
) -> tuple[list[Neighbor], list[str]]:
    """Combina fuentes disponibles; el fallo de una no impide consultar las demás."""
    errors: list[str] = []
    combined: dict[tuple[str, str], Neighbor] = {}
    success_count = 0
    for provider in providers:
        try:
            neighbors, provider_errors = provider.discover()
        except Exception as exc:  # La interfaz de plugins no debe tumbar el resto del inventario.
            errors.append(f"Falló el proveedor {getattr(provider, 'name', type(provider).__name__)}: {exc}")
            continue
        errors.extend(provider_errors)
        if not provider_errors:
            success_count += 1
        for item in neighbors:
            key = (item.ip_address, item.mac_address)
            existing = combined.get(key)
            if existing is None or (not existing.interface and item.interface):
                combined[key] = item

    neighbors = sorted(
        combined.values(),
        key=lambda item: (ipaddress.ip_address(item.ip_address).version, int(ipaddress.ip_address(item.ip_address)), item.mac_address),
    )
    if neighbors:
        # Herramientas fallback ausentes no invalidan las lecturas correctas.
        relevant_errors = [message for message in errors if not message.startswith("No está disponible la fuente opcional")]
        return neighbors, relevant_errors
    if success_count:
        relevant_errors = [message for message in errors if not message.startswith("No está disponible la fuente opcional")]
        relevant_errors.append(
            "Las fuentes disponibles no devolvieron entradas reconocibles. Esto no significa "
            "que la red esté vacía: NetSentinel no realiza un barrido activo."
        )
        return [], relevant_errors
    if errors:
        return [], errors
    return [], ["No fue posible consultar las tablas de vecinos del sistema."]


def read_neighbor_table() -> tuple[list[Neighbor], list[str]]:
    """Función compatible con la API v0.1, ahora respaldada por proveedores."""
    return discover_from_providers(default_providers())
