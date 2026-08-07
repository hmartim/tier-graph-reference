"""Review event model."""

from __future__ import annotations

from datetime import datetime

from .common import ReviewStatus, TierModel


class ReviewEvent(TierModel):
    """A recorded editorial decision about a TIER-derived subject.

    Review events keep historical decisions registered even after a source-state
    transition withdraws support (see T04: historical evidence is retained).
    """

    id: str
    subjectId: str
    status: ReviewStatus
    reviewer: str | None = None
    decidedAt: datetime | None = None
    note: str | None = None
