"""Grounding-profile models and the admissibility result.

These describe the *external* grounding facts a temporal grounding provider
owns. In the fixture provider they come from ``profile-fixture.json``; in the
SAT-Graph adapter they are derived from the SAT-Graph API. The core treats them
abstractly and never persists their intervals onto TIER-derived objects.
"""

from __future__ import annotations

from datetime import datetime

from .common import TierModel


class TemporalGroundingProfile(TierModel):
    """Metadata identifying a grounding profile."""

    id: str
    name: str | None = None
    version: str
    intervalConvention: str = "[from,to)"
    authorityNote: str | None = None


class GroundingEvidenceUnit(TierModel):
    """Maps an evidence unit to the source state that owns it."""

    id: str
    ownerSourceStateId: str


class GroundingSourceState(TierModel):
    """An external source state with a half-open admissibility interval.

    ``admissibleTo = None`` means open-ended. ``publishedAt`` is informational
    and MUST NOT control admissibility (see T09: publication does not replace the
    applicability boundary). ``transitionRef`` points at the provenance of the
    boundary (e.g. the action that ended admissibility, see T04).
    """

    id: str
    admissibleFrom: datetime
    admissibleTo: datetime | None = None
    publishedAt: datetime | None = None
    transitionRef: str | None = None

    def admissible_at(self, at: datetime) -> bool:
        """Half-open membership test: ``admissibleFrom <= at < admissibleTo``."""
        if at < self.admissibleFrom:
            return False
        return self.admissibleTo is None or at < self.admissibleTo


class ProfileFixture(TierModel):
    """The full contents of a ``profile-fixture.json`` document."""

    profile: TemporalGroundingProfile
    evidenceUnits: list[GroundingEvidenceUnit] = []
    sourceStates: list[GroundingSourceState] = []


class AdmissibilityResult(TierModel):
    """The outcome of evaluating one evidence record's admissibility at a time.

    ``admissible`` is the conjunction over ``anchorResults`` (every anchor's
    owning source state must be admissible).
    """

    at: str
    admissible: bool
    anchorResults: dict[str, bool] = {}
