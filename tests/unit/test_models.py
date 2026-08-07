"""Model-level invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tier_graph_reference.models import (
    INTERVAL_KEYS,
    DerivedRelation,
    QualifierStatus,
    RelationQualifier,
    iso_z,
    parse_instant,
)

_MINIMAL_RELATION = {
    "id": "r",
    "sourceEntityId": "a",
    "predicate": "P",
    "targetEntityId": "b",
    "predicateFamily": "fam",
}


def test_specified_qualifier_requires_value() -> None:
    with pytest.raises(ValidationError):
        RelationQualifier(status=QualifierStatus.SPECIFIED)


def test_absent_and_unknown_reject_values() -> None:
    with pytest.raises(ValidationError):
        RelationQualifier(status=QualifierStatus.ABSENT, value="x")
    with pytest.raises(ValidationError):
        RelationQualifier(status=QualifierStatus.UNKNOWN, value="x")


def test_unknown_is_not_absent() -> None:
    absent = RelationQualifier(status=QualifierStatus.ABSENT)
    unknown = RelationQualifier(status=QualifierStatus.UNKNOWN)
    assert absent != unknown
    assert unknown.is_unknown and not absent.is_unknown


def test_relation_has_no_interval_fields() -> None:
    dumped = DerivedRelation(**_MINIMAL_RELATION).model_dump()  # type: ignore[arg-type]
    for banned in INTERVAL_KEYS:
        assert banned not in dumped


@pytest.mark.parametrize("key", sorted(INTERVAL_KEYS))
def test_relation_rejects_authoritative_interval_keys(key: str) -> None:
    """R3 is enforced structurally: such a relation cannot even be constructed."""
    with pytest.raises(ValidationError):
        DerivedRelation.model_validate({**_MINIMAL_RELATION, key: "2020-01-01T00:00:00Z"})


def test_instant_roundtrip_is_canonical() -> None:
    assert iso_z(parse_instant("1988-10-05T00:00:00Z")) == "1988-10-05T00:00:00Z"
