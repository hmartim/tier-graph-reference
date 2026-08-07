"""Deterministic partial-match comparison of expected vs. actual results.

``expected`` is treated as an *assertion*: every key/value it declares must be
present and equal in ``actual``. Extra keys in ``actual`` are allowed (fixtures
assert only the fields relevant to a case), but arrays must match element-for-
element and in length. This keeps a single operation handler able to serve
several cases that assert different subsets.
"""

from __future__ import annotations

from typing import Any


def diff(expected: Any, actual: Any, path: str = "$") -> list[str]:
    """Return a list of human-readable mismatch descriptions (empty if it matches)."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {_typename(actual)}"]
        mismatches: list[str] = []
        for key, value in expected.items():
            if key not in actual:
                mismatches.append(f"{path}.{key}: missing in actual")
            else:
                mismatches.extend(diff(value, actual[key], f"{path}.{key}"))
        return mismatches
    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [f"{path}: expected array, got {_typename(actual)}"]
        if len(expected) != len(actual):
            return [f"{path}: array length {len(actual)} != expected {len(expected)}"]
        mismatches = []
        for index, (exp_item, act_item) in enumerate(zip(expected, actual, strict=True)):
            mismatches.extend(diff(exp_item, act_item, f"{path}[{index}]"))
        return mismatches
    if expected != actual:
        return [f"{path}: {actual!r} != expected {expected!r}"]
    return []


def matches(expected: Any, actual: Any) -> bool:
    return not diff(expected, actual)


def _typename(value: Any) -> str:
    return type(value).__name__
