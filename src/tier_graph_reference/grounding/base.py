"""The temporal grounding boundary.

A ``TemporalGroundingProvider`` owns *all* temporal admissibility semantics. The
core services depend only on this abstract interface (injected), never on any
concrete grounding substrate. The fixture provider is required for conformance;
the SAT-Graph adapter is one optional, substitutable implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from ..models import (
    AdmissibilityResult,
    GroundingSourceState,
    RelationEvidence,
    TemporalGroundingProfile,
    iso_z,
)


class TemporalGroundingProvider(ABC):
    """Answers "is this evidence admissible at time ``t``?" for one profile."""

    @abstractmethod
    def profile(self) -> TemporalGroundingProfile:
        """Return the profile metadata (id, version, interval convention)."""

    @abstractmethod
    def resolve_source_state(self, evidence_unit_id: str) -> GroundingSourceState | None:
        """Resolve the source state that owns an evidence unit."""

    @abstractmethod
    def evaluate_source_state(
        self, source_state_id: str, at: datetime, observer_time: datetime | None = None
    ) -> bool:
        """Return whether a source state is admissible at ``at``."""

    def evaluate_evidence(
        self, evidence: RelationEvidence, at: datetime, observer_time: datetime | None = None
    ) -> AdmissibilityResult:
        """Evaluate one evidence record's admissibility (conjunction over anchors).

        The record is admissible only when *every* anchor's owning source state
        is admissible at ``at`` (see T05). This default implementation is written
        purely in terms of the abstract primitives above, so it is shared by all
        providers.
        """
        anchor_results: dict[str, bool] = {}
        for anchor in evidence.anchors:
            unit_id = anchor.evidenceUnit.evidenceUnitId
            source_state = self.resolve_source_state(unit_id)
            if source_state is None:
                anchor_results[unit_id] = False
                continue
            anchor_results[unit_id] = self.evaluate_source_state(
                source_state.id, at, observer_time
            )
        admissible = bool(anchor_results) and all(anchor_results.values())
        return AdmissibilityResult(
            at=iso_z(at), admissible=admissible, anchorResults=anchor_results
        )

    @abstractmethod
    def list_state_boundaries(
        self,
        evidence_unit_ids: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[datetime]:
        """Return sorted unique admissibility boundaries for the given units."""
