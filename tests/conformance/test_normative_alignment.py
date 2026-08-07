"""Cross-check the fixture manifest against the vendored normative catalogue.

`tier-graph-api` DEFINES conformance; this repository EXECUTES it. Nothing
previously compared the two, which is how four operation divergences and four
competency-question divergences went unnoticed.

The rule enforced here is not "the fixtures must match the catalogue exactly" --
an implementation may legitimately satisfy a case with a stronger operation, or
carry the property in an asserted invariant. The rule is that **no divergence may
be silent**: anything that differs must be declared under `normativeAlignment`
with a status and a rationale.

See docs/conformance.md and vendor/tier-graph-api/0.1.0-draft/README.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_NORMATIVE_PATH = _ROOT / "vendor/tier-graph-api/0.1.0-draft/conformance/manifest.yaml"
_FIXTURE_PATH = _ROOT / "fixtures/manifest.yaml"

#: Divergences that are known gaps rather than justified substitutions -- i.e. the
#: normative behaviour is NOT executed. Empty since T08 was closed by implementing
#: createEvidence. Adding one requires editing this set, so a gap can never appear
#: silently.
_DECLARED_GAPS: set[str] = set()

_VALID_STATUSES = {"subsumes", "covered-by-invariant", "gap"}


def _load(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


_NORMATIVE = _load(_NORMATIVE_PATH)
_FIXTURES = _load(_FIXTURE_PATH)
_NORM_CASES = {c["id"]: c for c in _NORMATIVE["cases"]}
_FIX_CASES = {c["id"]: c for c in _FIXTURES["cases"]}
_CASE_IDS = sorted(_NORM_CASES)


def test_vendored_catalogue_is_present() -> None:
    """Without the vendored catalogue every check below would silently pass."""
    assert _NORMATIVE_PATH.is_file(), (
        f"missing vendored normative catalogue at {_NORMATIVE_PATH}; "
        "re-vendor it before relying on this suite"
    )
    assert _NORMATIVE["version"] == _FIXTURES["specificationVersion"]


def test_case_coverage_matches_exactly() -> None:
    assert set(_FIX_CASES) == set(_NORM_CASES), (
        f"missing fixtures: {sorted(set(_NORM_CASES) - set(_FIX_CASES))}; "
        f"unknown fixtures: {sorted(set(_FIX_CASES) - set(_NORM_CASES))}"
    )


@pytest.mark.parametrize("case_id", _CASE_IDS)
def test_slug_matches_fixture_directory(case_id: str) -> None:
    slug = _NORM_CASES[case_id]["slug"]
    directory = _FIX_CASES[case_id]["directory"]
    assert directory == f"cases/{case_id}-{slug}", (
        f"{case_id}: fixture directory {directory!r} does not follow the normative slug {slug!r}"
    )


@pytest.mark.parametrize("case_id", _CASE_IDS)
def test_competency_questions_match(case_id: str) -> None:
    assert sorted(_FIX_CASES[case_id]["competencyQuestions"]) == sorted(
        _NORM_CASES[case_id]["competencyQuestions"]
    )


@pytest.mark.parametrize("case_id", _CASE_IDS)
def test_conformance_classes_match(case_id: str) -> None:
    assert sorted(_FIX_CASES[case_id]["conformanceClasses"]) == sorted(
        _NORM_CASES[case_id]["conformanceClasses"]
    )


@pytest.mark.parametrize("case_id", _CASE_IDS)
def test_operation_matches_or_divergence_is_declared(case_id: str) -> None:
    normative_op = _NORM_CASES[case_id]["operation"]
    fixture = _FIX_CASES[case_id]
    if fixture["operation"] == normative_op:
        assert "normativeAlignment" not in fixture, (
            f"{case_id}: operation already matches the catalogue; "
            "remove the stale normativeAlignment block"
        )
        return

    alignment = fixture.get("normativeAlignment")
    assert alignment is not None, (
        f"{case_id}: fixture runs {fixture['operation']!r} but the normative catalogue "
        f"specifies {normative_op!r}, with no normativeAlignment declaration. "
        "Undeclared divergence is not permitted."
    )
    assert alignment["operation"] == normative_op, (
        f"{case_id}: normativeAlignment.operation is {alignment['operation']!r} but the "
        f"catalogue says {normative_op!r} -- the declaration is stale"
    )
    assert alignment["status"] in _VALID_STATUSES
    assert len(alignment.get("rationale", "").strip()) > 40, (
        f"{case_id}: normativeAlignment needs a substantive rationale"
    )


def test_declared_gaps_are_exactly_the_known_ones() -> None:
    """A new gap must be an explicit edit here, never a side effect."""
    gaps = {
        cid
        for cid, case in _FIX_CASES.items()
        if case.get("normativeAlignment", {}).get("status") == "gap"
    }
    assert gaps == _DECLARED_GAPS, (
        f"declared gaps changed: {sorted(gaps)} != {sorted(_DECLARED_GAPS)}. "
        "A gap means the normative behaviour is NOT executed; confirm it is intended "
        "and that the conformance report and docs say so."
    )


def test_subsumption_is_executed_not_merely_declared() -> None:
    """`status: subsumes` must be a demonstrated property, not a human judgement.

    T01 runs getRelationHistory where the catalogue specifies
    getRelationStateAtTime. That is only a legitimate substitution if the
    normative operation's answer is *derivable* from the executed one: for every
    instant, the state of the history segment covering it must equal the state
    getRelationStateAtTime reports. Probe instants are taken from the fixture's
    own source-state boundaries, plus points just inside and just outside each,
    so the half-open convention is exercised too.
    """
    from datetime import timedelta

    from tier_graph_reference.conformance.loader import (
        default_fixtures_dir as _dir,
    )
    from tier_graph_reference.conformance.loader import (
        load_manifest as _load_manifest,
    )
    from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
    from tier_graph_reference.models import parse_instant
    from tier_graph_reference.services import ServiceContext
    from tier_graph_reference.store.memory import MemoryTierStore

    subsuming = [
        cid
        for cid, case in _FIX_CASES.items()
        if case.get("normativeAlignment", {}).get("status") == "subsumes"
    ]
    assert subsuming, "no subsumption declared; this check would be vacuous"

    case = next(c for c in _load_manifest(_dir()).cases if c.case_id in subsuming)
    store = MemoryTierStore.from_input(case.input)
    grounding = FixtureGroundingProvider.from_dict(case.profile)
    ctx = ServiceContext.build(store, grounding)

    relation_id = case.request["arguments"]["relationId"]
    start = parse_instant(case.request["arguments"]["startAt"])
    end = parse_instant(case.request["arguments"]["endAt"])

    probes = {start}
    for state in grounding.profile_source_states():
        for boundary in (state.admissibleFrom, state.admissibleTo):
            if boundary is None or not (start <= boundary <= end):
                continue
            probes.update(
                {boundary - timedelta(seconds=1), boundary, boundary + timedelta(seconds=1)}
            )
    probes = {p for p in probes if start <= p <= end}
    assert len(probes) > 3, "too few probe instants to demonstrate subsumption"

    history = ctx.relation_state.history(relation_id, start=start, end=end)
    for at in sorted(probes):
        segment = next(
            (
                entry
                for entry in history
                if parse_instant(entry.model_dump(by_alias=True)["from"]) <= at
                and (entry.to is None or at < parse_instant(entry.to))
            ),
            None,
        )
        assert segment is not None, f"history does not cover {at}"
        point = ctx.relation_state.state_at(relation_id, at)
        assert segment.state is point.state, (
            f"subsumption fails at {at}: history segment says {segment.state}, "
            f"getRelationStateAtTime says {point.state}"
        )
        assert segment.supportingEvidenceIds == point.supportingEvidenceIds


def test_no_normative_operation_is_left_unexecuted() -> None:
    """Every normative operation in the catalogue is actually executed by a case."""
    executed = {case["operation"] for case in _FIX_CASES.values()}
    normative = {case["operation"] for case in _NORM_CASES.values()}
    unexecuted = sorted(
        op
        for op in normative
        if op not in executed
        and not any(
            c.get("normativeAlignment", {}).get("operation") == op
            and c["normativeAlignment"]["status"] != "gap"
            for c in _FIX_CASES.values()
        )
    )
    assert not unexecuted, (
        f"normative operations neither executed nor covered by a justified "
        f"divergence: {unexecuted}"
    )
