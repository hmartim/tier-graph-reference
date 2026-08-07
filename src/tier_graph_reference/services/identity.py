"""Relation identity comparison.

Identity-bearing signals are: source, predicate, target, polarity, and the
profile-declared truth-conditional qualifiers. Labels never define identity.

Rules (see T06):

- ``unknown`` is not ``absent``;
- any unresolved (``unknown``) identity-bearing qualifier blocks automatic
  equivalence and yields ``unresolved``.
"""

from __future__ import annotations

from ..models import (
    IDENTITY_BEARING_QUALIFIERS,
    DerivedRelation,
    IdentityDecision,
    QualifierStatus,
    RelationQualifier,
    TierModel,
)

_ABSENT = RelationQualifier(status=QualifierStatus.ABSENT)


class IdentityComparison(TierModel):
    """The structured result of comparing two relation candidates."""

    decision: IdentityDecision
    mergeAllowed: bool
    blockingDimensions: list[str] = []
    differingDimensions: list[str] = []
    reason: str


class RelationIdentityService:
    """Compares two relation candidates for identity, conservatively."""

    def __init__(self, identity_bearing: tuple[str, ...] = IDENTITY_BEARING_QUALIFIERS) -> None:
        self._dimensions = identity_bearing

    def compare(
        self, candidate_a: DerivedRelation, candidate_b: DerivedRelation
    ) -> IdentityComparison:
        structural_diffs = self._structural_diffs(candidate_a, candidate_b)
        blocking: list[str] = []
        differing: list[str] = list(structural_diffs)

        for dimension in self._dimensions:
            qa = candidate_a.qualifiers.get(dimension, _ABSENT)
            qb = candidate_b.qualifiers.get(dimension, _ABSENT)
            if qa.is_unknown or qb.is_unknown:
                blocking.append(dimension)
            elif not self._qualifiers_equal(qa, qb):
                differing.append(dimension)

        if blocking:
            return IdentityComparison(
                decision=IdentityDecision.UNRESOLVED,
                mergeAllowed=False,
                blockingDimensions=blocking,
                differingDimensions=differing,
                reason=self._blocking_reason(candidate_a, candidate_b, blocking),
            )
        if differing:
            return IdentityComparison(
                decision=IdentityDecision.DISTINCT,
                mergeAllowed=False,
                differingDimensions=differing,
                reason=f"identity-bearing dimensions differ: {', '.join(differing)}",
            )
        return IdentityComparison(
            decision=IdentityDecision.EQUIVALENT,
            mergeAllowed=True,
            reason="all identity-bearing dimensions match",
        )

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _structural_diffs(a: DerivedRelation, b: DerivedRelation) -> list[str]:
        diffs: list[str] = []
        if a.sourceEntityId != b.sourceEntityId:
            diffs.append("source")
        if a.predicate != b.predicate:
            diffs.append("predicate")
        if a.targetEntityId != b.targetEntityId:
            diffs.append("target")
        return diffs

    @staticmethod
    def _qualifiers_equal(a: RelationQualifier, b: RelationQualifier) -> bool:
        if a.status is not b.status:
            return False
        return a.value == b.value

    def _blocking_reason(
        self, a: DerivedRelation, b: DerivedRelation, blocking: list[str]
    ) -> str:
        # Special-case the canonical unknown-vs-absent situation for a stable message.
        for dimension in blocking:
            qa = a.qualifiers.get(dimension, _ABSENT)
            qb = b.qualifiers.get(dimension, _ABSENT)
            statuses = {qa.status, qb.status}
            if QualifierStatus.UNKNOWN in statuses and QualifierStatus.ABSENT in statuses:
                return "unknown is not equivalent to absent"
        return f"unresolved identity-bearing qualifier(s): {', '.join(blocking)}"
