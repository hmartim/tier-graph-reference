"""Relation identity comparison."""

from __future__ import annotations

from tier_graph_reference.models import DerivedRelation, IdentityDecision
from tier_graph_reference.services.identity import RelationIdentityService

_SERVICE = RelationIdentityService()


def _relation(rid: str, **qualifiers: dict) -> DerivedRelation:  # type: ignore[type-arg]
    return DerivedRelation.model_validate(
        {
            "id": rid,
            "sourceEntityId": "de-x",
            "predicate": "REQUIRES",
            "targetEntityId": "de-y",
            "predicateFamily": "normativeDependency",
            "qualifiers": {
                "polarity": {"status": "specified", "value": "positive"},
                **qualifiers,
            },
        }
    )


def test_unknown_vs_absent_is_unresolved() -> None:
    a = _relation("a", condition={"status": "absent"})
    b = _relation("b", condition={"status": "unknown"})
    result = _SERVICE.compare(a, b)
    assert result.decision is IdentityDecision.UNRESOLVED
    assert result.mergeAllowed is False
    assert result.blockingDimensions == ["condition"]
    assert result.reason == "unknown is not equivalent to absent"


def test_identical_qualifiers_are_equivalent() -> None:
    a = _relation("a", condition={"status": "absent"})
    b = _relation("b", condition={"status": "absent"})
    result = _SERVICE.compare(a, b)
    assert result.decision is IdentityDecision.EQUIVALENT
    assert result.mergeAllowed is True


def test_different_polarity_is_distinct() -> None:
    a = _relation("a")
    b = _relation("b")
    b.qualifiers["polarity"].value = "negative"
    result = _SERVICE.compare(a, b)
    assert result.decision is IdentityDecision.DISTINCT
    assert "polarity" in result.differingDimensions


def test_different_predicate_is_distinct() -> None:
    a = _relation("a")
    b = _relation("b")
    b.predicate = "DEPENDS_ON"
    result = _SERVICE.compare(a, b)
    assert result.decision is IdentityDecision.DISTINCT
