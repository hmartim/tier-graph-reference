"""The TIER storage boundary.

A ``TierStore`` holds **only TIER-derived objects**: entities, relations,
evidence, provenance, review events, and admission policies. It never holds a
source substrate (no ``item`` / ``version`` / ``text_unit`` / ``action`` and no
applicability/validity interval tables). Temporal admissibility is not stored
here; it is answered by a ``TemporalGroundingProvider``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from ..models import (
    AdmissionPolicy,
    DerivedEntity,
    DerivedRelation,
    ProvenanceActivity,
    RelationEvidence,
    ReviewEvent,
)

Filters = Mapping[str, Any] | None


class TierStore(ABC):
    """Read interface over TIER-derived objects."""

    # -- entities ----------------------------------------------------------
    @abstractmethod
    def get_entity(self, entity_id: str) -> DerivedEntity | None: ...

    @abstractmethod
    def list_entities(self, filters: Filters = None) -> list[DerivedEntity]: ...

    # -- relations ---------------------------------------------------------
    @abstractmethod
    def get_relation(self, relation_id: str) -> DerivedRelation | None: ...

    @abstractmethod
    def list_relations(self, filters: Filters = None) -> list[DerivedRelation]: ...

    # -- evidence ----------------------------------------------------------
    @abstractmethod
    def get_evidence(self, evidence_id: str) -> RelationEvidence | None: ...

    @abstractmethod
    def list_evidence(self, filters: Filters = None) -> list[RelationEvidence]: ...

    @abstractmethod
    def get_relation_evidence(self, relation_id: str) -> list[RelationEvidence]: ...

    @abstractmethod
    def get_relations_by_evidence_unit(
        self, profile_id: str, evidence_unit_id: str
    ) -> list[DerivedRelation]:
        """All relations with an evidence anchor on ``(profile_id, evidence_unit_id)``.

        This is a time-independent reverse lookup: it does not collapse distinct
        predicate families (see T03).
        """

    # -- provenance --------------------------------------------------------
    @abstractmethod
    def get_provenance_activity(self, activity_id: str) -> ProvenanceActivity | None: ...

    @abstractmethod
    def list_provenance_activities(self, subject_id: str | None = None) -> list[ProvenanceActivity]:
        """Provenance activities, optionally scoped to those referenced by one evidence id."""

    # -- review events -----------------------------------------------------
    @abstractmethod
    def get_review_events(self, subject_id: str | None = None) -> list[ReviewEvent]: ...

    # -- admission policies ------------------------------------------------
    @abstractmethod
    def get_policy(self, policy_id: str) -> AdmissionPolicy | None: ...

    @abstractmethod
    def list_policies(self) -> list[AdmissionPolicy]: ...

    # -- convenience -------------------------------------------------------
    def require_relation(self, relation_id: str) -> DerivedRelation:
        relation = self.get_relation(relation_id)
        if relation is None:
            raise KeyError(f"unknown relation: {relation_id}")
        return relation

    def require_evidence(self, evidence_id: str) -> RelationEvidence:
        evidence = self.get_evidence(evidence_id)
        if evidence is None:
            raise KeyError(f"unknown evidence: {evidence_id}")
        return evidence

    def require_policy(self, policy_id: str) -> AdmissionPolicy:
        policy = self.get_policy(policy_id)
        if policy is None:
            raise KeyError(f"unknown admission policy: {policy_id}")
        return policy


class WritableTierStore(TierStore):
    """Optional authoring interface for populating a store."""

    @abstractmethod
    def put_entity(self, entity: DerivedEntity) -> None: ...

    @abstractmethod
    def put_relation(self, relation: DerivedRelation) -> None: ...

    @abstractmethod
    def put_evidence(self, evidence: RelationEvidence) -> None: ...

    @abstractmethod
    def put_provenance_activity(self, activity: ProvenanceActivity) -> None: ...

    @abstractmethod
    def put_review_event(self, event: ReviewEvent) -> None: ...

    @abstractmethod
    def put_policy(self, policy: AdmissionPolicy) -> None: ...
