"""Fixture-backed temporal grounding provider.

This is a **minimal fixture-backed temporal grounding profile** used for
reproducible conformance testing. It is not a SAT-Graph database and not a
complete SAT-Graph export. It reads a ``profile-fixture.json`` document and
answers admissibility questions purely from the source-state intervals declared
there.

The intervals here belong to the grounding provider, never to the TIER-derived
data layer: no service copies them onto a ``DerivedRelation``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models import (
    GroundingSourceState,
    ProfileFixture,
    TemporalGroundingProfile,
)
from .base import TemporalGroundingProvider


class FixtureGroundingProvider(TemporalGroundingProvider):
    """A grounding provider whose facts come from a ``profile-fixture.json``."""

    def __init__(self, fixture: ProfileFixture) -> None:
        self._fixture = fixture
        self._source_states: dict[str, GroundingSourceState] = {
            state.id: state for state in fixture.sourceStates
        }
        self._owner_by_unit: dict[str, str] = {
            unit.id: unit.ownerSourceStateId for unit in fixture.evidenceUnits
        }

    # -- construction ------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FixtureGroundingProvider:
        return cls(ProfileFixture.model_validate(data))

    @classmethod
    def from_path(cls, path: str | Path) -> FixtureGroundingProvider:
        import json

        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    # -- interface ---------------------------------------------------------
    def profile(self) -> TemporalGroundingProfile:
        return self._fixture.profile

    def resolve_source_state(self, evidence_unit_id: str) -> GroundingSourceState | None:
        owner_id = self._owner_by_unit.get(evidence_unit_id)
        if owner_id is None:
            return None
        return self._source_states.get(owner_id)

    def evaluate_source_state(
        self, source_state_id: str, at: datetime, observer_time: datetime | None = None
    ) -> bool:
        # The fixture provider is single-perspective: observer_time (transaction
        # time) is accepted for interface parity but does not alter fixture data.
        state = self._source_states.get(source_state_id)
        if state is None:
            return False
        return state.admissible_at(at)

    def list_state_boundaries(
        self,
        evidence_unit_ids: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[datetime]:
        boundaries: set[datetime] = set()
        for unit_id in evidence_unit_ids:
            state = self.resolve_source_state(unit_id)
            if state is None:
                continue
            boundaries.add(state.admissibleFrom)
            if state.admissibleTo is not None:
                boundaries.add(state.admissibleTo)
        selected = sorted(
            instant
            for instant in boundaries
            if (start is None or instant >= start) and (end is None or instant <= end)
        )
        return selected

    # -- helpers used by services -----------------------------------------
    def source_state_for_unit(self, evidence_unit_id: str) -> GroundingSourceState | None:
        """Alias of :meth:`resolve_source_state` for readability at call sites."""
        return self.resolve_source_state(evidence_unit_id)

    def profile_source_states(self) -> list[GroundingSourceState]:
        """All declared source states. Fixture-only; not part of the provider contract."""
        return list(self._source_states.values())
