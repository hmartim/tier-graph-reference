"""Optional SAT-Graph HTTP grounding adapter.

Requires the ``httpx`` extra. This adapter is one substitutable legal
integration; it is never required for TIER-Graph conformance.
"""

from __future__ import annotations

from .client import SatGraphClient, SatGraphEndpoints
from .mapping import SatGraphMapping
from .models import SatGraphTextUnit, SatGraphVersion
from .provider import SatGraphGroundingConfig, SatGraphHttpGroundingProvider

__all__ = [
    "SatGraphClient",
    "SatGraphEndpoints",
    "SatGraphGroundingConfig",
    "SatGraphHttpGroundingProvider",
    "SatGraphMapping",
    "SatGraphTextUnit",
    "SatGraphVersion",
]
