"""Admission policy model.

An admission policy is the pair ``π = ⟨Π_review, A_state⟩``: which review
statuses may ground admission, and which evidential states admit a relation.
The reference previously implemented only the second half, leaving Π_review as
a hard-coded module constant that no policy could vary.
"""

from __future__ import annotations

from .common import EvidentialState, ReviewStatus, TierModel

#: Review statuses that MAY ground admission, in increasing order of strength.
#: ``rejected`` and ``superseded`` are absent by construction: they are a **core**
#: invariant, not a policy dial. Such records remain stored and auditable, but
#: never ground a relation under any policy.
GROUNDING_REVIEW_STATUSES: tuple[ReviewStatus, ...] = (
    ReviewStatus.PROPOSED,
    ReviewStatus.ACCEPTED,
)


class AdmissionPolicy(TierModel):
    """Selects which evidence and which evidential states enter a projection.

    ``admittedStates`` is ``A_state``: a relation is admitted when its computed
    evidential state at ``t`` is in this set.

    ``minimumReviewStatus`` is ``Π_review``, expressed as a floor over
    :data:`GROUNDING_REVIEW_STATUSES`. Omitting it admits any grounding status,
    i.e. ``{proposed, accepted}``; setting it to ``accepted`` yields a
    reviewed-evidence policy admitting ``{accepted}`` only. Whether unreviewed
    extraction may ground a legal answer is a deliberate deployment choice, so
    it belongs in the policy rather than in a default buried in the core.
    """

    id: str
    name: str | None = None
    admittedStates: list[EvidentialState]
    minimumReviewStatus: ReviewStatus | None = None

    def admits(self, state: EvidentialState) -> bool:
        """Whether a relation in this evidential state enters the projection."""
        return state in self.admittedStates

    def grounding_review_statuses(self) -> frozenset[ReviewStatus]:
        """The Π_review this policy declares.

        Never includes ``rejected`` or ``superseded``: those are excluded by the
        core invariant, which no policy may relax.
        """
        if self.minimumReviewStatus is None:
            return frozenset(GROUNDING_REVIEW_STATUSES)
        if self.minimumReviewStatus not in GROUNDING_REVIEW_STATUSES:
            # A policy may not nominate a non-grounding status as its floor.
            return frozenset()
        floor = GROUNDING_REVIEW_STATUSES.index(self.minimumReviewStatus)
        return frozenset(GROUNDING_REVIEW_STATUSES[floor:])

    def admits_review(self, status: ReviewStatus) -> bool:
        return status in self.grounding_review_statuses()
