"""Audit service.

Returns structured, machine-readable trails suitable for independent
inspection. Re-extraction accumulates provenance without duplicating evidence:
a single evidence occurrence may carry several provenance activities (see T08).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..grounding.base import TemporalGroundingProvider
from ..models import EXCLUDED_REVIEW_STATUSES
from ..store.base import TierStore
from .relation_state import RelationStateService


class AuditService:
    """Builds audit trails for relations and evidence."""

    def __init__(
        self,
        store: TierStore,
        grounding: TemporalGroundingProvider,
        relation_state: RelationStateService,
    ) -> None:
        self._store = store
        self._grounding = grounding
        self._relation_state = relation_state

    def evidence_audit_trail(
        self, evidence_id: str, at: datetime | None = None
    ) -> dict[str, Any]:
        evidence = self._store.require_evidence(evidence_id)
        siblings = [
            e
            for e in self._store.get_relation_evidence(evidence.relationId)
            if e.reviewStatus not in EXCLUDED_REVIEW_STATUSES
        ]
        trail: dict[str, Any] = {
            "evidenceId": evidence.id,
            "relationId": evidence.relationId,
            "evidenceRecordCount": len(siblings),
            "reviewStatus": evidence.reviewStatus.value,
            "provenanceActivityIds": list(evidence.provenanceActivityIds),
            "provenanceActivityCount": len(evidence.provenanceActivityIds),
            # Distinct evidential *bases*, keyed by EvidenceKey -- not a record
            # count. Two records sharing a key are one basis counted twice, which
            # is the corroboration inflation T08 exists to prevent.
            "independentEvidenceCount": len({e.identity_key for e in siblings}),
            "anchors": [anchor.model_dump(exclude_none=True) for anchor in evidence.anchors],
        }
        if at is not None:
            trail["admissibilityAt"] = self._grounding.evaluate_evidence(
                evidence, at
            ).model_dump()
        return trail

    def relation_audit_trail(
        self, relation_id: str, at: datetime | None = None
    ) -> dict[str, Any]:
        relation = self._store.require_relation(relation_id)
        evidence = self._store.get_relation_evidence(relation_id)
        trail: dict[str, Any] = {
            "relationId": relation.id,
            "relation": relation.model_dump(),
            "evidence": [e.model_dump(exclude_none=True) for e in evidence],
            "evidenceRecordCount": len(evidence),
            "reviewEvents": [ev.model_dump(exclude_none=True) for ev in
                             self._store.get_review_events(relation_id)],
        }
        if at is not None:
            trail["stateAt"] = self._relation_state.state_at(relation_id, at).model_dump()
        return trail

    def explain_relation_state(
        self, relation_id: str, at: datetime, observer_time: datetime | None = None
    ) -> dict[str, Any]:
        snapshot = self._relation_state.state_at(
            relation_id, at, observer_time=observer_time
        )
        breakdown: list[dict[str, Any]] = []
        for evidence in self._store.get_relation_evidence(relation_id):
            excluded = evidence.reviewStatus in EXCLUDED_REVIEW_STATUSES
            result = self._grounding.evaluate_evidence(evidence, at, observer_time)
            breakdown.append(
                {
                    "evidenceId": evidence.id,
                    "stance": evidence.stance.value,
                    "reviewStatus": evidence.reviewStatus.value,
                    "excludedByReview": excluded,
                    "admissible": result.admissible and not excluded,
                    "anchorResults": result.anchorResults,
                }
            )
        return {
            "relationId": relation_id,
            "state": snapshot.state.value,
            "supportingEvidenceIds": snapshot.supportingEvidenceIds,
            "refutingEvidenceIds": snapshot.refutingEvidenceIds,
            "evidenceBreakdown": breakdown,
        }
