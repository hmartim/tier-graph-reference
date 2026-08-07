"""SAT-Graph HTTP temporal grounding provider (optional legal integration).

This adapter implements the abstract ``TemporalGroundingProvider`` against a
separately configured SAT-Graph API. Admissibility is decided **by the SAT-Graph
endpoint** (``getApplicableVersions``): the adapter never fabricates intervals
locally. Source-state intervals returned by ``resolve_source_state`` are read
from the authoritative ``Version`` object and are used only for informational
boundary listing.

Nothing here is required for TIER-Graph conformance. The public conformance
suite uses :class:`FixtureGroundingProvider` instead.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from ...grounding.base import TemporalGroundingProvider
from ...models import GroundingSourceState, TemporalGroundingProfile, iso_z
from ...models.common import parse_instant
from .client import SatGraphClient, SatGraphEndpoints
from .mapping import SatGraphMapping


@dataclass
class SatGraphGroundingConfig:
    """Configuration for the SAT-Graph grounding adapter (no secrets in source)."""

    base_url: str
    api_key: str | None = None
    profile_id: str = "sat-graph"
    profile_version: str = "unknown"
    endpoints: SatGraphEndpoints = field(default_factory=SatGraphEndpoints)

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> SatGraphGroundingConfig:
        source = env if env is not None else dict(os.environ)
        base_url = source.get("SATGRAPH_API_BASE_URL")
        if not base_url:
            raise RuntimeError(
                "SATGRAPH_API_BASE_URL is not set; the SAT-Graph adapter has no "
                "hard-coded endpoint. Configure it via the environment."
            )
        return cls(
            base_url=base_url,
            api_key=source.get("SATGRAPH_API_KEY"),
            profile_id=source.get("SATGRAPH_PROFILE_ID", "sat-graph"),
            profile_version=source.get("SATGRAPH_PROFILE_VERSION", "unknown"),
        )


class SatGraphHttpGroundingProvider(TemporalGroundingProvider):
    """A grounding provider backed by a live SAT-Graph API."""

    def __init__(
        self,
        config: SatGraphGroundingConfig,
        *,
        client: SatGraphClient | None = None,
        mapping: SatGraphMapping | None = None,
    ) -> None:
        self._config = config
        self._mapping = mapping or SatGraphMapping()
        self._client = client or SatGraphClient(
            base_url=config.base_url, api_key=config.api_key, endpoints=config.endpoints
        )
        self._item_by_version: dict[str, str] = {}

    # -- interface ---------------------------------------------------------
    def profile(self) -> TemporalGroundingProfile:
        return TemporalGroundingProfile(
            id=self._config.profile_id,
            name="SAT-Graph HTTP grounding",
            version=self._config.profile_version,
            authorityNote="Admissibility is decided by the configured SAT-Graph API.",
        )

    def resolve_source_state(self, evidence_unit_id: str) -> GroundingSourceState | None:
        text_unit_id = self._mapping.evidence_unit_to_text_unit_id(evidence_unit_id)
        text_unit = self._client.get_text_unit(text_unit_id)
        version_id = self._mapping.source_state_id_from_text_unit(text_unit)
        version = self._client.get_version(version_id)
        self._item_by_version[version_id] = self._mapping.item_id_from_version(version)

        interval = version.applicabilityInterval or version.validityInterval
        if not interval or interval[0] is None:
            # No authoritative interval to report; boundary listing is unavailable,
            # but admissibility is still decided by the endpoint (see evaluate_*).
            return None
        # The live API may return date-only boundaries; parse_instant normalizes
        # them to aware UTC datetimes so they compare with query instants.
        end = interval[1] if len(interval) > 1 else None
        return GroundingSourceState(
            id=version_id,
            admissibleFrom=parse_instant(interval[0]),
            admissibleTo=parse_instant(end) if end is not None else None,
            transitionRef=self._mapping.transition_ref_from_version(version),
        )

    def evaluate_source_state(
        self, source_state_id: str, at: datetime, observer_time: datetime | None = None
    ) -> bool:
        item_id = self._item_by_version.get(source_state_id)
        if item_id is None:
            version = self._client.get_version(source_state_id)
            item_id = self._mapping.item_id_from_version(version)
            self._item_by_version[source_state_id] = item_id
        applicable = self._client.get_applicable_version_ids(
            item_id,
            iso_z(at),
            iso_z(observer_time) if observer_time is not None else None,
        )
        return source_state_id in applicable

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
        return sorted(
            b
            for b in boundaries
            if (start is None or b >= start) and (end is None or b <= end)
        )

    def close(self) -> None:
        self._client.close()
