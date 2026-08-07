"""Mappings between TIER-Graph references and SAT-Graph identifiers.

These mappings belong **only** to the adapter. The core never performs them.

    EvidenceUnitRef      -> SAT-Graph TextUnit identifier
    SourceStateRef       -> SAT-Graph Version identifier
    source identity      -> SAT-Graph Item identifier
    transition provenance-> SAT-Graph Action identifier

By default the mapping is identity (the opaque TIER reference *is* the SAT-Graph
identifier). Deployments with a different convention can subclass
:class:`SatGraphMapping` and override the hooks.
"""

from __future__ import annotations

from .models import SatGraphTextUnit, SatGraphVersion


class SatGraphMapping:
    """Default identity mapping between TIER references and SAT-Graph ids."""

    def evidence_unit_to_text_unit_id(self, evidence_unit_id: str) -> str:
        """Map an opaque evidence-unit id to a SAT-Graph ``TextUnit`` id."""
        return evidence_unit_id

    def source_state_id_from_text_unit(self, text_unit: SatGraphTextUnit) -> str:
        """Derive the owning source state (a ``Version`` id) from a ``TextUnit``."""
        return text_unit.sourceId

    def item_id_from_version(self, version: SatGraphVersion) -> str:
        """Derive the source identity (an ``Item`` id) from a ``Version``."""
        return version.itemId

    def transition_ref_from_version(self, version: SatGraphVersion) -> str | None:
        """Map the version's terminating action to a transition provenance ref."""
        return version.terminatedByActionId
