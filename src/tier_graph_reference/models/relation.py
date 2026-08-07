"""Derived relation model.

A ``DerivedRelation`` is a proposition: source -> predicate -> target, plus
truth-conditional qualifiers. It deliberately has **no** temporal interval of
its own. Temporal admissibility is always derived through the grounding
provider from the relation's evidence; authoritative source intervals are never
copied here (a core invariant, verified by the conformance runner).
"""

from __future__ import annotations

from .common import ReviewStatus, TierModel
from .qualifier import RelationQualifier

#: Keys that would carry an authoritative temporal interval. R3 forbids these on a
#: ``DerivedRelation``; ``TierModel``'s ``extra="forbid"`` enforces it structurally,
#: and the conformance loader scans raw fixture JSON for them so that an authoring
#: mistake reports as a fixture error rather than an opaque ValidationError.
INTERVAL_KEYS: frozenset[str] = frozenset(
    {"validityInterval", "applicabilityInterval", "admissibleFrom", "admissibleTo", "interval"}
)

#: Canonical, identity-bearing qualifier dimensions in the reference profile.
#: All are treated as truth-conditional (see RelationIdentityService).
IDENTITY_BEARING_QUALIFIERS: tuple[str, ...] = (
    "polarity",
    "condition",
    "scope",
    "modality",
    "participantRoles",
)


class DerivedRelation(TierModel):
    """A time-independent derived relation between two entities."""

    id: str
    sourceEntityId: str
    predicate: str
    targetEntityId: str
    predicateFamily: str
    qualifiers: dict[str, RelationQualifier] = {}
    reviewStatus: ReviewStatus = ReviewStatus.PROPOSED
