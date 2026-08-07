# Fixture format

Each conformance case is a directory under `fixtures/cases/T<NN>-<slug>/` with
four payload files plus a README. The case is registered in
`fixtures/manifest.yaml`, which is the single source of the case declarations.

```
fixtures/
├── manifest.yaml          # registry + declarations (implements, versions, classes)
├── fixture.schema.json    # JSON Schema for case metadata (input.json)
└── cases/
    └── T01-persistent-relation/
        ├── README.md
        ├── input.json
        ├── profile-fixture.json
        ├── request.json
        └── expected.json
```

## `input.json` — TIER-derived objects only

```jsonc
{
  "caseId": "T01",
  "title": "...",
  "specificationVersion": "0.1.0-draft",
  "operation": "getRelationHistory",
  "entities": [ /* DerivedEntity */ ],
  "relations": [ /* DerivedRelation (no temporal interval!) */ ],
  "evidence": [ /* RelationEvidence */ ],
  "provenanceActivities": [ /* optional */ ],
  "admissionPolicies": [ /* optional */ ]
}
```

Contains only TIER-derived objects: entities, relations, evidence, provenance,
review events, and (optionally) admission policies. It loads into the Pydantic
models — an unmodelled field is a validation error.

## `profile-fixture.json` — minimal grounding facts

```jsonc
{
  "profile": { "id": "public-legal-fixture", "version": "0.1.0", "intervalConvention": "[from,to)" },
  "evidenceUnits": [ { "id": "tu-art6-1988", "ownerSourceStateId": "v-art6-1988" } ],
  "sourceStates": [ { "id": "v-art6-1988", "admissibleFrom": "1988-10-05T00:00:00Z", "admissibleTo": "2000-02-14T00:00:00Z" } ]
}
```

A **minimal fixture-backed temporal grounding profile**, not a SAT-Graph export.
Intervals are half-open `[admissibleFrom, admissibleTo)`; a missing/`null`
`admissibleTo` means open-ended. `publishedAt` is informational and never
controls admissibility (see T09). `transitionRef` records the provenance of a
boundary (see T04).

## `request.json` — the operation to execute

```jsonc
{ "operation": "getRelationHistory", "arguments": { "relationId": "...", "profileId": "...", "startAt": "...", "endAt": "..." } }
```

The `operation` must be one the runner supports (see
`conformance.operations.supported_operations()`).

## `expected.json` — the asserted result

`expected.json` is a **partial assertion**: every key/value it declares must be
present and equal in the actual result. Extra keys in the actual result are
allowed, but arrays must match element-for-element and in length. This lets one
operation handler serve several cases that assert different invariants (e.g.
`getRelationStateAtTime` asserts `relationCount` in T02 but
`distinctRelationCount` in T07).

See [conformance.md](conformance.md) for the comparison rules in detail.

## Manifest declarations

Beyond the payloads, each case declares (in `manifest.yaml`):

```yaml
- id: T01
  operation: getRelationHistory
  conformanceClass: Query API Conformance
  groundingProfileId: public-legal-fixture
  groundingProfileVersion: 0.1.0
  caseDefinitionReference:
    repository: tier-graph-api
    version: 0.1.0-draft
    path: conformance/cases/T01.md
```

`caseDefinitionReference` points at the **normative** definition of the case in
`tier-graph-api`. The fixture *implements* that case; it does not redefine it.

## Adding a case

1. Create the case directory with the five files.
2. Register it in `manifest.yaml` with its declarations.
3. Run `python scripts/validate_fixtures.py` and
   `python scripts/run_conformance.py`.

Adapter-integration fixtures (that exercise the SAT-Graph adapter) do **not** go
here; they live under `tests/adapters/sat_graph/` with mocked responses.
