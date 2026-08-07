"""Time-indexed projection service.

The projection at ``(at, policy)`` contains exactly the relations whose computed
evidential state at ``at`` is admitted by the policy. Authoritative source
intervals are never copied onto projected relations.
"""

from __future__ import annotations

from datetime import datetime

from ..models import ProjectedRelation
from ..store.base import TierStore
from .relation_state import RelationStateService


class ProjectionService:
    """Builds the set of relations admitted at a time under a policy."""

    def __init__(self, store: TierStore, relation_state: RelationStateService) -> None:
        self._store = store
        self._relation_state = relation_state

    def project(
        self, at: datetime, policy_id: str, observer_time: datetime | None = None
    ) -> list[ProjectedRelation]:
        policy = self._store.require_policy(policy_id)
        projected: list[ProjectedRelation] = []
        for relation in self._store.list_relations():
            snapshot = self._relation_state.state_at(
                relation.id,
                at,
                observer_time=observer_time,
                grounding_reviews=policy.grounding_review_statuses(),
            )
            if policy.admits(snapshot.state):
                projected.append(
                    ProjectedRelation(
                        relationId=relation.id,
                        sourceEntityId=relation.sourceEntityId,
                        predicate=relation.predicate,
                        targetEntityId=relation.targetEntityId,
                        state=snapshot.state,
                    )
                )
        return projected
