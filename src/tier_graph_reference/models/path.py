"""Path result models.

These follow the normative ``schemas/query/grounded-path.schema.json`` and
``path-step.schema.json``. The earlier shapes carried only a flat list of
relation identifiers, which dropped each step's evidential state: under a
recall-oriented policy a relation admitted while *refuted* became
indistinguishable from a supported one. Admission by a policy is not evidential
support, and the two must remain separable in the answer.
"""

from __future__ import annotations

from .common import TierModel
from .projection import EvidentialStateSnapshot


class PathStep(TierModel):
    """One traversed relation, with the evidential state it carried at the time."""

    ordinal: int
    relationId: str
    fromEntityId: str
    toEntityId: str
    #: The full snapshot, not a bare label: a consumer deciding whether to rely on
    #: this step needs the supporting and refuting evidence behind the state.
    evidentialState: EvidentialStateSnapshot
    admitted: bool
    direction: str | None = None
    exclusionReason: str | None = None


class GroundedPath(TierModel):
    """A path evaluated under one profile, query time, and admission policy.

    ``admissible`` means **every step was admitted by the policy** -- nothing
    more. A recall-oriented policy may admit refuted or contested relations, so
    an admissible path is not necessarily a positively supported one. A consumer
    requiring positive support must check that every step's
    ``evidentialState.state`` is ``supported``; :attr:`is_supported` computes it.
    """

    id: str
    sourceEntityId: str
    targetEntityId: str
    steps: list[PathStep]
    profileId: str
    queryTime: str
    policyId: str
    admissible: bool

    @property
    def relation_ids(self) -> list[str]:
        """The traversed relations, in order. Derived; not part of the contract."""
        return [step.relationId for step in self.steps]

    @property
    def is_supported(self) -> bool:
        """Whether every step is positively supported, not merely admitted."""
        return bool(self.steps) and all(
            step.evidentialState.state.value == "supported" for step in self.steps
        )


class ExclusionExplanation(TierModel):
    """Why a relation could not participate in a path at the query time.

    ``reasonCode`` is a stable, machine-readable code (e.g.
    ``EVIDENCE_SOURCE_STATE_NOT_ADMISSIBLE``); ``evidenceId`` points at the
    evidence record whose grounding failed, when applicable.
    """

    relationId: str
    reasonCode: str
    evidenceId: str | None = None
    detail: str | None = None
