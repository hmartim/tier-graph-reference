"""Relation evidential-state computation."""

from __future__ import annotations

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import EvidentialState, parse_instant
from tier_graph_reference.services.relation_state import RelationStateService
from tier_graph_reference.store.memory import MemoryTierStore

_PROFILE = {
    "profile": {"id": "p", "version": "1"},
    "evidenceUnits": [{"id": "u", "ownerSourceStateId": "s"}],
    "sourceStates": [{"id": "s", "admissibleFrom": "2020-01-01T00:00:00Z", "admissibleTo": None}],
}


def _store(*stances: str) -> MemoryTierStore:
    evidence = [
        {
            "id": f"e{i}",
            "relationId": "r",
            "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u"}}],
            "stance": stance,
            "reviewStatus": "accepted",
        }
        for i, stance in enumerate(stances)
    ]
    return MemoryTierStore.from_input(
        {
            "relations": [
                {
                    "id": "r",
                    "sourceEntityId": "a",
                    "predicate": "P",
                    "targetEntityId": "b",
                    "predicateFamily": "fam",
                    "reviewStatus": "accepted",
                }
            ],
            "evidence": evidence,
        }
    )


def _state(*stances: str) -> EvidentialState:
    service = RelationStateService(_store(*stances), FixtureGroundingProvider.from_dict(_PROFILE))
    return service.state_at("r", parse_instant("2021-01-01T00:00:00Z")).state


def test_supported() -> None:
    assert _state("supports") is EvidentialState.SUPPORTED


def test_refuted() -> None:
    assert _state("refutes") is EvidentialState.REFUTED


def test_contested() -> None:
    assert _state("supports", "refutes") is EvidentialState.CONTESTED


def test_unsupported_when_no_evidence() -> None:
    assert _state() is EvidentialState.UNSUPPORTED


def test_unsupported_before_admissibility() -> None:
    service = RelationStateService(_store("supports"), FixtureGroundingProvider.from_dict(_PROFILE))
    early = service.state_at("r", parse_instant("2019-01-01T00:00:00Z"))
    assert early.state is EvidentialState.UNSUPPORTED
