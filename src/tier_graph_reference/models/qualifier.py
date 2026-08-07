"""Relation qualifier model."""

from __future__ import annotations

from pydantic import model_validator

from .common import QualifierStatus, TierModel

#: A qualifier value may be a scalar string or a list of strings (e.g. roles).
QualifierValue = str | list[str] | None


class RelationQualifier(TierModel):
    """One qualifier dimension of a relation (polarity, condition, scope, ...).

    A qualifier carries a ``status`` and, only when ``specified``, a ``value``.
    The distinction between ``absent`` and ``unknown`` is load-bearing for
    identity comparison and is enforced here: ``unknown`` never carries a value.
    """

    status: QualifierStatus
    value: QualifierValue = None

    @model_validator(mode="after")
    def _check_value_matches_status(self) -> RelationQualifier:
        if self.status is QualifierStatus.SPECIFIED and self.value is None:
            raise ValueError("a 'specified' qualifier must carry a value")
        if self.status is not QualifierStatus.SPECIFIED and self.value is not None:
            raise ValueError(f"a '{self.status.value}' qualifier must not carry a value")
        return self

    @property
    def is_specified(self) -> bool:
        return self.status is QualifierStatus.SPECIFIED

    @property
    def is_unknown(self) -> bool:
        return self.status is QualifierStatus.UNKNOWN
