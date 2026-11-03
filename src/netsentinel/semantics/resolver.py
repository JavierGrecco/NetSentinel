"""Resolución determinista de nombres de campos, con typos solo como sugerencias."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Iterable

from .catalog import get_source_profile
from .models import (
    HeaderCollision,
    HeaderResolution,
    HeaderResolutionPlan,
    HeaderStatus,
    HeaderSuggestion,
    SourceProfile,
)


MAX_HEADER_LENGTH = 128
MIN_SUGGESTION_LENGTH = 4
SUGGESTION_CUTOFF = 0.78
AMBIGUITY_MARGIN = 0.06
MAX_SUGGESTIONS = 3


def normalize_header(value: str | None) -> tuple[str | None, str | None]:
    """Normaliza una cabecera sin borrar estructura de rutas ni aceptar confusables.

    Devuelve (clave, motivo_inseguro). Los acentos latinos se pliegan para aceptar
    variantes de escritura; letras de otros alfabetos y caracteres de control se
    rechazan en vez de convertirlos silenciosamente en alias ASCII.
    """
    if value is None or not isinstance(value, str):
        return None, "La cabecera no es texto."
    raw = value.lstrip("\ufeff").strip()
    if not raw:
        return None, "La cabecera está vacía."
    if len(raw) > MAX_HEADER_LENGTH:
        return None, f"La cabecera supera el máximo de {MAX_HEADER_LENGTH} caracteres."
    if any(unicodedata.category(character).startswith("C") for character in raw):
        return None, "La cabecera contiene caracteres de control o formato no admitidos."

    normalized = unicodedata.normalize("NFKC", raw)
    normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", normalized)
    normalized = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", normalized)
    decomposed = unicodedata.normalize("NFKD", normalized)
    without_marks = "".join(
        character for character in decomposed
        if unicodedata.category(character) != "Mn"
    ).casefold()

    if any(character.isalpha() and not character.isascii() for character in without_marks):
        return None, "La cabecera mezcla caracteres no latinos o visualmente confundibles."

    key = re.sub(r"[\s-]+", "_", without_marks)
    key = re.sub(r"[^a-z0-9_.]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    if not key or key in {".", ".."}:
        return None, "La cabecera no contiene un nombre reconocible."
    return key, None


@lru_cache(maxsize=16)
def _alias_index(profile_name: str) -> tuple[tuple[str, str], ...]:
    profile = get_source_profile(profile_name)
    entries: dict[str, str] = {}
    for alias, field_name in profile.aliases.items():
        key, reason = normalize_header(alias)
        if reason or key is None:
            raise ValueError(f"Alias inseguro en el catálogo {profile_name}: {alias!r}.")
        previous = entries.get(key)
        if previous is not None and previous != field_name:
            raise ValueError(
                f"El catálogo {profile_name} repite el alias {alias!r} para "
                f"{previous!r} y {field_name!r}."
            )
        entries[key] = field_name
    return tuple(sorted(entries.items()))


def _suggest(
    normalized: str,
    aliases: tuple[tuple[str, str], ...],
) -> tuple[HeaderSuggestion, ...]:
    """Busca candidatos solo en el perfil activo; nunca confirma un typo."""
    if len(normalized) < MIN_SUGGESTION_LENGTH:
        return ()

    best_by_field: dict[str, HeaderSuggestion] = {}
    for alias, field_name in aliases:
        if abs(len(alias) - len(normalized)) > max(3, len(normalized) // 3):
            continue
        score = SequenceMatcher(None, normalized, alias, autojunk=False).ratio()
        if score < SUGGESTION_CUTOFF:
            continue
        candidate = HeaderSuggestion(field_name, alias, score)
        previous = best_by_field.get(field_name)
        if previous is None or (candidate.score, candidate.matched_alias) > (
            previous.score, previous.matched_alias
        ):
            best_by_field[field_name] = candidate

    ranked = sorted(
        best_by_field.values(),
        key=lambda item: (-item.score, item.field_name, item.matched_alias),
    )
    return tuple(ranked[:MAX_SUGGESTIONS])


def resolve_headers(
    headers: Iterable[str | None],
    source_profile: str | SourceProfile,
    *,
    suggest_typos: bool = True,
) -> HeaderResolutionPlan:
    """Resuelve cabeceras por contexto y señala conflictos sin escoger una columna.

    Solo los matches canónicos y los alias exactos son utilizables. Las sugerencias
    aproximadas nunca rellenan field_name y, por lo tanto, no pueden importarse por
    accidente. Dos columnas asignadas al mismo campo invalidan ambas asignaciones.
    """
    profile = (
        get_source_profile(source_profile)
        if isinstance(source_profile, str)
        else source_profile
    )
    aliases = _alias_index(profile.name) if profile.name in {
        "activity_csv", "zeek_conn_log"
    } else _compile_custom_aliases(profile)
    alias_map = dict(aliases)
    resolutions: list[HeaderResolution] = []

    for position, raw_header in enumerate(headers):
        key, unsafe_reason = normalize_header(raw_header)
        if unsafe_reason:
            resolutions.append(HeaderResolution(
                position, raw_header, None, HeaderStatus.UNSAFE_NAME,
                reason=unsafe_reason,
            ))
            continue

        assert key is not None
        if key in profile.blocked_headers:
            resolutions.append(HeaderResolution(
                position, raw_header, key, HeaderStatus.BLOCKED,
                reason=profile.blocked_headers[key],
            ))
            continue
        if key in profile.ignored_headers:
            resolutions.append(HeaderResolution(
                position, raw_header, key, HeaderStatus.IGNORED,
                reason=profile.ignored_headers[key],
            ))
            continue
        field_name = alias_map.get(key)
        if field_name is not None:
            status = (
                HeaderStatus.CANONICAL
                if key == field_name
                else HeaderStatus.ALIAS
            )
            resolutions.append(HeaderResolution(
                position, raw_header, key, status,
                field_name=field_name,
                matched_alias=key,
            ))
            continue

        suggestions = _suggest(key, aliases) if suggest_typos else ()
        if not suggestions:
            resolutions.append(HeaderResolution(
                position, raw_header, key, HeaderStatus.UNKNOWN,
                reason="No hay un alias exacto ni una sugerencia segura en este perfil.",
            ))
            continue
        if len(suggestions) > 1 and suggestions[0].score - suggestions[1].score < AMBIGUITY_MARGIN:
            resolutions.append(HeaderResolution(
                position, raw_header, key, HeaderStatus.AMBIGUOUS,
                suggestions=suggestions,
                reason="Hay más de un campo plausible; no se asigna automáticamente.",
            ))
            continue
        resolutions.append(HeaderResolution(
            position, raw_header, key, HeaderStatus.SUGGESTION,
            suggestions=(suggestions[0],),
            reason="Coincidencia aproximada; requiere confirmación explícita.",
        ))

    grouped: dict[str, list[int]] = {}
    for index, resolution in enumerate(resolutions):
        if resolution.usable and resolution.field_name:
            grouped.setdefault(resolution.field_name, []).append(index)

    collisions: list[HeaderCollision] = []
    for field_name, positions in sorted(grouped.items()):
        if len(positions) < 2:
            continue
        collisions.append(HeaderCollision(
            field_name=field_name,
            positions=tuple(resolutions[index].position for index in positions),
            source_headers=tuple(resolutions[index].source_header for index in positions),
        ))
        for index in positions:
            current = resolutions[index]
            resolutions[index] = HeaderResolution(
                position=current.position,
                source_header=current.source_header,
                normalized_header=current.normalized_header,
                status=HeaderStatus.COLLISION,
                field_name=field_name,
                matched_alias=current.matched_alias,
                reason=(
                    f"Más de una columna representa {field_name}; se requiere "
                    "resolver el conflicto antes de importar."
                ),
            )

    return HeaderResolutionPlan(
        source_profile=profile.name,
        headers=tuple(resolutions),
        collisions=tuple(collisions),
    )


def _compile_custom_aliases(profile: SourceProfile) -> tuple[tuple[str, str], ...]:
    """Permite perfiles pequeños de prueba sin relajar la validación de alias."""
    entries: dict[str, str] = {}
    for alias, field_name in profile.aliases.items():
        key, reason = normalize_header(alias)
        if reason or key is None:
            raise ValueError(f"Alias inseguro en el perfil {profile.name}: {alias!r}.")
        previous = entries.get(key)
        if previous is not None and previous != field_name:
            raise ValueError(f"Alias ambiguo en el perfil {profile.name}: {alias!r}.")
        entries[key] = field_name
    return tuple(sorted(entries.items()))
