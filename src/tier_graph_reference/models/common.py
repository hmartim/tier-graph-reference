"""Shared enums, base model, and time helpers for the TIER-derived layer.

These types **implement** the normative `tier-graph-api` object model (pinned at
v0.1.0-draft); they do not redefine it. Any field that is implementation-only
(not part of the normative model) is called out in a docstring and, where it
appears in serialized output, namespaced under ``x-tier-reference``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TierModel(BaseModel):
    """Base for all TIER-derived and result models.

    ``extra="forbid"`` makes the models double as structural validators for the
    public fixtures: an unexpected field is a fixture error, not silently
    ignored.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)


class ReviewStatus(StrEnum):
    """Editorial state of a TIER-derived object."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


#: Review statuses whose evidence is excluded from admissibility/state by default.
EXCLUDED_REVIEW_STATUSES: frozenset[ReviewStatus] = frozenset(
    {ReviewStatus.REJECTED, ReviewStatus.SUPERSEDED}
)


class QualifierStatus(StrEnum):
    """Whether a qualifier dimension is specified, deliberately absent, or unknown.

    ``unknown`` is **not** ``absent``: an unknown identity-bearing qualifier
    blocks automatic relation equivalence.
    """

    SPECIFIED = "specified"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class Polarity(StrEnum):
    """Proposition polarity. Distinct from evidence stance."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class Stance(StrEnum):
    """Whether an evidence record supports or refutes its relation."""

    SUPPORTS = "supports"
    REFUTES = "refutes"


class EvidentialState(StrEnum):
    """Computed evidential state of a relation at a time.

    These are **evidential** states (a function of admissible evidence), not
    claims of domain truth.
    """

    SUPPORTED = "supported"
    REFUTED = "refuted"
    CONTESTED = "contested"
    UNSUPPORTED = "unsupported"


class IdentityDecision(StrEnum):
    """Result of comparing two relation candidates for identity."""

    EQUIVALENT = "equivalent"
    DISTINCT = "distinct"
    UNRESOLVED = "unresolved"


def parse_instant(value: str) -> datetime:
    """Parse an RFC3339 instant (accepting a trailing ``Z``) to an aware UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def iso_z(dt: datetime) -> str:
    """Format an aware datetime as ``YYYY-MM-DDTHH:MM:SSZ`` (canonical fixture form)."""
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

