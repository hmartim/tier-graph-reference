# Vendored normative specification — `tier-graph-api` v0.1.0-draft

Exact, unmodified snapshots of the normative artifacts this reference
implementation targets.

| Field | Value |
|---|---|
| Source repository | `https://github.com/hmartim/tier-graph-api` |
| Source tag / commit | `v0.1.0-draft` @ `d7875b6` |
| Retrieval date | 2026-08-07 |
| Modifications | **None.** Byte-for-byte copies. |

The commit is the immutable anchor; the tag is for legibility.

## Artifacts

### `conformance/manifest.yaml`

The normative case catalogue (T01–T10): operations, competency questions,
conformance classes, and required invariants.

Checksum (sha256): `69a66f5a2ec1eaac42b4b82e28f800243dcc8047c20c6392ad86e05e756494c6`

Consumed by
[`tests/conformance/test_normative_alignment.py`](../../../tests/conformance/test_normative_alignment.py),
which fails if `fixtures/manifest.yaml` drifts from it in case coverage,
competency questions, conformance classes, or operation — unless the divergence
is explicitly declared under `normativeAlignment` with a rationale.

### `schemas/`

The 44 normative JSON Schema 2020-12 data models.

Tree checksum: recorded in [`schemas.sha256`](./schemas.sha256), recomputed and
compared by the test suite.

Consumed by
[`tests/conformance/test_schema_conformance.py`](../../../tests/conformance/test_schema_conformance.py),
which validates serialized results against them **as whole objects**, so
`additionalProperties: false` and every required field are enforced. Validating
field by field is what lets a representation drift from the contract while
appearing correct.

## Why vendored

The dependency direction is strictly `tier-graph-reference` → `tier-graph-api`.
Vendoring makes the conformance suite self-contained and pins exactly which
version of the contract the published results were produced against; the
checksums make a silent local edit detectable.
