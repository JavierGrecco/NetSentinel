"""Inspección de formas de valores y conversiones con unidades explícitas."""

from __future__ import annotations

import ipaddress
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

from .catalog import get_field_definition
from .models import FieldValueStatus, QuantityStatus, ValueKind


MAX_MEASUREMENT_LENGTH = 128
MAX_INSPECTED_VALUE_LENGTH = 4096
MAX_NUMERIC_DIGITS = 64
MAX_NUMERIC_EXPONENT = 128


_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_MEASUREMENT = re.compile(
    r"^(?P<number>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(?P<unit>.*?)$"
)
_MAC = re.compile(
    r"^(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$"
    r"|^(?:[0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$"
)


@dataclass(frozen=True, slots=True)
class UnitDefinition:
    aliases: tuple[str, ...]
    dimension: str
    canonical_unit: str
    factor: Decimal


@dataclass(frozen=True, slots=True)
class QuantityInspection:
    status: QuantityStatus
    numeric_value: Decimal | None
    source_unit: str | None = None
    dimension: str | None = None
    canonical_unit: str | None = None
    normalized_value: Decimal | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ValueInspection:
    kind: ValueKind
    normalized_preview: str | None = None
    timezone_aware: bool | None = None
    quantity: QuantityInspection | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class FieldValueCheck:
    """Contrasta la forma observada con el tipo/rango del campo ya identificado."""

    field_name: str
    status: FieldValueStatus
    expected_kind: ValueKind | None
    inspection: ValueInspection
    reason: str | None = None


_UNIT_DEFINITIONS = (
    UnitDefinition(("B", "byte", "bytes", "octet", "octets"), "data_size", "B", Decimal("1")),
    UnitDefinition(("kB",), "data_size", "B", Decimal("1000")),
    UnitDefinition(("MB",), "data_size", "B", Decimal("1000000")),
    UnitDefinition(("GB",), "data_size", "B", Decimal("1000000000")),
    UnitDefinition(("KiB",), "data_size", "B", Decimal("1024")),
    UnitDefinition(("MiB",), "data_size", "B", Decimal("1048576")),
    UnitDefinition(("GiB",), "data_size", "B", Decimal("1073741824")),
    UnitDefinition(("s", "sec", "second", "seconds"), "time", "s", Decimal("1")),
    UnitDefinition(("ms", "millisecond", "milliseconds"), "time", "s", Decimal("0.001")),
    UnitDefinition(("us", "µs", "μs", "microsecond", "microseconds"), "time", "s", Decimal("0.000001")),
    UnitDefinition(("ns", "nanosecond", "nanoseconds"), "time", "s", Decimal("0.000000001")),
    UnitDefinition(("min", "minute", "minutes"), "time", "s", Decimal("60")),
    UnitDefinition(("h", "hr", "hour", "hours"), "time", "s", Decimal("3600")),
    UnitDefinition(("%", "percent", "percentage"), "ratio", "1", Decimal("0.01")),
)
_UNIT_INDEX = {
    alias: definition
    for definition in _UNIT_DEFINITIONS
    for alias in definition.aliases
}
_AMBIGUOUS_UNITS = {
    "KB": "KB puede significar kilobytes decimales o kibibytes; declaralo como kB o KiB.",
    "kb": "kb puede referirse a kilobits y no a kilobytes.",
    "Mb": "Mb representa megabits en convenciones habituales, no megabytes.",
}


def _multiply_exact(value: Decimal, factor: Decimal) -> Decimal:
    """Multiplica con precisión suficiente para no redondear conversiones válidas."""
    with localcontext() as context:
        context.prec = max(50, len(value.as_tuple().digits) + len(factor.as_tuple().digits) + 8)
        return value * factor


def parse_quantity(value: str) -> QuantityInspection:
    """Convierte solo magnitudes con unidad explícita y dimensionalmente reconocida.

    Los valores numéricos sin unidad nunca se clasifican por rango o longitud.
    Las unidades ambiguas, desconocidas o con escritura incorrecta no se convierten.
    """
    if not isinstance(value, str):
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason="La magnitud debe recibirse como texto.",
        )
    raw = value.strip()
    if len(raw) > MAX_MEASUREMENT_LENGTH:
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason=f"La magnitud supera el máximo de {MAX_MEASUREMENT_LENGTH} caracteres.",
        )
    match = _MEASUREMENT.fullmatch(raw)
    if not match:
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason="El valor no contiene un número decimal finito válido.",
        )
    try:
        number = Decimal(match.group("number"))
    except InvalidOperation:
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason="El número no es válido.",
        )
    if not number.is_finite():
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason="NaN e Infinity no son magnitudes admitidas.",
        )
    number_parts = number.as_tuple()
    if (
        len(number_parts.digits) > MAX_NUMERIC_DIGITS
        or abs(number_parts.exponent) > MAX_NUMERIC_EXPONENT
    ):
        return QuantityInspection(
            QuantityStatus.INVALID_NUMBER, None,
            reason="La precisión o escala numérica supera el límite admitido.",
        )

    unit = match.group("unit").strip()
    if not unit:
        return QuantityInspection(
            QuantityStatus.NO_UNIT,
            number,
            reason="El número no declara una unidad; no se infiere por su magnitud.",
        )
    if unit in _AMBIGUOUS_UNITS:
        return QuantityInspection(
            QuantityStatus.AMBIGUOUS_UNIT,
            number,
            source_unit=unit,
            reason=_AMBIGUOUS_UNITS[unit],
        )
    definition = _UNIT_INDEX.get(unit)
    if definition is None:
        return QuantityInspection(
            QuantityStatus.UNKNOWN_UNIT,
            number,
            source_unit=unit,
            reason=f"Unidad no registrada: {unit}.",
        )

    return QuantityInspection(
        status=QuantityStatus.EXPLICIT,
        numeric_value=number,
        source_unit=unit,
        dimension=definition.dimension,
        canonical_unit=definition.canonical_unit,
        normalized_value=_multiply_exact(number, definition.factor),
    )


