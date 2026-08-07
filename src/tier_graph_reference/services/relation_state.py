"""Relation evidential-state service.

For one relation at one time, the state is computed from the *admissible*
evidence records (rejected/superseded evidence is excluded by default):

- supporting only  -> ``supported``
- refuting only    -> ``refuted``
- both             -> ``contested``
- neither          -> ``unsupported``

These are evidential states, not domain truth.
"""

from __future__ import annotations

from datetime import datetime

from ..grounding.base import TemporalGroundingProvider
from ..models import (
    EXCLUDED_REVIEW_STATUSES,
    EvidentialState,
    EvidentialStateSnapshot,
    RelationEvidence,
    RelationHistoryEntry,
    ReviewStatus,
    Stance,
    iso_z,
)
from ..store.base import TierStore


class RelationStateService:
    """Computes evidential state and history for relations."""

    def __init__(self, store: TierStore, grounding: TemporalGroundingProvider) -> None:
        self._store = store
        self._grounding = grounding

    # -- point-in-time -----------------------------------------------------
    def state_at(
        self,
        relation_id: str,
        at: datetime,
        *,
        at_label: str | None = None,
        observer_time: datetime | None = None,
        grounding_reviews: frozenset[ReviewStatus] | None = None,
    ) -> EvidentialStateSnapshot:
        """``grounding_reviews`` is the policy's Pi_review; ``None`` means the
        core invariant (any status except ``rejected``/``superseded``)."""
        self._store.require_relation(relation_id)
        supporting: list[str] = []
        refuting: list[str] = []
        for evidence in self._active_evidence(relation_id, grounding_reviews):
            result = self._grounding.evaluate_evidence(evidence, at, observer_time)
            if not result.admissible:
                continue
            if evidence.stance is Stance.SUPPORTS:
                supporting.append(evidence.id)
            else:
                refuting.append(evidence.id)
        return EvidentialStateSnapshot(
            relationId=relation_id,
            profileId=self._grounding.profile().id,
            queryTime=at_label if at_label is not None else iso_z(at),
            state=_state_from(supporting, refuting),
            supportingEvidenceIds=supporting,
            refutingEvidenceIds=refuting,
            observerTime=iso_z(observer_time) if observer_time is not None else None,
        )

    # -- history -----------------------------------------------------------
    def history(
        self,
        relation_id: str,
        *,
        start: datetime,
        end: datetime,
        observer_time: datetime | None = None,
    ) -> list[RelationHistoryEntry]:
        self._store.require_relation(relation_id)
        unit_ids = self._relation_unit_ids(relation_id)
        boundaries = set(self._grounding.list_state_boundaries(unit_ids, start, end))
        boundaries.add(start)
        instants = sorted(b for b in boundaries if start <= b <= end)
        if not instants:
            instants = [start]

        entries: list[RelationHistoryEntry] = []
        for index, seg_from in enumerate(instants):
            seg_to = instants[index + 1] if index + 1 < len(instants) else self._segment_end(
                relation_id, seg_from, end
            )
            snapshot = self.state_at(relation_id, seg_from)
            entry = RelationHistoryEntry(
                **{"from": iso_z(seg_from)},
                to=iso_z(seg_to) if seg_to is not None else None,
                state=snapshot.state,
                supportingEvidenceIds=snapshot.supportingEvidenceIds,
                refutingEvidenceIds=snapshot.refutingEvidenceIds,
            )
            if entries and self._mergeable(entries[-1], entry):
                entries[-1].to = entry.to
            else:
                entries.append(entry)
        return entries

    def boundary_causes(self, relation_id: str, times: list[datetime]) -> list[str]:
        """Transition references for boundaries crossed within the queried window."""
        if not times:
            return []
        window_start, window_end = min(times), max(times)
        causes: list[str] = []
        for unit_id in self._relation_unit_ids(relation_id):
            state = self._grounding.resolve_source_state(unit_id)
            if state is None or state.admissibleTo is None or state.transitionRef is None:
                continue
            within_window = window_start <= state.admissibleTo <= window_end
            if within_window and state.transitionRef not in causes:
                causes.append(state.transitionRef)
        return causes

    # -- internals ---------------------------------------------------------
    def _active_evidence(
        self, relation_id: str, grounding_reviews: frozenset[ReviewStatus] | None = None
    ) -> list[RelationEvidence]:
        return [
            evidence
            for evidence in self._store.get_relation_evidence(relation_id)
            if evidence.reviewStatus not in EXCLUDED_REVIEW_STATUSES
            and (grounding_reviews is None or evidence.reviewStatus in grounding_reviews)
        ]

    def _relation_unit_ids(self, relation_id: str) -> list[str]:
        unit_ids: list[str] = []
        for evidence in self._active_evidence(relation_id):
            for unit_id in evidence.evidence_unit_ids:
                if unit_id not in unit_ids:
                    unit_ids.append(unit_id)
        return unit_ids

    def _segment_end(
        self, relation_id: str, seg_from: datetime, query_end: datetime
    ) -> datetime | None:
        """Resolve the end of the final history segment.

        If a source state admissible at ``seg_from`` is open-ended, the segment is
        open (``None``); otherwise use the latest finite boundary governing it.
        """
        latest_finite: datetime | None = None
        for unit_id in self._relation_unit_ids(relation_id):
            state = self._grounding.resolve_source_state(unit_id)
            if state is None or not state.admissible_at(seg_from):
                continue
            if state.admissibleTo is None:
                return None
            if latest_finite is None or state.admissibleTo > latest_finite:
                latest_finite = state.admissibleTo
        return latest_finite

    @staticmethod
    def _mergeable(previous: RelationHistoryEntry, current: RelationHistoryEntry) -> bool:
        return (
            previous.to is not None
            and previous.state is current.state
            and previous.supportingEvidenceIds == current.supportingEvidenceIds
            and previous.refutingEvidenceIds == current.refutingEvidenceIds
        )


def _state_from(supporting: list[str], refuting: list[str]) -> EvidentialState:
    if supporting and refuting:
        return EvidentialState.CONTESTED
    if supporting:
        return EvidentialState.SUPPORTED
    if refuting:
        return EvidentialState.REFUTED
    return EvidentialState.UNSUPPORTED
