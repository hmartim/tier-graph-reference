"""Backward-compatible import location for the SAT-Graph HTTP grounding provider.

The implementation lives under the explicitly optional adapter package
:mod:`tier_graph_reference.adapters.sat_graph`. This shim re-exports it so code
that expects ``grounding.sat_graph_http.SatGraphHttpGroundingProvider`` keeps
working. Importing it requires the ``httpx`` extra.
"""

from __future__ import annotations

from ..adapters.sat_graph.provider import (
    SatGraphGroundingConfig,
    SatGraphHttpGroundingProvider,
)

__all__ = ["SatGraphGroundingConfig", "SatGraphHttpGroundingProvider"]
