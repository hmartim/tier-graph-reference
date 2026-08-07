"""Partial-match comparator semantics."""

from __future__ import annotations

from tier_graph_reference.conformance.compare import diff, matches


def test_extra_keys_in_actual_are_allowed() -> None:
    assert matches({"a": 1}, {"a": 1, "b": 2})


def test_missing_expected_key_fails() -> None:
    assert not matches({"a": 1}, {"b": 2})


def test_array_length_must_match() -> None:
    assert not matches([1, 2], [1, 2, 3])
    assert matches([1, 2], [1, 2])


def test_nested_partial_match() -> None:
    expected = {"states": [{"state": "supported"}]}
    actual = {"states": [{"state": "supported", "at": "t", "extra": True}], "invariants": {}}
    assert matches(expected, actual)


def test_diff_reports_path() -> None:
    problems = diff({"x": {"y": 1}}, {"x": {"y": 2}})
    assert problems == ["$.x.y: 2 != expected 1"]
