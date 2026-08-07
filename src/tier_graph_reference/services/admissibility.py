"""Evidence admissibility service.

Admissibility of an evidence record is conjunctive over its anchors: every
anchor's owning source state must be admissible at ``t`` (see T05). Separate
evidence records are alternative bases and are evaluated independently.
"""

from __future__ import annotations

from datetime import datetime

from ..grounding.base import TemporalGroundingProvider
from ..models import AdmissibilityResult, RelationEvidence
from ..store.base import TierStore


class AdmissibilityService:
    """Evaluates whether evidence is admissible at a given time."""

    def __init__(self, store: TierStore, grounding: TemporalGroundingProvider) -> None:
        self._store = store
        self._grounding = grounding

    def evaluate(
        self, evidence_id: str, at: datetime, observer_time: datetime | None = None
    ) -> AdmissibilityResult:
        evidence = self._store.require_evidence(evidence_id)
        return self._grounding.evaluate_evidence(evidence, at, observer_time)

    def evaluate_record(
        self, evidence: RelationEvidence, at: datetime, observer_time: datetime | None = None
    ) -> AdmissibilityResult:
        return self._grounding.evaluate_evidence(evidence, at, observer_time)
