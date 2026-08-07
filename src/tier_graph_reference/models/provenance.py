"""Provenance activity model.

Provenance is where re-processing detail lives: model, confidence, and generation
time belong to the *activity*, never to the evidence record. That separation is
what lets a re-extraction over the same basis append an activity instead of
creating a second, apparently independent evidential basis (see T08 and
``EvidenceKey``): none of these fields is identity-bearing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from .common import TierModel


class AgentRef(TierModel):
    """A person, organization, software component, or model.

    ``kind`` distinguishes them; the same shape serves ``agent``, ``software``,
    and ``model`` in the normative schema.
    """

    model_config = ConfigDict(extra="allow")

    kind: str = "software"
    id: str | None = None
    label: str | None = None
    name: str | None = None
    version: str | None = None


#: Backwards-compatible alias: the reference previously modelled only the model
#: slot, as ``ActivityModel``.
ActivityModel = AgentRef


class ProvenanceActivity(TierModel):
    """A reified pipeline activity (e.g. an extraction run).

    Two provenance activities may point at a single evidence occurrence: a
    re-extraction accumulates provenance without duplicating evidence (see T08).
    """

    id: str
    activityType: str
    startedAt: datetime
    endedAt: datetime | None = None
    agent: AgentRef | None = None
    software: AgentRef | None = None
    model: AgentRef | None = None
    parameters: dict[str, Any] | None = None
    #: Confidence produced by THIS activity. Belongs to the activity, not to the
    #: evidence, and is explicitly not part of the evidence identity key.
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    inputIds: list[str] = []
    outputIds: list[str] = []
    metadata: dict[str, Any] | None = None