def inspect_value(value: Any) -> ValueInspection:
    """Reconoce el tipo estructural sin deducir el significado contextual del dato."""
    if value is None:
        return ValueInspection(ValueKind.EMPTY)
    if isinstance(value, bool):
        return ValueInspection(ValueKind.BOOLEAN, normalized_preview=str(value).lower())
    if isinstance(value, int):
        if abs(value) >= 10 ** MAX_NUMERIC_DIGITS:
            return ValueInspection(
                ValueKind.INVALID,
                reason=f"La precisión numérica supera el máximo de {MAX_NUMERIC_DIGITS} dígitos.",
            )
        return ValueInspection(ValueKind.INTEGER, normalized_preview=str(value))
    if isinstance(value, float):
        if not math.isfinite(value):
            return ValueInspection(ValueKind.INVALID, reason="El número debe ser finito.")
        parts = Decimal(str(value)).as_tuple()
        if (
            len(parts.digits) > MAX_NUMERIC_DIGITS
            or abs(parts.exponent) > MAX_NUMERIC_EXPONENT
        ):
            return ValueInspection(
                ValueKind.INVALID,
                reason="La precisión o escala numérica supera el límite admitido.",
            )
        return ValueInspection(ValueKind.DECIMAL, normalized_preview=str(value))
    if isinstance(value, Decimal):
        if not value.is_finite():
            return ValueInspection(ValueKind.INVALID, reason="El número debe ser finito.")
        parts = value.as_tuple()
        if (
            len(parts.digits) > MAX_NUMERIC_DIGITS
            or abs(parts.exponent) > MAX_NUMERIC_EXPONENT
        ):
            return ValueInspection(
                ValueKind.INVALID,
                reason="La precisión o escala numérica supera el límite admitido.",
            )
        kind = ValueKind.INTEGER if value == value.to_integral_value() else ValueKind.DECIMAL
        return ValueInspection(kind, normalized_preview=str(value))
    if isinstance(value, (dict, list, tuple, set)):
        return ValueInspection(ValueKind.STRUCTURED, reason="El valor es una estructura, no un escalar.")

    if not isinstance(value, str):
        return ValueInspection(ValueKind.INVALID, reason="Tipo de valor no admitido.")

    raw = value.strip()
    if not raw:
        return ValueInspection(ValueKind.EMPTY)
    if len(raw) > MAX_INSPECTED_VALUE_LENGTH:
        return ValueInspection(
            ValueKind.INVALID,
            reason=f"El valor supera el máximo de {MAX_INSPECTED_VALUE_LENGTH} caracteres.",
        )
    lowered = raw.casefold()
    if lowered in {"true", "false"}:
        return ValueInspection(ValueKind.BOOLEAN, normalized_preview=lowered)

    quantity = parse_quantity(raw)
    if quantity.status is QuantityStatus.INVALID_NUMBER and _NUMBER.fullmatch(raw):
        return ValueInspection(
            ValueKind.INVALID,
            quantity=quantity,
            reason=quantity.reason or "La precisión o escala numérica supera el límite admitido.",
        )
    if quantity.status is QuantityStatus.EXPLICIT:
        return ValueInspection(
            ValueKind.MEASUREMENT,
            normalized_preview=str(quantity.normalized_value),
            quantity=quantity,
        )
    if quantity.status is QuantityStatus.AMBIGUOUS_UNIT:
        return ValueInspection(
            ValueKind.AMBIGUOUS_MEASUREMENT,
            quantity=quantity,
            reason=quantity.reason,
        )

    try:
        address = ipaddress.ip_address(raw)
        return ValueInspection(
            ValueKind.IP_ADDRESS,
            normalized_preview=str(address),
        )
    except ValueError:
        pass

    if _MAC.fullmatch(raw):
        normalized_mac = raw.lower().replace("-", ":").replace(".", "")
        if "." in raw:
            normalized_mac = ":".join(
                normalized_mac[index:index + 2] for index in range(0, 12, 2)
            )
        return ValueInspection(ValueKind.MAC_ADDRESS, normalized_preview=normalized_mac)

    if re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[Tt ])", raw):
        try:
            if len(raw) == 10:
                date.fromisoformat(raw)
                return ValueInspection(ValueKind.TIMESTAMP, normalized_preview=raw, timezone_aware=None)
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00").replace("z", "+00:00"))
            return ValueInspection(
                ValueKind.TIMESTAMP,
                normalized_preview=parsed.isoformat(),
                timezone_aware=parsed.tzinfo is not None and parsed.utcoffset() is not None,
            )
        except ValueError:
            return ValueInspection(ValueKind.INVALID, reason="La fecha ISO 8601 no es válida.")

    if _NUMBER.fullmatch(raw):
        if len(raw) > MAX_MEASUREMENT_LENGTH:
            return ValueInspection(
                ValueKind.INVALID,
                reason=f"El número supera el máximo de {MAX_MEASUREMENT_LENGTH} caracteres.",
            )
        try:
            number = Decimal(raw)
        except InvalidOperation:
            return ValueInspection(ValueKind.INVALID, reason="El número no es válido.")
        parts = number.as_tuple()
        if (
            len(parts.digits) > MAX_NUMERIC_DIGITS
            or abs(parts.exponent) > MAX_NUMERIC_EXPONENT
        ):
            return ValueInspection(
                ValueKind.INVALID,
                quantity=quantity,
                reason="La precisión o escala numérica supera el límite admitido.",
            )
        kind = ValueKind.INTEGER if number == number.to_integral_value() else ValueKind.DECIMAL
        # Se conserva el texto original: clasificar un número no autoriza a usarlo
        # como puerto, bytes, paquetes, duración, identificador o timestamp Unix.
        return ValueInspection(kind, normalized_preview=raw, quantity=quantity)

    return ValueInspection(ValueKind.TEXT, quantity=quantity if quantity.status is not QuantityStatus.INVALID_NUMBER else None)



