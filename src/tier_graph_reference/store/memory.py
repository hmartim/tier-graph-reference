"""In-memory TIER store. The default store for conformance and tests."""

from __future__ import annotations

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
from .base import Filters, WritableTierStore


def _matches(obj: Any, filters: Filters) -> bool:
    if not filters:
        return True
    return all(getattr(obj, key, None) == expected for key, expected in filters.items())


class MemoryTierStore(WritableTierStore):
    """A dictionary-backed store of TIER-derived objects."""

    def __init__(self) -> None:
        self._entities: dict[str, DerivedEntity] = {}
        self._relations: dict[str, DerivedRelation] = {}
        self._evidence: dict[str, RelationEvidence] = {}
        self._activities: dict[str, ProvenanceActivity] = {}
        self._reviews: list[ReviewEvent] = []
        self._policies: dict[str, AdmissionPolicy] = {}

    # -- loading -----------------------------------------------------------
    @classmethod
    def from_input(cls, data: Mapping[str, Any]) -> MemoryTierStore:
        """Build a store from a fixture ``input.json`` document (TIER objects only)."""
        store = cls()
        for raw in data.get("entities", []):
            store.put_entity(DerivedEntity.model_validate(raw))
        for raw in data.get("relations", []):
            store.put_relation(DerivedRelation.model_validate(raw))
        for raw in data.get("evidence", []):
            store.put_evidence(RelationEvidence.model_validate(raw))
        for raw in data.get("provenanceActivities", []):
            store.put_provenance_activity(ProvenanceActivity.model_validate(raw))
        for raw in data.get("reviewEvents", []):
            store.put_review_event(ReviewEvent.model_validate(raw))
        for raw in data.get("admissionPolicies", []):
            store.put_policy(AdmissionPolicy.model_validate(raw))
        return store

    # -- entities ----------------------------------------------------------
    def get_entity(self, entity_id: str) -> DerivedEntity | None:
        return self._entities.get(entity_id)

    def list_entities(self, filters: Filters = None) -> list[DerivedEntity]:
        return [e for e in self._entities.values() if _matches(e, filters)]

    # -- relations ---------------------------------------------------------
    def get_relation(self, relation_id: str) -> DerivedRelation | None:
        return self._relations.get(relation_id)

    def list_relations(self, filters: Filters = None) -> list[DerivedRelation]:
        return [r for r in self._relations.values() if _matches(r, filters)]

    # -- evidence ----------------------------------------------------------
    def get_evidence(self, evidence_id: str) -> RelationEvidence | None:
        return self._evidence.get(evidence_id)

    def list_evidence(self, filters: Filters = None) -> list[RelationEvidence]:
        return [e for e in self._evidence.values() if _matches(e, filters)]

    def get_relation_evidence(self, relation_id: str) -> list[RelationEvidence]:
        return [e for e in self._evidence.values() if e.relationId == relation_id]

    def get_relations_by_evidence_unit(
        self, profile_id: str, evidence_unit_id: str
    ) -> list[DerivedRelation]:
        relation_ids: list[str] = []
        for evidence in self._evidence.values():
            for anchor in evidence.anchors:
                ref = anchor.evidenceUnit
                if ref.profileId == profile_id and ref.evidenceUnitId == evidence_unit_id:
                    if evidence.relationId not in relation_ids:
                        relation_ids.append(evidence.relationId)
                    break
        return [self._relations[rid] for rid in relation_ids if rid in self._relations]

    # -- provenance --------------------------------------------------------
    def get_provenance_activity(self, activity_id: str) -> ProvenanceActivity | None:
        return self._activities.get(activity_id)

    def list_provenance_activities(
        self, subject_id: str | None = None
    ) -> list[ProvenanceActivity]:
        if subject_id is None:
            return list(self._activities.values())
        evidence = self._evidence.get(subject_id)
        if evidence is None:
            return []
        return [
            self._activities[aid]
            for aid in evidence.provenanceActivityIds
            if aid in self._activities
        ]

    # -- review events -----------------------------------------------------
    def get_review_events(self, subject_id: str | None = None) -> list[ReviewEvent]:
        if subject_id is None:
            return list(self._reviews)
        return [event for event in self._reviews if event.subjectId == subject_id]

    # -- admission policies ------------------------------------------------
    def get_policy(self, policy_id: str) -> AdmissionPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self) -> list[AdmissionPolicy]:
        return list(self._policies.values())

    # -- authoring ---------------------------------------------------------
    def put_entity(self, entity: DerivedEntity) -> None:
        self._entities[entity.id] = entity

    def put_relation(self, relation: DerivedRelation) -> None:
        self._relations[relation.id] = relation

    def put_evidence(self, evidence: RelationEvidence) -> None:
        self._evidence[evidence.id] = evidence

    def put_provenance_activity(self, activity: ProvenanceActivity) -> None:
        self._activities[activity.id] = activity

    def put_review_event(self, event: ReviewEvent) -> None:
        self._reviews.append(event)

    def put_policy(self, policy: AdmissionPolicy) -> None:
        self._policies[policy.id] = policy
