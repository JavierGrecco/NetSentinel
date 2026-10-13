#!/usr/bin/env python3
"""Verify CI's minimum dependency constraints match pyproject lower bounds."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENT = re.compile(
    r"^\\s*([A-Za-z0-9_.-]+)(?:\\[[^]]+\\])?\\s*>=\\s*([0-9]+(?:\\.[0-9]+)*)"
)
PIN = re.compile(r"^\\s*([A-Za-z0-9_.-]+)\\s*==\\s*([0-9]+(?:\\.[0-9]+)*)\\s*$")


def normalized_name(name: str) -> str:
    """Normalize package names as packaging tools do for simple ASCII names."""
    return re.sub(r"[-_.]+", "-", name).lower()


def normalized_version(version: str) -> tuple[int, ...]:
    """Normalize numeric lower bounds so 2.0 equals 2.0.0 for comparison."""
    parts = [int(part) for part in version.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def main() -> int:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    requirements = list(project.get("dependencies", []))
    requirements.extend(project.get("optional-dependencies", {}).get("test", []))

    expected: dict[str, str] = {}
    errors: list[str] = []
    for requirement in requirements:
        match = REQUIREMENT.match(requirement)
        if not match:
            errors.append(f"Cannot parse direct requirement or lower bound: {requirement!r}")
            continue
        name, lower_bound = match.groups()
        normalized = normalized_name(name)
        if normalized in expected:
            errors.append(f"Duplicate direct requirement name in project metadata: {name}")
            continue
        expected[normalized] = lower_bound

    pins: dict[str, str] = {}
    for line_number, line in enumerate(
        (ROOT / "ci" / "constraints-min.txt").read_text(encoding="utf-8").splitlines(), start=1
    ):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = PIN.match(stripped)
        if not match:
            errors.append(f"Unsupported minimum constraint syntax on line {line_number}: {stripped!r}")
            continue
        name, pin = match.groups()
        normalized = normalized_name(name)
        if normalized in pins:
            errors.append(f"Duplicate minimum constraint for {name}")
            continue
        pins[normalized] = pin

    for name in sorted(expected.keys() - pins.keys()):
        errors.append(f"Missing minimum constraint for {name} (pyproject lower bound >= {expected[name]})")
    for name in sorted(pins.keys() - expected.keys()):
        errors.append(f"Unexpected minimum constraint for {name}; no matching direct requirement exists")
    for name in sorted(expected.keys() & pins.keys()):
        if normalized_version(expected[name]) != normalized_version(pins[name]):
            errors.append(
                f"Constraint mismatch for {name}: pyproject lower bound >= {expected[name]}, "
                f"minimum constraint is == {pins[name]}"
            )

    if errors:
        print("Minimum dependency constraints are out of sync:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(expected)} minimum direct runtime/test dependency constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
