"""Result models for evidential state, relation history, and projections."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from .common import EvidentialState, TierModel


class EvidentialStateSnapshot(TierModel):
    """The evidential state of one relation at one query time under one profile.

    Field names follow the normative
    ``schemas/query/evidential-state-snapshot.schema.json``. ``queryTime`` was
    previously spelled ``at``, which the schema does not permit; the snapshot is
    embedded in ``PathStep``, so a divergence here silently propagated into every
    path result.

    This describes *registered evidence* under one profile and time. It is not a
    declaration of domain truth.
    """

    relationId: str
    profileId: str
    queryTime: str
    state: EvidentialState
    supportingEvidenceIds: list[str] = []
    refutingEvidenceIds: list[str] = []
    observerTime: str | None = None
    policyId: str | None = None


class RelationHistoryEntry(TierModel):
    """One period of stable evidential state within a relation's history.

    ``to = None`` marks an open-ended final period. The interval is a *derived*
    read of the grounding boundaries; it is never persisted on the relation.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_: str = Field(alias="from")
    to: str | None = None
    state: EvidentialState
    supportingEvidenceIds: list[str] = []
    refutingEvidenceIds: list[str] = []


class ProjectedRelation(TierModel):
    """A relation admitted into a time-indexed projection under a policy.

    It carries the identity of the relation and its computed evidential state at
    the projection time. It deliberately carries **no** temporal interval.
    """

    relationId: str
    sourceEntityId: str
    predicate: str
    targetEntityId: str
    state: EvidentialState
