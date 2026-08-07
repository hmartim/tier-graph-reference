"""Prove the conformance assertions can fail.

A case that passes proves nothing unless a violation would make it fail. Each
mutation below breaks exactly one property the suite claims to verify; the
corresponding case MUST turn red, and MUST do so *on the field that announces
that property*. Asserting only ``passed is False`` would go green when a
mutation breaks something unrelated -- the harness would inherit the very defect
it exists to prevent.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest

from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest
from tier_graph_reference.conformance.runner import run_case
from tier_graph_reference.grounding import base as grounding_base
from tier_graph_reference.models import GroundedPath, iso_z
from tier_graph_reference.models import evidence as evidence_models
from tier_graph_reference.models import grounding as grounding_models
from tier_graph_reference.models import path as path_models
from tier_graph_reference.models import relation as relation_models
from tier_graph_reference.services import authoring as authoring_service
from tier_graph_reference.services import identity as identity_service
from tier_graph_reference.services import paths as paths_service
from tier_graph_reference.store import memory as memory_store

_MANIFEST = load_manifest(default_fixtures_dir())
_CASES = {case.case_id: case for case in _MANIFEST.cases}

Mutation = Callable[[pytest.MonkeyPatch], None]


# --------------------------------------------------------------------------
# Mutations
# --------------------------------------------------------------------------
def all_time_traversal_then_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """R7 violation: traverse the all-time graph, filter the answer afterwards.

    This is the anti-pattern §7 prohibits, and it is output-equivalent to the
    conforming implementation -- only the trace can tell them apart.
    """

    def leaky(
        self: paths_service.PathService,
        source_entity_id: str,
        target_entity_id: str,
        at: datetime,
        policy_id: str,
        max_depth: int,
        observer_time: datetime | None = None,
    ) -> tuple[list[GroundedPath], list[Any], paths_service.TraversalTrace]:
        projected = self._projection.project(at, policy_id, observer_time)
        admitted = {rel.relationId for rel in projected}
        all_edges = [
            paths_service.Edge(rel.sourceEntityId, rel.targetEntityId, rel.id)
            for rel in self._store.list_relations()
        ]
        visited: set[str] = set()
        routes = paths_service._edge_paths(
            all_edges, source_entity_id, target_entity_id, max_depth, visited=visited
        )
        routes = [r for r in routes if all(rid in admitted for rid in r)]
        paths = [
            self._build_path(i, source_entity_id, target_entity_id, r, at, policy_id,
                             observer_time)
            for i, r in enumerate(routes)
        ]
        trace = paths_service.TraversalTrace(
            offeredRelationIds=frozenset(edge.relation_id for edge in all_edges),
            visitedRelationIds=frozenset(visited),
            returnedRelationIds=frozenset(rid for p in paths for rid in p.relation_ids),
            projectedRelationIds=frozenset(admitted),
            allTimeRelationCount=len(self._store.list_relations()),
        )
        excluded = self._explain_excluded_routes(
            source_entity_id, target_entity_id, max_depth, admitted, at, observer_time
        )
        return paths, excluded, trace

    monkeypatch.setattr(paths_service.PathService, "find_paths_traced", leaky)


def delete_historical_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    """R3/§6.3 violation: drop evidence instead of retaining it as inadmissible."""
    original = memory_store.MemoryTierStore.get_evidence

    def forgetful(self: memory_store.MemoryTierStore, evidence_id: str) -> Any:
        if evidence_id == "re-divorce-pre-2010":
            return None  # simulate physical deletion once the source state closed
        return original(self, evidence_id)

    monkeypatch.setattr(memory_store.MemoryTierStore, "get_evidence", forgetful)


def unknown_treated_as_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """§4 violation: an unresolved qualifier stops blocking automatic merging."""
    monkeypatch.setattr(
        identity_service.RelationQualifier,
        "is_unknown",
        property(lambda self: False),
    )


def polarity_ignored_in_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """§4 violation: polarity drops out of the identity key."""
    reduced = tuple(
        d for d in relation_models.IDENTITY_BEARING_QUALIFIERS if d != "polarity"
    )
    monkeypatch.setattr(
        identity_service.RelationIdentityService,
        "__init__",
        lambda self, identity_bearing=reduced: setattr(self, "_dimensions", reduced),
    )


def anchors_combined_disjunctively(monkeypatch: pytest.MonkeyPatch) -> None:
    """§3 violation: a conjunctive evidence basis becomes disjunctive."""
    original = grounding_base.TemporalGroundingProvider.evaluate_evidence

    def any_anchor(
        self: grounding_base.TemporalGroundingProvider,
        evidence: Any,
        at: datetime,
        observer_time: datetime | None = None,
    ) -> Any:
        result = original(self, evidence, at, observer_time)
        return type(result)(
            at=iso_z(at),
            admissible=any(result.anchorResults.values()),
            anchorResults=result.anchorResults,
        )

    monkeypatch.setattr(
        grounding_base.TemporalGroundingProvider, "evaluate_evidence", any_anchor
    )


def publication_controls_admissibility(monkeypatch: pytest.MonkeyPatch) -> None:
    """§5 violation: publication admits a provision before its applicability."""

    def published_is_admissible(
        self: grounding_models.GroundingSourceState, at: datetime
    ) -> bool:
        start = self.publishedAt or self.admissibleFrom
        if at < start:
            return False
        return self.admissibleTo is None or at < self.admissibleTo

    monkeypatch.setattr(
        grounding_models.GroundingSourceState, "admissible_at", published_is_admissible
    )


def evidence_key_never_looked_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """spec/04 §4.4 violation: every submission creates a fresh record.

    This is the failure mode T08 exists to prevent -- re-extraction inflating
    apparent corroboration by turning one basis into several.
    """
    monkeypatch.setattr(
        authoring_service.EvidenceAuthoringService,
        "find_by_key",
        lambda self, key: None,
    )


def activity_included_in_evidence_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """spec/04 §4.4 violation: provenance becomes identity-bearing.

    If the activity is part of the key, a re-run with a new activity is a new
    basis by construction, and de-duplication can never trigger.
    """
    original = evidence_models.RelationEvidence.identity_key.fget  # type: ignore[attr-defined]

    def keyed_by_activity(self: evidence_models.RelationEvidence) -> Any:
        base = original(self)
        # Keep the EvidenceKey shape; only make provenance identity-bearing.
        return base._replace(
            anchors=(*base.anchors, ("__activity__", ",".join(self.provenanceActivityIds), ""))
        )

    monkeypatch.setattr(
        evidence_models.RelationEvidence,
        "identity_key",
        property(keyed_by_activity),
    )


def path_step_state_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    """§7 violation: the edge is reduced to an identifier, dropping its state.

    This reproduces the defect the reference actually shipped: under a
    recall-oriented policy a refuted relation became indistinguishable from a
    supported one, because the answer carried no per-step evidential state.
    """
    original = path_models.GroundedPath.model_dump

    def flat(self: path_models.GroundedPath, **kwargs: Any) -> Any:
        dumped = original(self, **kwargs)
        # The exact pre-correction shape: a flat identifier list, no steps.
        dumped["relationIds"] = [step["relationId"] for step in dumped.pop("steps", [])]
        return dumped

    monkeypatch.setattr(path_models.GroundedPath, "model_dump", flat)


def zero_length_path_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    """spec/08 violation: a trivial zero-step path is returned as a result.

    Graph theory admits the trivial path from a vertex to itself; this contract
    does not, because a zero-step answer carries no evidence and no
    admissibility to report. The DFS enforces it in a single ``and acc``
    conjunct, which is easy to drop by accident.
    """
    original = paths_service._edge_paths

    def with_trivial(
        edges: Any, source: str, target: str, max_depth: int, **kwargs: Any
    ) -> Any:
        results = original(edges, source, target, max_depth, **kwargs)
        return [[], *results]  # the zero-length path the guard suppresses

    monkeypatch.setattr(paths_service, "_edge_paths", with_trivial)


#: (mutation, case, substring the failure explanation must mention)
MUTATIONS: list[tuple[Mutation, str, str]] = [
    (path_step_state_discarded, "T10", "steps"),
    (zero_length_path_returned, "T10", "paths"),
    (all_time_traversal_then_filter, "T10", "trace"),
    (delete_historical_evidence, "T04", "historicalEvidence"),
    (unknown_treated_as_absent, "T06", "decision"),
    (polarity_ignored_in_identity, "T07", "pairwiseIdentity"),
    (anchors_combined_disjunctively, "T05", "semantics"),
    (publication_controls_admissibility, "T09", "vacatioChecks"),
    (evidence_key_never_looked_up, "T08", "evidenceRecordCount"),
    (activity_included_in_evidence_key, "T08", "evidenceRecordCount"),
]


@pytest.mark.parametrize(
    "mutation,case_id,field",
    MUTATIONS,
    ids=[f"{case_id}-{m.__name__}" for m, case_id, _ in MUTATIONS],
)
def test_mutation_turns_case_red(
    mutation: Mutation, case_id: str, field: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    mutation(monkeypatch)
    result = run_case(_CASES[case_id])
    assert result["passed"] is False, (
        f"{case_id} still passes under {mutation.__name__}: its assertion is vacuous"
    )
    assert any(field in line for line in result["explanation"]), (
        f"{case_id} failed under {mutation.__name__}, but not on {field!r} -- "
        f"the mutation may be breaking something unrelated. "
        f"Explanation: {result['explanation']}"
    )


def test_suite_is_green_without_mutations() -> None:
    """The mutations above must be the only reason any case fails."""
    failures = [c.case_id for c in _MANIFEST.cases if not run_case(c)["passed"]]
    assert not failures, f"unmutated cases failing: {failures}"
