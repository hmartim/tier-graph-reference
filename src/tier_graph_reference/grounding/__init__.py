"""Temporal grounding providers.

- :class:`TemporalGroundingProvider` — the abstract boundary (all the core
  depends on).
- :class:`FixtureGroundingProvider` — required for public conformance.
- ``SatGraphHttpGroundingProvider`` — optional legal integration, imported
  lazily from :mod:`tier_graph_reference.adapters.sat_graph` (requires the
  ``httpx`` extra). Import it via ``grounding.sat_graph_http`` or directly from
  the adapters package.
"""

from __future__ import annotations

from .base import TemporalGroundingProvider
from .fixture import FixtureGroundingProvider

__all__ = ["FixtureGroundingProvider", "TemporalGroundingProvider"]
