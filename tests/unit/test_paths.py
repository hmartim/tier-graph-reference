"""Path search over the time-indexed projection, with exclusion explanations."""

from __future__ import annotations

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import parse_instant
from tier_graph_reference.services import ServiceContext, TraversalTrace
from tier_graph_reference.services.paths import REASON_SOURCE_STATE
from tier_graph_reference.store.memory import MemoryTierStore

_INPUT = {
    "entities": [
        {"id": "de-a", "canonicalLabel": "A", "entityType": "concept", "reviewStatus": "accepted"},
        {"id": "de-b", "canonicalLabel": "B", "entityType": "concept", "reviewStatus": "accepted"},
        {"id": "de-c", "canonicalLabel": "C", "entityType": "concept", "reviewStatus": "accepted"},
    ],
    "relations": [
        {
            "id": "ab",
            "sourceEntityId": "de-a",
            "predicate": "DEPENDS_ON",
            "targetEntityId": "de-b",
            "predicateFamily": "procedural",
            "reviewStatus": "accepted",
        },
        {
            "id": "bc",
            "sourceEntityId": "de-b",
            "predicate": "TRIGGERS",
            "targetEntityId": "de-c",
            "predicateFamily": "normativeConsequential",
            "reviewStatus": "accepted",
        },
    ],
    "evidence": [
        {
            "id": "e-ab",
            "relationId": "ab",
            "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u-ab"}}],
            "stance": "supports",
            "reviewStatus": "accepted",
        },
        {
            "id": "e-bc",
            "relationId": "bc",
            "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u-bc"}}],
            "stance": "supports",
            "reviewStatus": "accepted",
        },
    ],
    "admissionPolicies": [{"id": "strict", "name": "strict", "admittedStates": ["supported"]}],
}
_PROFILE = {
    "profile": {"id": "p", "version": "1"},
    "evidenceUnits": [
        {"id": "u-ab", "ownerSourceStateId": "s-ab"},
        {"id": "u-bc", "ownerSourceStateId": "s-bc-future"},
    ],
    "sourceStates": [
        {"id": "s-ab", "admissibleFrom": "2020-01-01T00:00:00Z", "admissibleTo": None},
        {"id": "s-bc-future", "admissibleFrom": "2026-01-01T00:00:00Z", "admissibleTo": None},
    ],
}


def _ctx() -> ServiceContext:
    store = MemoryTierStore.from_input(_INPUT)
    return ServiceContext.build(store, FixtureGroundingProvider.from_dict(_PROFILE))


def test_no_path_before_future_boundary_with_explanation() -> None:
    ctx = _ctx()
    paths, excluded = ctx.paths.find_paths(
        "de-a", "de-c", parse_instant("2025-01-01T00:00:00Z"), "strict", 2
    )
    assert paths == []
    assert len(excluded) == 1
    assert excluded[0].relationId == "bc"
    assert excluded[0].reasonCode == REASON_SOURCE_STATE
    assert excluded[0].evidenceId == "e-bc"


def test_path_admitted_after_boundary() -> None:
    ctx = _ctx()
    paths, excluded = ctx.paths.find_paths(
        "de-a", "de-c", parse_instant("2026-01-01T00:00:00Z"), "strict", 2
    )
    assert [p.relation_ids for p in paths] == [["ab", "bc"]]
    assert excluded == []


def test_trace_records_only_candidate_generation() -> None:
    ctx = _ctx()
    _, _, trace = ctx.paths.find_paths_traced(
        "de-a", "de-c", parse_instant("2025-01-01T00:00:00Z"), "strict", 2
    )
    # The diagnostic enumeration walks the all-time graph; it must not leak in.
    assert trace.offeredRelationIds == frozenset({"ab"})
    assert trace.projectedRelationIds == frozenset({"ab"})
    assert trace.projection_is_non_trivial
    assert trace.uses_projected_graph
    assert trace.leakage_witness_relation_ids == []


def _trace(
    offered: set[str], projected: set[str], *, visited: set[str] | None = None
) -> TraversalTrace:
    return TraversalTrace(
        offeredRelationIds=frozenset(offered),
        visitedRelationIds=frozenset(visited if visited is not None else offered),
        returnedRelationIds=frozenset(),
        projectedRelationIds=frozenset(projected),
        allTimeRelationCount=len(projected) + 1,
    )


def test_narrowing_below_the_projection_is_conformant() -> None:
    """R7 constrains candidate generation *by* the projection, not *to* all of it.

    An implementation that prunes further before traversing -- by reachability,
    predicate family, or direction -- offers a strict subset and introduces no
    temporal-topology leakage. Requiring equality would reject it.
    """
    trace = _trace(offered={"ab"}, projected={"ab", "bc"})
    assert trace.uses_projected_graph
    assert trace.leakage_witness_relation_ids == []


def test_offering_outside_the_projection_is_leakage() -> None:
    trace = _trace(offered={"ab", "bc"}, projected={"ab"})
    assert not trace.uses_projected_graph
    assert trace.leakage_witness_relation_ids == ["bc"]


def test_visiting_more_than_was_offered_is_leakage() -> None:
    """Guards the instrument itself: the trace must observe the real edge set."""
    trace = _trace(offered={"ab"}, projected={"ab"}, visited={"ab", "bc"})
    assert not trace.uses_projected_graph
    assert trace.leakage_witness_relation_ids == ["bc"]
