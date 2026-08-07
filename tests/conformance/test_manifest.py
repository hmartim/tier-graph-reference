"""Execute every registered conformance case and assert it passes (T01-T10)."""

from __future__ import annotations

import pytest

from tier_graph_reference.conformance.loader import (
    FixtureError,
    _assert_no_relation_intervals,
    default_fixtures_dir,
    load_manifest,
)
from tier_graph_reference.conformance.runner import run_case
from tier_graph_reference.models import INTERVAL_KEYS

_MANIFEST = load_manifest(default_fixtures_dir())


def test_manifest_registers_ten_cases() -> None:
    assert len(_MANIFEST.cases) == 10
    assert _MANIFEST.specification_version == "0.1.0-draft"


@pytest.mark.parametrize("case", _MANIFEST.cases, ids=[c.case_id for c in _MANIFEST.cases])
def test_case_passes(case) -> None:  # type: ignore[no-untyped-def]
    result = run_case(case)
    assert result["passed"], result["explanation"]


@pytest.mark.parametrize("key", sorted(INTERVAL_KEYS))
def test_loader_rejects_relation_intervals_in_raw_fixture(key: str) -> None:
    """R3 at the fixture level: the scan must name the invariant, not just fail."""
    payload = {"relations": [{"id": "dr-x", key: "2020-01-01T00:00:00Z"}]}
    with pytest.raises(FixtureError, match=r"R3"):
        _assert_no_relation_intervals("TXX", payload)


def test_loader_accepts_clean_fixture() -> None:
    _assert_no_relation_intervals("TXX", {"relations": [{"id": "dr-x", "predicate": "P"}]})
