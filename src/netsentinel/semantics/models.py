"""Tipos inmutables del catálogo semántico; no contienen lógica de transporte o persistencia."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ValueKind(str, Enum):
    EMPTY = "empty"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DECIMAL = "decimal"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    TIMESTAMP = "timestamp"
    MEASUREMENT = "measurement"
    AMBIGUOUS_MEASUREMENT = "ambiguous_measurement"
    TEXT = "text"
    STRUCTURED = "structured"
    INVALID = "invalid"


class HeaderStatus(str, Enum):
    CANONICAL = "canonical"
    ALIAS = "alias"
    IGNORED = "ignored"
    BLOCKED = "blocked"
    SUGGESTION = "suggestion"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"
    UNSAFE_NAME = "unsafe_name"
    COLLISION = "collision"


class QuantityStatus(str, Enum):
    EXPLICIT = "explicit"
    NO_UNIT = "no_unit"
    UNKNOWN_UNIT = "unknown_unit"
    AMBIGUOUS_UNIT = "ambiguous_unit"
    INVALID_NUMBER = "invalid_number"


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """Significado estable de un campo interno."""

    name: str
    value_kind: ValueKind
    description: str
    dimension: str | None = None
    canonical_unit: str | None = None
    semantic_scope: str | None = None
    sensitive: bool = False


@dataclass(frozen=True, slots=True)
class SourceProfile:
    """Vocabulario declarado por un formato de origen concreto."""

    name: str
    description: str
    aliases: Mapping[str, str]
    ignored_headers: Mapping[str, str]
    blocked_headers: Mapping[str, str]
    field_scopes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class HeaderSuggestion:
    """Candidato textual; nunca equivale a una asignación automática."""

    field_name: str
    matched_alias: str
    score: float


@dataclass(frozen=True, slots=True)
class HeaderResolution:
    """Resultado explicable para una cabecera de origen."""

    position: int
    source_header: str | None
    normalized_header: str | None
    status: HeaderStatus
    field_name: str | None = None
    matched_alias: str | None = None
    suggestions: tuple[HeaderSuggestion, ...] = ()
    reason: str | None = None

    @property
    def usable(self) -> bool:
        """Solo los matches explícitos, sin colisiones, pueden alimentar un mapeo."""
        return self.status in {HeaderStatus.CANONICAL, HeaderStatus.ALIAS}


@dataclass(frozen=True, slots=True)
class HeaderCollision:
    """Grupo de columnas que se resolverían al mismo campo canónico."""

    field_name: str
    positions: tuple[int, ...]
    source_headers: tuple[str | None, ...]


@dataclass(frozen=True, slots=True)
class HeaderResolutionPlan:
    """Plan de resolución de cabeceras para una única fuente."""

    source_profile: str
    headers: tuple[HeaderResolution, ...]
    collisions: tuple[HeaderCollision, ...]
