"""Pi_review: which review statuses may ground admission.

An admission policy is the pair ``⟨Π_review, A_state⟩``. The reference used to
implement only ``A_state``, with ``Π_review`` frozen as a module constant that
excluded ``rejected``/``superseded`` and silently admitted ``proposed``. That is
not a neutral default: it decides whether unreviewed extraction may ground a
legal answer, which belongs in the policy, not in the core.

The split enforced here:

- **core invariant** — ``rejected`` and ``superseded`` never ground admission,
  under any policy. They remain stored and auditable.
- **policy choice** — ``{accepted}`` (reviewed evidence) or
  ``{proposed, accepted}`` (exploratory).
"""

from __future__ import annotations

from typing import Any

import pytest

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import (
    AdmissionPolicy,
    EvidentialState,
    ReviewStatus,
    parse_instant,
)
from tier_graph_reference.services import ServiceContext
from tier_graph_reference.store.memory import MemoryTierStore

_AT = "2024-01-01T00:00:00Z"


def _policy(policy_id: str, minimum: str | None) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "id": policy_id,
        "name": policy_id,
        "admittedStates": ["supported"],
    }
    if minimum is not None:
        policy["minimumReviewStatus"] = minimum
    return policy


_INPUT: dict[str, Any] = {
    "entities": [
        {"id": "de-a", "canonicalLabel": "A", "entityType": "concept", "reviewStatus": "accepted"},
        {"id": "de-b", "canonicalLabel": "B", "entityType": "concept", "reviewStatus": "accepted"},
    ],
    "relations": [
        {"id": "r1", "sourceEntityId": "de-a", "predicate": "P", "targetEntityId": "de-b",
         "predicateFamily": "procedural", "reviewStatus": "accepted"},
    ],
    "evidence": [
        # The only support is an unreviewed extraction.
        {"id": "e-proposed", "relationId": "r1",
         "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u"}}],
         "stance": "supports", "reviewStatus": "proposed"},
    ],
    "admissionPolicies": [
        _policy("reviewed", "accepted"),
        _policy("exploratory", "proposed"),
        _policy("unset", None),
    ],
}
_PROFILE = {
    "profile": {"id": "p", "version": "1"},
    "evidenceUnits": [{"id": "u", "ownerSourceStateId": "s"}],
    "sourceStates": [{"id": "s", "admissibleFrom": "2020-01-01T00:00:00Z", "admissibleTo": None}],
}


def _ctx() -> ServiceContext:
    return ServiceContext.build(
        MemoryTierStore.from_input(_INPUT), FixtureGroundingProvider.from_dict(_PROFILE)
    )


# -- the core invariant no policy may relax ---------------------------------
@pytest.mark.parametrize("minimum", [None, "proposed", "accepted", "rejected", "superseded"])
def test_rejected_and_superseded_never_ground_admission(minimum: str) -> None:
    policy = AdmissionPolicy.model_validate(_policy("p", minimum))
    grounding = policy.grounding_review_statuses()
    assert ReviewStatus.REJECTED not in grounding
    assert ReviewStatus.SUPERSEDED not in grounding


def test_a_policy_cannot_nominate_a_non_grounding_floor() -> None:
    """Naming `rejected` as the floor admits nothing, rather than admitting it."""
    policy = AdmissionPolicy.model_validate(_policy("p", "rejected"))
    assert policy.grounding_review_statuses() == frozenset()


# -- the policy choice -------------------------------------------------------
def test_reviewed_policy_does_not_admit_proposed_evidence() -> None:
    projected = _ctx().projection.project(parse_instant(_AT), "reviewed")
    assert projected == [], "unreviewed extraction must not ground a reviewed-evidence policy"


def test_exploratory_policy_admits_proposed_evidence() -> None:
    projected = _ctx().projection.project(parse_instant(_AT), "exploratory")
    assert [(p.relationId, p.state) for p in projected] == [("r1", EvidentialState.SUPPORTED)]


def test_unset_minimum_admits_any_grounding_status() -> None:
    """Omitting the floor is the permissive reading, and must be chosen knowingly."""
    projected = _ctx().projection.project(parse_instant(_AT), "unset")
    assert [p.relationId for p in projected] == ["r1"]


def test_the_public_fixtures_declare_a_reviewed_evidence_policy() -> None:
    """The executed results must not depend on the permissive default."""
    from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest

    for case in load_manifest(default_fixtures_dir()).cases:
        for raw in case.input.get("admissionPolicies", []):
            assert raw.get("minimumReviewStatus") == "accepted", (
                f"{case.case_id} policy {raw['id']!r} leaves Pi_review implicit"
            )


def test_every_fixture_evidence_record_is_accepted() -> None:
    """So the ten reported results are independent of the proposed question."""
    from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest

    for case in load_manifest(default_fixtures_dir()).cases:
        for evidence in case.input.get("evidence", []):
            assert evidence.get("reviewStatus") == "accepted", (
                f"{case.case_id}: evidence {evidence['id']!r} is not accepted"
            )
