"""Evidence identity and create-or-append semantics (spec/04 §4.4, case T08).

The happy path -- re-extraction appends provenance instead of duplicating -- is
only half the contract. These tests pin the boundaries: what counts as the *same*
evidential basis, and what legitimately counts as a different one. Getting the
boundary wrong in either direction is a defect: too loose merges distinct bases,
too strict inflates apparent corroboration.
"""

from __future__ import annotations

from typing import Any

import pytest

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import ProvenanceActivity, RelationEvidence
from tier_graph_reference.services import ServiceContext
from tier_graph_reference.store.memory import MemoryTierStore

_INPUT: dict[str, Any] = {
    "entities": [
        {"id": "de-a", "canonicalLabel": "A", "entityType": "concept", "reviewStatus": "accepted"},
        {"id": "de-b", "canonicalLabel": "B", "entityType": "concept", "reviewStatus": "accepted"},
    ],
    "relations": [
        {
            "id": "r1",
            "sourceEntityId": "de-a",
            "predicate": "DEPENDS_ON",
            "targetEntityId": "de-b",
            "predicateFamily": "procedural",
            "reviewStatus": "accepted",
        }
    ],
}
_PROFILE = {"profile": {"id": "p", "version": "1"}, "evidenceUnits": [], "sourceStates": []}


def _ctx() -> ServiceContext:
    store = MemoryTierStore.from_input(_INPUT)
    return ServiceContext.build(store, FixtureGroundingProvider.from_dict(_PROFILE))


def _anchor(unit: str, selector: dict[str, Any] | None = None, role: str | None = None) -> dict:
    anchor: dict[str, Any] = {"evidenceUnit": {"profileId": "p", "evidenceUnitId": unit}}
    if selector is not None:
        anchor["selector"] = selector
    if role is not None:
        anchor["role"] = role
    return anchor


def _evidence(evidence_id: str, anchors: list[dict], stance: str = "supports") -> RelationEvidence:
    return RelationEvidence.model_validate(
        {"id": evidence_id, "relationId": "r1", "anchors": anchors, "stance": stance,
         "reviewStatus": "accepted"}
    )


def _activity(activity_id: str) -> ProvenanceActivity:
    return ProvenanceActivity.model_validate(
        {"id": activity_id, "activityType": "extraction", "startedAt": "2026-01-01T00:00:00Z"}
    )


# -- same basis -------------------------------------------------------------
def test_reextraction_appends_activity_without_new_record() -> None:
    authoring = _ctx().require_authoring()
    first = authoring.create_evidence(_evidence("e1", [_anchor("u1")]), _activity("a1"))
    second = authoring.create_evidence(_evidence("e2", [_anchor("u1")]), _activity("a2"))

    assert first.created and not first.duplicateKeyDetected
    assert not second.created and second.duplicateKeyDetected
    assert second.evidenceId == "e1", "the original occurrence must keep its identifier"
    assert second.provenanceActivityIds == ["a1", "a2"]
    assert authoring.independent_evidence_count("r1") == 1


def test_anchor_order_does_not_affect_identity() -> None:
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1"), _anchor("u2")]), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u2"), _anchor("u1")]), _activity("a2")
    )
    assert not outcome.created, "anchors are a set; submission order is not identity"
    assert outcome.evidenceId == "e1"


def test_repeated_anchor_normalizes_to_the_same_basis() -> None:
    """Anchors are a set: ``u ∧ u ≡ u``, so a repeat is not a broader basis."""
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1")]), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u1"), _anchor("u1")]), _activity("a2")
    )
    assert not outcome.created
    assert outcome.evidenceId == "e1"
    assert authoring.independent_evidence_count("r1") == 1


def test_confidence_and_model_are_not_identity_bearing() -> None:
    """Provenance detail never constitutes a distinct evidential basis."""
    authoring = _ctx().require_authoring()
    first = ProvenanceActivity.model_validate(
        {
            "id": "a1",
            "activityType": "extraction",
            "startedAt": "2026-01-01T00:00:00Z",
            "model": {"name": "extractor", "version": "1.0"},
            "confidence": 0.6,
        }
    )
    second = ProvenanceActivity.model_validate(
        {
            "id": "a2",
            "activityType": "extraction",
            "startedAt": "2026-06-01T00:00:00Z",
            "model": {"name": "extractor", "version": "9.9"},
            "confidence": 0.99,
        }
    )
    authoring.create_evidence(_evidence("e1", [_anchor("u1")]), first)
    outcome = authoring.create_evidence(_evidence("e2", [_anchor("u1")]), second)
    assert not outcome.created
    assert outcome.provenanceActivityIds == ["a1", "a2"]


def test_role_is_annotation_not_identity() -> None:
    """spec/04: role 'does NOT alter the default conjunctive semantics'."""
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1", role="definition")]), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u1", role="duty")]), _activity("a2")
    )
    assert not outcome.created
    assert outcome.evidenceId == "e1"


def test_resubmitting_the_same_activity_is_idempotent() -> None:
    """An activity is an event, not a counter: it must not accumulate duplicates."""
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1")]), _activity("a1"))
    outcome = authoring.create_evidence(_evidence("e2", [_anchor("u1")]), _activity("a1"))
    assert outcome.provenanceActivityIds == ["a1"]


# -- different basis --------------------------------------------------------
def test_different_stance_is_a_distinct_basis() -> None:
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1")], stance="supports"), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u1")], stance="refutes"), _activity("a2")
    )
    assert outcome.created and outcome.evidenceId == "e2"
    assert authoring.independent_evidence_count("r1") == 2


def test_different_selector_is_a_distinct_basis() -> None:
    """Selectors participate in evidence identity through the anchor set."""
    authoring = _ctx().require_authoring()
    span_a = {"type": "textPosition", "start": 0, "end": 10}
    span_b = {"type": "textPosition", "start": 20, "end": 30}
    authoring.create_evidence(_evidence("e1", [_anchor("u1", span_a)]), _activity("a1"))
    outcome = authoring.create_evidence(_evidence("e2", [_anchor("u1", span_b)]), _activity("a2"))
    assert outcome.created and outcome.evidenceId == "e2"


def test_absent_selector_differs_from_a_present_one() -> None:
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1")]), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u1", {"type": "textPosition", "start": 0, "end": 5})]),
        _activity("a2"),
    )
    assert outcome.created


def test_extra_anchor_is_a_distinct_basis() -> None:
    authoring = _ctx().require_authoring()
    authoring.create_evidence(_evidence("e1", [_anchor("u1")]), _activity("a1"))
    outcome = authoring.create_evidence(
        _evidence("e2", [_anchor("u1"), _anchor("u2")]), _activity("a2")
    )
    assert outcome.created, "a conjunctive basis over more units is a different basis"


def test_unknown_relation_is_rejected() -> None:
    authoring = _ctx().require_authoring()
    candidate = _evidence("e1", [_anchor("u1")])
    candidate.relationId = "does-not-exist"
    with pytest.raises(KeyError):
        authoring.create_evidence(candidate, _activity("a1"))
