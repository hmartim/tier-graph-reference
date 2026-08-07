"""Fixture grounding provider: half-open intervals and conjunctive evidence."""

from __future__ import annotations

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import (
    EvidenceAnchor,
    EvidenceUnitRef,
    RelationEvidence,
    parse_instant,
)

_PROFILE = {
    "profile": {"id": "p", "version": "1", "intervalConvention": "[from,to)"},
    "evidenceUnits": [
        {"id": "u-def", "ownerSourceStateId": "s-def"},
        {"id": "u-duty", "ownerSourceStateId": "s-duty"},
    ],
    "sourceStates": [
        {
            "id": "s-def",
            "admissibleFrom": "2024-01-01T00:00:00Z",
            "admissibleTo": "2025-01-01T00:00:00Z",
        },
        {"id": "s-duty", "admissibleFrom": "2024-01-01T00:00:00Z", "admissibleTo": None},
    ],
}


def _provider() -> FixtureGroundingProvider:
    return FixtureGroundingProvider.from_dict(_PROFILE)


def test_half_open_interval_excludes_upper_bound() -> None:
    provider = _provider()
    # admissibleTo is exclusive
    assert provider.evaluate_source_state("s-def", parse_instant("2024-12-31T23:59:59Z"))
    assert not provider.evaluate_source_state("s-def", parse_instant("2025-01-01T00:00:00Z"))
    # admissibleFrom is inclusive
    assert provider.evaluate_source_state("s-def", parse_instant("2024-01-01T00:00:00Z"))


def test_conjunctive_evidence_needs_every_anchor() -> None:
    provider = _provider()
    evidence = RelationEvidence(
        id="e",
        relationId="r",
        anchors=[
            EvidenceAnchor(evidenceUnit=EvidenceUnitRef(profileId="p", evidenceUnitId="u-def")),
            EvidenceAnchor(evidenceUnit=EvidenceUnitRef(profileId="p", evidenceUnitId="u-duty")),
        ],
    )
    both = provider.evaluate_evidence(evidence, parse_instant("2024-06-01T00:00:00Z"))
    assert both.admissible
    assert both.anchorResults == {"u-def": True, "u-duty": True}

    one = provider.evaluate_evidence(evidence, parse_instant("2025-06-01T00:00:00Z"))
    assert not one.admissible
    assert one.anchorResults == {"u-def": False, "u-duty": True}
