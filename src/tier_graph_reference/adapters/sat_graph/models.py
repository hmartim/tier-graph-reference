"""Adapter-only SAT-Graph response models.

These types exist **only** inside the SAT-Graph adapter. They are never exposed
as TIER-Graph core types: the core does not know about ``TextUnit``, ``Version``,
``Item``, or ``Action``. Fields mirror the SAT-Graph API specification but are
kept minimal (extra fields tolerated) because the adapter needs only a few.

Shape normalization (verified against a live SAT-Graph API 0.1.0 instance):
the live API returns numeric identifiers and represents intervals as
``{"start": ..., "end": ...}`` objects. Both are normalized here — identifiers
to strings, intervals to two-element ``[start, end]`` arrays — so the adapter
accepts either convention.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

#: A SAT-Graph TimeInterval is a two-element array ``[start, end]`` (end nullable).
TimeIntervalArray = list[str | None]


class SatGraphTextUnit(BaseModel):
    """Minimal view of a SAT-Graph ``TextUnit`` (the evidence-unit substrate)."""

    model_config = ConfigDict(extra="allow")

    id: str
    sourceType: str
    sourceId: str

    @field_validator("id", "sourceId", mode="before")
    @classmethod
    def _stringify(cls, value: object) -> str:
        return str(value)


class SatGraphVersion(BaseModel):
    """Minimal view of a SAT-Graph ``Version`` (the source-state substrate)."""

    model_config = ConfigDict(extra="allow")

    id: str
    itemId: str
    validityInterval: TimeIntervalArray | None = None
    applicabilityInterval: TimeIntervalArray | None = None
    producedByActionId: str | None = None
    terminatedByActionId: str | None = None

    @field_validator("id", "itemId", mode="before")
    @classmethod
    def _stringify(cls, value: object) -> str:
        return str(value)

    @field_validator("validityInterval", "applicabilityInterval", mode="before")
    @classmethod
    def _normalize_interval(cls, value: object) -> object:
        if isinstance(value, dict):
            return [value.get("start"), value.get("end")]
        return value
