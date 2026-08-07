"""Evidence authoring: create-or-append under the evidence identity key.

Re-running an extraction over the same relation, anchors, and stance must **not**
create a second evidence record. Doing so would inflate apparent corroboration:
one basis counted twice reads as two independent bases. Instead the existing
occurrence gains a provenance activity (spec/04 §4.4, conformance case T08).

This is the only write path in the reference implementation that is not a plain
``put_*``; everything else in ``TierStore`` is deliberately dumb storage.
"""

from __future__ import annotations

from ..models import EvidenceKey, ProvenanceActivity, RelationEvidence, TierModel
from ..store.base import TierStore, WritableTierStore


class EvidenceSubmissionOutcome(TierModel):
    """What one ``createEvidence`` submission did."""

    evidenceId: str
    #: False when an occurrence with the same EvidenceKey already existed.
    created: bool
    #: The normative contract calls for a duplicate key to be *detected* and
    #: flagged (HTTP 409 at the API boundary); this is that signal offline.
    duplicateKeyDetected: bool
    provenanceActivityIds: list[str]


class EvidenceAuthoringService:
    """Creates evidence records, deduplicating by :class:`EvidenceKey`."""

    def __init__(self, store: WritableTierStore) -> None:
        self._store = store

    @staticmethod
    def supports(store: TierStore) -> bool:
        return isinstance(store, WritableTierStore)

    def create_evidence(
        self,
        candidate: RelationEvidence,
        activity: ProvenanceActivity | None = None,
    ) -> EvidenceSubmissionOutcome:
        """Create the record, or append provenance to the matching occurrence."""
        self._store.require_relation(candidate.relationId)
        existing = self.find_by_key(candidate.identity_key)

        if existing is None:
            record = candidate.model_copy(deep=True)
            if activity is not None:
                self._store.put_provenance_activity(activity)
                if activity.id not in record.provenanceActivityIds:
                    record.provenanceActivityIds = [*record.provenanceActivityIds, activity.id]
            self._store.put_evidence(record)
            return EvidenceSubmissionOutcome(
                evidenceId=record.id,
                created=True,
                duplicateKeyDetected=False,
                provenanceActivityIds=list(record.provenanceActivityIds),
            )

        # Duplicate key: keep the original occurrence and its identifier, and
        # append the new activity. The candidate's own id is discarded -- a new
        # identifier for the same basis is precisely the duplication forbidden here.
        if activity is not None:
            self._store.put_provenance_activity(activity)
            if activity.id not in existing.provenanceActivityIds:
                # Re-submitting the *same* activity id is idempotent rather than
                # duplicating: an activity is an event, not a counter.
                existing.provenanceActivityIds = [
                    *existing.provenanceActivityIds,
                    activity.id,
                ]
                self._store.put_evidence(existing)
        return EvidenceSubmissionOutcome(
            evidenceId=existing.id,
            created=False,
            duplicateKeyDetected=True,
            provenanceActivityIds=list(existing.provenanceActivityIds),
        )

    def find_by_key(self, key: EvidenceKey) -> RelationEvidence | None:
        """The stored occurrence with this identity key, if any."""
        for evidence in self._store.get_relation_evidence(key.relationId):
            if evidence.identity_key == key:
                return evidence
        return None

    def independent_evidence_count(self, relation_id: str) -> int:
        """Distinct evidential bases for a relation.

        Counts distinct :class:`EvidenceKey` values, not records: two records
        sharing a key would be the same basis counted twice.
        """
        return len(
            {evidence.identity_key for evidence in self._store.get_relation_evidence(relation_id)}
        )
