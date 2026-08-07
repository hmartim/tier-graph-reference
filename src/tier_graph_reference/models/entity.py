"""Derived entity model."""

from __future__ import annotations

from .common import ReviewStatus, TierModel


class DerivedEntity(TierModel):
    """A TIER-derived entity (concept, event, legal category, ...).

    The identifier is opaque and stable; ``canonicalLabel`` is a mutable display
    label and MUST NOT be used to derive identity.
    """

    id: str
    canonicalLabel: str
    entityType: str
    reviewStatus: ReviewStatus = ReviewStatus.PROPOSED