def inspect_field_value(field_name: str, value: Any) -> FieldValueCheck:
    """Valida un valor según un campo conocido sin inferir el rol desde su contenido.

    La forma observada no cambia el significado del campo. Por ejemplo, un entero
    no se convierte en timestamp Unix por su magnitud; los contadores siguen
    dependiendo de la semántica y la capa de medición declaradas por la fuente.
    """
    definition = get_field_definition(field_name)
    inspection = inspect_value(value)
    if definition is None:
        return FieldValueCheck(
            field_name, FieldValueStatus.UNKNOWN_FIELD, None, inspection,
            "El campo no existe en el catálogo semántico.",
        )
    if value is None:
        return FieldValueCheck(
            field_name, FieldValueStatus.MISSING, definition.value_kind, inspection,
            "La fuente no informó este campo.",
        )
    if inspection.kind is ValueKind.EMPTY:
        return FieldValueCheck(
            field_name, FieldValueStatus.EMPTY, definition.value_kind, inspection,
            "El campo llegó vacío; no equivale a un cero observado.",
        )
    if inspection.kind is ValueKind.INVALID:
        return FieldValueCheck(
            field_name, FieldValueStatus.INVALID, definition.value_kind, inspection,
            inspection.reason or "El valor no es válido.",
        )
    if inspection.kind is ValueKind.AMBIGUOUS_MEASUREMENT:
        return FieldValueCheck(
            field_name, FieldValueStatus.AMBIGUOUS, definition.value_kind, inspection,
            inspection.reason or "La unidad declarada es ambigua.",
        )

    valid = False
    reason: str | None = None
    raw_text = value.strip() if isinstance(value, str) else None

    if definition.value_kind is ValueKind.TEXT:
        valid = isinstance(value, str)
    elif definition.value_kind is ValueKind.BOOLEAN:
        valid = inspection.kind is ValueKind.BOOLEAN
        if raw_text is not None and raw_text.casefold() in {"yes", "no", "1", "0"}:
            valid = True
        if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
            valid = True
    elif definition.value_kind is ValueKind.INTEGER:
        valid = inspection.kind is ValueKind.INTEGER
        if valid and definition.minimum is not None and definition.maximum is not None:
            # Comparar como Decimal evita excepciones para representaciones como
            # "443.0" o "4.43e2" que son enteras por valor, pero no por sintaxis.
            numeric = Decimal(str(value))
            if not Decimal(definition.minimum) <= numeric <= Decimal(definition.maximum):
                valid = False
                reason = f"El valor debe estar entre {definition.minimum} y {definition.maximum}."
    elif definition.value_kind is ValueKind.IP_ADDRESS:
        valid = inspection.kind is ValueKind.IP_ADDRESS
    elif definition.value_kind is ValueKind.MAC_ADDRESS:
        valid = inspection.kind is ValueKind.MAC_ADDRESS
    elif definition.value_kind is ValueKind.TIMESTAMP:
        valid = inspection.kind is ValueKind.TIMESTAMP

    return FieldValueCheck(
        field_name=field_name,
        status=FieldValueStatus.VALID if valid else FieldValueStatus.TYPE_MISMATCH,
        expected_kind=definition.value_kind,
        inspection=inspection,
        reason=reason or (
            None if valid else
            f"El campo espera {definition.value_kind.value}, pero el valor tiene forma {inspection.kind.value}."
        ),
    )
