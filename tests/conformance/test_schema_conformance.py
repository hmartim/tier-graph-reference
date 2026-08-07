"""Validate serialized results against the vendored normative JSON Schemas.

Field-by-field assertions are what let ``GroundedPath`` drift: the reference
carried a flat ``relationIds`` list for a schema that requires ``steps``, and
``PathStep`` sat unused as dead code while every path answer silently dropped its
evidential state. Nothing compared the produced object to the contract *as a
whole*, so nothing noticed.

These tests validate the **entire** object, so `additionalProperties: false` and
every required field are enforced. The schemas are vendored (not read from a
sibling checkout) so the check is self-contained and pinned.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
from tier_graph_reference.models import parse_instant
from tier_graph_reference.services import ServiceContext
from tier_graph_reference.store.memory import MemoryTierStore

_VENDOR = Path(__file__).resolve().parents[2] / "vendor/tier-graph-api/0.1.0-draft"
_SCHEMAS = _VENDOR / "schemas"


def _tree_sha256() -> str:
    """Checksum over the vendored tree: sorted relative path + file bytes."""
    import hashlib

    digest = hashlib.sha256()
    for file in sorted(_SCHEMAS.rglob("*.json")):
        digest.update(file.relative_to(_SCHEMAS).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def test_vendored_schema_tree_matches_its_recorded_checksum() -> None:
    """The pin is only worth anything if drift is detectable.

    A vendored copy that is silently edited would make every validation below
    pass against something other than the normative contract.
    """
    recorded = (_VENDOR / "schemas.sha256").read_text(encoding="utf-8").split()[0]
    assert _tree_sha256() == recorded, (
        "the vendored schema tree no longer matches its recorded checksum; "
        "re-vendor from the pinned commit or update the record deliberately"
    )


def test_validation_resolves_only_against_the_vendored_tree() -> None:
    """No test may resolve a $ref against a sibling checkout or an installed copy."""
    resolved = _REGISTRY.get_or_retrieve(_BASE + "query/grounded-path.schema.json").value
    vendored = json.loads((_SCHEMAS / "query/grounded-path.schema.json").read_text("utf-8"))
    assert resolved.contents == vendored
    assert all(
        str(uri).startswith("https://spec.tier-graph.org/schemas/") for uri in _REGISTRY
    ), "the registry holds a resource from outside the vendored tree"


def _registry() -> Registry:
    """Register every vendored schema under its own ``$id`` and its relative path."""
    registry: Registry = Registry()
    for file in sorted(_SCHEMAS.rglob("*.schema.json")):
        contents = json.loads(file.read_text(encoding="utf-8"))
        resource = Resource(contents=contents, specification=DRAFT202012)
        registry = registry.with_resource(contents["$id"], resource)
    return registry


_REGISTRY = _registry()
_BASE = "https://spec.tier-graph.org/schemas/"


def validate(schema_name: str, instance: Any) -> None:
    """Validate a whole instance against a vendored normative schema."""
    uri = _BASE + schema_name
    schema = _REGISTRY.get_or_retrieve(uri).value.contents
    errors = sorted(
        Draft202012Validator(schema, registry=_REGISTRY).iter_errors(instance),
        key=lambda e: list(e.absolute_path),
    )
    assert not errors, "\n".join(
        f"  at ${'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors
    )


# -- a graph where one relation is admissible but REFUTED --------------------
_INPUT: dict[str, Any] = {
    "entities": [
        {"id": f"de-{x}", "canonicalLabel": x.upper(), "entityType": "concept",
         "reviewStatus": "accepted"} for x in ("a", "b", "c")
    ],
    "relations": [
        {"id": "ab", "sourceEntityId": "de-a", "predicate": "P", "targetEntityId": "de-b",
         "predicateFamily": "procedural", "reviewStatus": "accepted"},
        {"id": "bc", "sourceEntityId": "de-b", "predicate": "Q", "targetEntityId": "de-c",
         "predicateFamily": "factualCausal", "reviewStatus": "accepted"},
    ],
    "evidence": [
        {"id": "e-ab", "relationId": "ab",
         "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u"}}],
         "stance": "supports", "reviewStatus": "accepted"},
        # bc has ONLY refuting evidence: admissible under recall, never supported.
        {"id": "e-bc", "relationId": "bc",
         "anchors": [{"evidenceUnit": {"profileId": "p", "evidenceUnitId": "u"}}],
         "stance": "refutes", "reviewStatus": "accepted"},
    ],
    "admissionPolicies": [
        {"id": "strict", "name": "Strict", "admittedStates": ["supported"]},
        {"id": "recall", "name": "Recall", "admittedStates": ["supported", "refuted", "contested"]},
    ],
}
_PROFILE = {
    "profile": {"id": "p", "version": "1"},
    "evidenceUnits": [{"id": "u", "ownerSourceStateId": "s"}],
    "sourceStates": [{"id": "s", "admissibleFrom": "2020-01-01T00:00:00Z", "admissibleTo": None}],
}
_AT = "2024-01-01T00:00:00Z"


def _ctx() -> ServiceContext:
    return ServiceContext.build(
        MemoryTierStore.from_input(_INPUT), FixtureGroundingProvider.from_dict(_PROFILE)
    )


def _recall_path() -> Any:
    paths, _ = _ctx().paths.find_paths("de-a", "de-c", parse_instant(_AT), "recall", 2)
    assert len(paths) == 1, "the recall policy should admit the two-hop route"
    return paths[0]


# -- A: strict policy --------------------------------------------------------
def test_strict_policy_excludes_the_refuted_relation() -> None:
    ctx = _ctx()
    projected = {p.relationId for p in ctx.projection.project(parse_instant(_AT), "strict")}
    assert projected == {"ab"}
    paths, _ = ctx.paths.find_paths("de-a", "de-c", parse_instant(_AT), "strict", 2)
    assert paths == []


# -- B: recall policy admits it, but the state survives ----------------------
def test_recall_policy_admits_but_preserves_the_refuted_state() -> None:
    path = _recall_path()
    assert path.admissible is True, "every step was admitted by the policy"
    states = {s.relationId: s.evidentialState.state.value for s in path.steps}
    assert states == {"ab": "supported", "bc": "refuted"}
    assert all(step.admitted for step in path.steps)


# -- C: admission is not support --------------------------------------------
def test_admissible_path_is_not_necessarily_supported() -> None:
    """The distinction the old shape destroyed."""
    path = _recall_path()
    assert path.admissible is True
    assert path.is_supported is False, (
        "a path containing a refuted step must not read as positively supported"
    )


def test_supported_path_is_both_admissible_and_supported() -> None:
    ctx = _ctx()
    paths, _ = ctx.paths.find_paths("de-a", "de-b", parse_instant(_AT), "recall", 1)
    assert len(paths) == 1
    assert paths[0].admissible and paths[0].is_supported


# -- D: whole-object validation against the normative schema -----------------
def test_grounded_path_validates_against_the_normative_schema() -> None:
    validate("query/grounded-path.schema.json",
             _recall_path().model_dump(mode="json", exclude_none=True))


def test_evidential_state_snapshot_validates_against_the_normative_schema() -> None:
    snapshot = _ctx().relation_state.state_at("ab", parse_instant(_AT))
    validate("query/evidential-state-snapshot.schema.json",
             snapshot.model_dump(mode="json", exclude_none=True))


def test_schema_validation_rejects_the_pre_correction_shape() -> None:
    """The shape this repository used to emit must fail the normative schema.

    Without this, a future regression could reintroduce the flat list and the
    validator above would never be exercised against a genuine negative.
    """
    with pytest.raises(AssertionError):
        validate("query/grounded-path.schema.json",
                 {"relationIds": ["ab", "bc"], "admissible": True})


# -- structural invariants JSON Schema cannot express ------------------------
def test_zero_length_paths_are_not_returned() -> None:
    """A deliberate contract decision, not a mathematical necessity.

    Graph theory admits a trivial path of length zero from a vertex to itself.
    This operation returns *relational* paths, so it does not: a zero-step answer
    carries no evidence and no admissibility to report. The schema currently
    expresses this only implicitly (``steps`` is required but unbounded); this
    test pins the behaviour so it cannot flip silently.
    """
    ctx = _ctx()
    paths, _ = ctx.paths.find_paths("de-a", "de-a", parse_instant(_AT), "recall", 2)
    assert paths == []


def test_steps_are_contiguous_and_chained() -> None:
    """Ordinals run 0..n-1 and each step starts where the previous one ended."""
    path = _recall_path()
    assert [s.ordinal for s in path.steps] == list(range(len(path.steps)))
    for previous, following in zip(path.steps, path.steps[1:], strict=False):
        assert previous.toEntityId == following.fromEntityId, (
            f"step {previous.ordinal} ends at {previous.toEntityId} but "
            f"step {following.ordinal} starts at {following.fromEntityId}"
        )


def test_path_endpoints_match_first_and_last_steps() -> None:
    path = _recall_path()
    assert path.sourceEntityId == path.steps[0].fromEntityId
    assert path.targetEntityId == path.steps[-1].toEntityId


def test_admissible_implies_every_step_admitted() -> None:
    path = _recall_path()
    assert path.admissible is all(step.admitted for step in path.steps)


def test_is_supported_is_derived_not_serialized() -> None:
    """`additionalProperties: false` forbids inventing a field for it."""
    dumped = _recall_path().model_dump(mode="json", exclude_none=True)
    assert "is_supported" not in dumped
    assert "supportive" not in dumped


# -- E: the correction must not change WHICH relations are admitted ----------
@pytest.mark.parametrize("policy,expected", [("strict", {"ab"}), ("recall", {"ab", "bc"})])
def test_temporal_decision_is_unchanged_by_the_representation(
    policy: str, expected: set[str]
) -> None:
    ctx = _ctx()
    projected = {p.relationId for p in ctx.projection.project(parse_instant(_AT), policy)}
    assert projected == expected


# -- F: serialization round-trip preserves the state -------------------------
def test_round_trip_preserves_step_state_and_order() -> None:
    """Guards against a future DTO or adapter layer dropping the state again."""
    from tier_graph_reference.models import GroundedPath

    original = _recall_path()
    restored = GroundedPath.model_validate(
        json.loads(json.dumps(original.model_dump(mode="json", exclude_none=True)))
    )
    assert [s.ordinal for s in restored.steps] == [s.ordinal for s in original.steps]
    assert [s.relationId for s in restored.steps] == [s.relationId for s in original.steps]
    assert [s.fromEntityId for s in restored.steps] == [s.fromEntityId for s in original.steps]
    assert [s.toEntityId for s in restored.steps] == [s.toEntityId for s in original.steps]
    assert [s.evidentialState.state for s in restored.steps] == [
        s.evidentialState.state for s in original.steps
    ]
    assert restored.is_supported == original.is_supported
