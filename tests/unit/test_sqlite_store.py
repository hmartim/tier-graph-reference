"""TIER-only SQLite store: no source tables, faithful round-trip."""

from __future__ import annotations

from tier_graph_reference.store.memory import MemoryTierStore
from tier_graph_reference.store.sqlite import FORBIDDEN_TABLES, SQLiteTierStore

_INPUT = {
    "entities": [
        {"id": "de-a", "canonicalLabel": "A", "entityType": "concept", "reviewStatus": "accepted"},
        {"id": "de-b", "canonicalLabel": "B", "entityType": "concept", "reviewStatus": "accepted"},
    ],
    "relations": [
        {
            "id": "r",
            "sourceEntityId": "de-a",
            "predicate": "CAUSES",
            "targetEntityId": "de-b",
            "predicateFamily": "factualCausal",
            "qualifiers": {
                "polarity": {"status": "specified", "value": "positive"},
                "participantRoles": {"status": "specified", "value": ["agent", "third party"]},
                "condition": {"status": "absent"},
            },
            "reviewStatus": "accepted",
        }
    ],
    "evidence": [
        {
            "id": "e",
            "relationId": "r",
            "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u"}}],
            "stance": "supports",
            "reviewStatus": "accepted",
            "provenanceActivityIds": ["pa-1"],
        }
    ],
    "provenanceActivities": [
        {"id": "pa-1", "activityType": "extraction", "startedAt": "2026-01-01T00:00:00Z"}
    ],
}


def test_schema_has_no_source_tables() -> None:
    store = SQLiteTierStore.create(source=MemoryTierStore.from_input(_INPUT))
    store.assert_no_source_tables()
    assert not (store.table_names() & FORBIDDEN_TABLES)


def test_roundtrip_preserves_relation_and_evidence() -> None:
    store = SQLiteTierStore.create(source=MemoryTierStore.from_input(_INPUT))
    relation = store.get_relation("r")
    assert relation is not None
    assert relation.qualifiers["participantRoles"].value == ["agent", "third party"]
    assert relation.qualifiers["condition"].status.value == "absent"

    reverse = store.get_relations_by_evidence_unit("p", "u")
    assert [r.id for r in reverse] == ["r"]

    evidence = store.get_evidence("e")
    assert evidence is not None
    assert evidence.provenanceActivityIds == ["pa-1"]
