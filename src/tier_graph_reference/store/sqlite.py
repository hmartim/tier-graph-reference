"""Optional TIER-only SQLite store.

The schema contains **only** TIER-derived tables. It intentionally never
declares SAT-Graph source tables (``item``, ``version``, ``text_unit``,
``action``, ``applicability_interval``, ``validity_interval``). External
references remain opaque strings such as ``public-legal:tu-art6-1988``.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..models import (
    AdmissionPolicy,
    DerivedEntity,
    DerivedRelation,
    ProvenanceActivity,
    RelationEvidence,
    ReviewEvent,
)
from .base import Filters, TierStore, WritableTierStore

#: Source-substrate tables that MUST NOT appear in a TIER-only database.
FORBIDDEN_TABLES: frozenset[str] = frozenset(
    {
        "item",
        "version",
        "text_unit",
        "action",
        "applicability_interval",
        "validity_interval",
    }
)

_SCHEMA = """
CREATE TABLE derived_entity (
    id TEXT PRIMARY KEY,
    canonical_label TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    review_status TEXT NOT NULL
);
CREATE TABLE derived_relation (
    id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    predicate_family TEXT NOT NULL,
    review_status TEXT NOT NULL
);
CREATE TABLE relation_qualifier (
    relation_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    status TEXT NOT NULL,
    value_json TEXT,
    PRIMARY KEY (relation_id, dimension)
);
CREATE TABLE relation_evidence (
    id TEXT PRIMARY KEY,
    relation_id TEXT NOT NULL,
    stance TEXT NOT NULL,
    review_status TEXT NOT NULL
);
CREATE TABLE evidence_anchor (
    evidence_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    profile_id TEXT NOT NULL,
    evidence_unit_id TEXT NOT NULL,
    role TEXT,
    selector_json TEXT,
    PRIMARY KEY (evidence_id, idx)
);
CREATE TABLE provenance_activity (
    id TEXT PRIMARY KEY,
    activity_type TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    model_json TEXT
);
CREATE TABLE evidence_provenance_activity (
    evidence_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    PRIMARY KEY (evidence_id, activity_id)
);
CREATE TABLE review_event (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    status TEXT NOT NULL,
    reviewer TEXT,
    decided_at TEXT,
    note TEXT
);
CREATE TABLE admission_policy (
    id TEXT PRIMARY KEY,
    name TEXT,
    admitted_states_json TEXT NOT NULL
);
CREATE INDEX ix_relation_evidence_relation ON relation_evidence (relation_id);
CREATE INDEX ix_evidence_anchor_unit ON evidence_anchor (profile_id, evidence_unit_id);
"""


class SQLiteTierStore(TierStore):
    """A TIER-only store backed by SQLite.

    Use :meth:`create` to build a fresh database, optionally seeding it from an
    existing :class:`~tier_graph_reference.store.base.TierStore`.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._conn = connection
        self._conn.row_factory = sqlite3.Row

    # -- construction ------------------------------------------------------
    @classmethod
    def create(
        cls, path: str | Path | None = None, *, source: TierStore | None = None
    ) -> SQLiteTierStore:
        """Create a new TIER-only database (in-memory if ``path`` is None)."""
        conn = sqlite3.connect(str(path) if path is not None else ":memory:")
        conn.executescript(_SCHEMA)
        conn.commit()
        store = cls(conn)
        if source is not None:
            store.seed_from(source)
        return store

    def close(self) -> None:
        self._conn.close()

    def table_names(self) -> set[str]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {row["name"] for row in rows}

    def assert_no_source_tables(self) -> None:
        """Fail loudly if any forbidden source-substrate table exists."""
        present = self.table_names() & FORBIDDEN_TABLES
        if present:
            raise AssertionError(f"forbidden source-substrate tables present: {sorted(present)}")

    # -- seeding -----------------------------------------------------------
    def seed_from(self, source: TierStore) -> None:
        for entity in source.list_entities():
            self._insert_entity(entity)
        for relation in source.list_relations():
            self._insert_relation(relation)
        for evidence in source.list_evidence():
            self._insert_evidence(evidence)
        for activity in source.list_provenance_activities():
            self._insert_activity(activity)
        for event in source.get_review_events():
            self._insert_review(event)
        for policy in source.list_policies():
            self._insert_policy(policy)
        self._conn.commit()

    def _insert_entity(self, entity: DerivedEntity) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO derived_entity VALUES (?, ?, ?, ?)",
            (entity.id, entity.canonicalLabel, entity.entityType, entity.reviewStatus.value),
        )

    def _insert_relation(self, relation: DerivedRelation) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO derived_relation VALUES (?, ?, ?, ?, ?, ?)",
            (
                relation.id,
                relation.sourceEntityId,
                relation.predicate,
                relation.targetEntityId,
                relation.predicateFamily,
                relation.reviewStatus.value,
            ),
        )
        for dimension, qualifier in relation.qualifiers.items():
            value_json = None if qualifier.value is None else json.dumps(qualifier.value)
            self._conn.execute(
                "INSERT OR REPLACE INTO relation_qualifier VALUES (?, ?, ?, ?)",
                (relation.id, dimension, qualifier.status.value, value_json),
            )

    def _insert_evidence(self, evidence: RelationEvidence) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO relation_evidence VALUES (?, ?, ?, ?)",
            (evidence.id, evidence.relationId, evidence.stance.value, evidence.reviewStatus.value),
        )
        for idx, anchor in enumerate(evidence.anchors):
            selector_json = (
                None
                if anchor.selector is None
                else json.dumps(anchor.selector.model_dump(exclude_none=True))
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO evidence_anchor VALUES (?, ?, ?, ?, ?, ?)",
                (
                    evidence.id,
                    idx,
                    anchor.evidenceUnit.profileId,
                    anchor.evidenceUnit.evidenceUnitId,
                    anchor.role,
                    selector_json,
                ),
            )
        for ordinal, activity_id in enumerate(evidence.provenanceActivityIds):
            self._conn.execute(
                "INSERT OR REPLACE INTO evidence_provenance_activity VALUES (?, ?, ?)",
                (evidence.id, activity_id, ordinal),
            )

    def _insert_activity(self, activity: ProvenanceActivity) -> None:
        model_json = None if activity.model is None else json.dumps(activity.model.model_dump())
        self._conn.execute(
            "INSERT OR REPLACE INTO provenance_activity VALUES (?, ?, ?, ?, ?)",
            (
                activity.id,
                activity.activityType,
                activity.startedAt.isoformat() if activity.startedAt else None,
                activity.endedAt.isoformat() if activity.endedAt else None,
                model_json,
            ),
        )

    def _insert_review(self, event: ReviewEvent) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO review_event VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.id,
                event.subjectId,
                event.status.value,
                event.reviewer,
                event.decidedAt.isoformat() if event.decidedAt else None,
                event.note,
            ),
        )

    def _insert_policy(self, policy: AdmissionPolicy) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO admission_policy VALUES (?, ?, ?)",
            (policy.id, policy.name, json.dumps([s.value for s in policy.admittedStates])),
        )

    # -- reconstruction ----------------------------------------------------
    def _entity_from_row(self, row: sqlite3.Row) -> DerivedEntity:
        return DerivedEntity(
            id=row["id"],
            canonicalLabel=row["canonical_label"],
            entityType=row["entity_type"],
            reviewStatus=row["review_status"],
        )

    def _relation_from_row(self, row: sqlite3.Row) -> DerivedRelation:
        qrows = self._conn.execute(
            "SELECT dimension, status, value_json FROM relation_qualifier WHERE relation_id = ?",
            (row["id"],),
        ).fetchall()
        qualifiers: dict[str, Any] = {}
        for q in qrows:
            value = None if q["value_json"] is None else json.loads(q["value_json"])
            qualifiers[q["dimension"]] = {"status": q["status"], "value": value}
        return DerivedRelation.model_validate(
            {
                "id": row["id"],
                "sourceEntityId": row["source_entity_id"],
                "predicate": row["predicate"],
                "targetEntityId": row["target_entity_id"],
                "predicateFamily": row["predicate_family"],
                "qualifiers": qualifiers,
                "reviewStatus": row["review_status"],
            }
        )

    def _evidence_from_row(self, row: sqlite3.Row) -> RelationEvidence:
        arows = self._conn.execute(
            "SELECT idx, profile_id, evidence_unit_id, role, selector_json "
            "FROM evidence_anchor WHERE evidence_id = ? ORDER BY idx",
            (row["id"],),
        ).fetchall()
        anchors: list[dict[str, Any]] = []
        for a in arows:
            anchor: dict[str, Any] = {
                "evidenceUnit": {
                    "profileId": a["profile_id"],
                    "evidenceUnitId": a["evidence_unit_id"],
                }
            }
            if a["role"] is not None:
                anchor["role"] = a["role"]
            if a["selector_json"] is not None:
                anchor["selector"] = json.loads(a["selector_json"])
            anchors.append(anchor)
        prows = self._conn.execute(
            "SELECT activity_id FROM evidence_provenance_activity "
            "WHERE evidence_id = ? ORDER BY ordinal",
            (row["id"],),
        ).fetchall()
        return RelationEvidence.model_validate(
            {
                "id": row["id"],
                "relationId": row["relation_id"],
                "anchors": anchors,
                "stance": row["stance"],
                "reviewStatus": row["review_status"],
                "provenanceActivityIds": [p["activity_id"] for p in prows],
            }
        )

    def _activity_from_row(self, row: sqlite3.Row) -> ProvenanceActivity:
        data: dict[str, Any] = {
            "id": row["id"],
            "activityType": row["activity_type"],
        }
        if row["started_at"] is not None:
            data["startedAt"] = row["started_at"]
        if row["ended_at"] is not None:
            data["endedAt"] = row["ended_at"]
        if row["model_json"] is not None:
            data["model"] = json.loads(row["model_json"])
        return ProvenanceActivity.model_validate(data)

    # -- read interface ----------------------------------------------------
    def get_entity(self, entity_id: str) -> DerivedEntity | None:
        row = self._conn.execute(
            "SELECT * FROM derived_entity WHERE id = ?", (entity_id,)
        ).fetchone()
        return self._entity_from_row(row) if row else None

    def list_entities(self, filters: Filters = None) -> list[DerivedEntity]:
        rows = self._conn.execute("SELECT * FROM derived_entity").fetchall()
        entities = [self._entity_from_row(row) for row in rows]
        return [e for e in entities if _matches(e, filters)]

    def get_relation(self, relation_id: str) -> DerivedRelation | None:
        row = self._conn.execute(
            "SELECT * FROM derived_relation WHERE id = ?", (relation_id,)
        ).fetchone()
        return self._relation_from_row(row) if row else None

    def list_relations(self, filters: Filters = None) -> list[DerivedRelation]:
        rows = self._conn.execute("SELECT * FROM derived_relation").fetchall()
        relations = [self._relation_from_row(row) for row in rows]
        return [r for r in relations if _matches(r, filters)]

    def get_evidence(self, evidence_id: str) -> RelationEvidence | None:
        row = self._conn.execute(
            "SELECT * FROM relation_evidence WHERE id = ?", (evidence_id,)
        ).fetchone()
        return self._evidence_from_row(row) if row else None

    def list_evidence(self, filters: Filters = None) -> list[RelationEvidence]:
        rows = self._conn.execute("SELECT * FROM relation_evidence").fetchall()
        evidence = [self._evidence_from_row(row) for row in rows]
        return [e for e in evidence if _matches(e, filters)]

    def get_relation_evidence(self, relation_id: str) -> list[RelationEvidence]:
        rows = self._conn.execute(
            "SELECT * FROM relation_evidence WHERE relation_id = ?", (relation_id,)
        ).fetchall()
        return [self._evidence_from_row(row) for row in rows]

    def get_relations_by_evidence_unit(
        self, profile_id: str, evidence_unit_id: str
    ) -> list[DerivedRelation]:
        rows = self._conn.execute(
            "SELECT DISTINCT re.relation_id AS relation_id, re.rowid AS ord "
            "FROM evidence_anchor ea JOIN relation_evidence re ON ea.evidence_id = re.id "
            "WHERE ea.profile_id = ? AND ea.evidence_unit_id = ? ORDER BY ord",
            (profile_id, evidence_unit_id),
        ).fetchall()
        result: list[DerivedRelation] = []
        seen: set[str] = set()
        for row in rows:
            rid = row["relation_id"]
            if rid in seen:
                continue
            seen.add(rid)
            relation = self.get_relation(rid)
            if relation is not None:
                result.append(relation)
        return result

    def get_provenance_activity(self, activity_id: str) -> ProvenanceActivity | None:
        row = self._conn.execute(
            "SELECT * FROM provenance_activity WHERE id = ?", (activity_id,)
        ).fetchone()
        return self._activity_from_row(row) if row else None

    def list_provenance_activities(
        self, subject_id: str | None = None
    ) -> list[ProvenanceActivity]:
        if subject_id is None:
            rows = self._conn.execute("SELECT * FROM provenance_activity").fetchall()
            return [self._activity_from_row(row) for row in rows]
        prows = self._conn.execute(
            "SELECT activity_id FROM evidence_provenance_activity "
            "WHERE evidence_id = ? ORDER BY ordinal",
            (subject_id,),
        ).fetchall()
        activities: list[ProvenanceActivity] = []
        for p in prows:
            activity = self.get_provenance_activity(p["activity_id"])
            if activity is not None:
                activities.append(activity)
        return activities

    def get_review_events(self, subject_id: str | None = None) -> list[ReviewEvent]:
        if subject_id is None:
            rows = self._conn.execute("SELECT * FROM review_event").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM review_event WHERE subject_id = ?", (subject_id,)
            ).fetchall()
        return [
            ReviewEvent.model_validate(
                {
                    "id": row["id"],
                    "subjectId": row["subject_id"],
                    "status": row["status"],
                    "reviewer": row["reviewer"],
                    "decidedAt": row["decided_at"],
                    "note": row["note"],
                }
            )
            for row in rows
        ]

    def get_policy(self, policy_id: str) -> AdmissionPolicy | None:
        row = self._conn.execute(
            "SELECT * FROM admission_policy WHERE id = ?", (policy_id,)
        ).fetchone()
        if row is None:
            return None
        return AdmissionPolicy.model_validate(
            {
                "id": row["id"],
                "name": row["name"],
                "admittedStates": json.loads(row["admitted_states_json"]),
            }
        )

    def list_policies(self) -> list[AdmissionPolicy]:
        rows = self._conn.execute("SELECT id FROM admission_policy").fetchall()
        policies: list[AdmissionPolicy] = []
        for row in rows:
            policy = self.get_policy(row["id"])
            if policy is not None:
                policies.append(policy)
        return policies


def _matches(obj: Any, filters: Filters) -> bool:
    if not filters:
        return True
    return all(getattr(obj, key, None) == expected for key, expected in filters.items())


# Re-export for the writable interface parity check in tests.
__all__ = ["FORBIDDEN_TABLES", "SQLiteTierStore", "WritableTierStore"]
