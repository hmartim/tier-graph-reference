# Running the conformance suite

## Run it

```bash
python scripts/run_conformance.py            # writes results/, prints per-case status
python scripts/run_conformance.py --quiet    # only the final pass/fail line
```

Or as a module / console script:

```bash
python -m tier_graph_reference.conformance.runner
tier-conformance            # installed console entry point
```

Outputs (tracked, and checked against a fresh run by
`scripts/check_results_current.py`):

- `results/conformance-results.json` — machine-readable;
- `results/conformance-summary.md` — human-readable.

## What a run does

For each case the runner:

1. loads `input.json` into a `MemoryTierStore` (TIER objects only);
2. loads `profile-fixture.json` into a `FixtureGroundingProvider`;
3. builds a `ServiceContext` (store + grounding);
4. executes `request.json`'s operation via the same services the API uses;
5. compares the normalized result against `expected.json`;
6. records pass/fail, a deterministic explanation, and timing.

## Report shape

```jsonc
{
  "implements": "tier-graph-api v0.1.0-draft",
  "specificationVersion": "0.1.0-draft",
  "referenceImplementationVersion": "0.1.0",
  "fixtureSetVersion": "0.1.0",
  "executedAt": "2026-07-14T00:00:00Z",
  "total": 10, "passed": 10, "failed": 0,
  "conformanceClasses": [ /* rollup, see below */ ],
  "cases": [
    {
      "caseId": "T01", "operation": "getRelationHistory",
      "conformanceClass": "Query API Conformance",
      "implementationVersion": "0.1.0",
      "groundingProfileId": "public-legal-fixture",
      "groundingProfileVersion": "0.1.0",
      "caseDefinitionReference": { "repository": "tier-graph-api", "version": "0.1.0-draft", "path": "..." },
      "passed": true, "durationMs": 0.3,
      "expected": { }, "actual": { }, "explanation": []
    }
  ]
}
```

## Conformance classes

Results are reported **by class** rather than as one undifferentiated claim:

| Class | Source | Status in v0.1.0 |
|---|---|---|
| Core Model Conformance | T06, T07 | passed |
| Temporal Grounding Conformance | T05, T09 | passed |
| Query API Conformance | T01, T02, T03, T04 | passed |
| Path Conformance | T10 | passed |
| Authoring Conformance | T08 | **partial** |
| Analytical Extension Conformance | — | experimental |
| SAT-Graph Adapter Integration | `tests/adapters/sat_graph` | mocked |

The first five are computed from the executed cases. **Authoring is reported as
`partial`, not `passed`**: T08 executes `createEvidence` — evidence identity and
de-duplication — but the remaining authoring operations (`appendProvenanceActivity`,
`recordReviewEvent`) are out of scope for v0.1.0, so `passed 1/1` must not be read
as full coverage of the class. The rollup carries a `note` saying exactly that.

The last two are reported statically: analytical extensions (communities, causal
gates) are deliberately outside the core, and the SAT-Graph adapter is validated
separately with mocked HTTP responses. SAT-Graph integration is **not** a required
conformance class.

## The comparison rule

`expected.json` is a partial assertion. Formally, `diff(expected, actual)` is
empty iff:

- for every key in an expected object, the key exists in the actual object and
  its value matches (recursively) — extra actual keys are ignored;
- expected and actual arrays have equal length and match element-by-element;
- scalars are equal.

This is implemented in `conformance/compare.py` and unit-tested in
`tests/unit/test_compare.py`.

Because `expected.json` asserts only what it declares, a *computed* field that no
fixture asserts changes nothing. Every invariant reported by a case is computed
from the executed run — never a literal, never an echo of the request arguments —
and each is covered by a falsifying mutation in
`tests/conformance/test_assertions_are_falsifiable.py`, which must turn its case
red on the field announcing the violated property.

## Normative alignment

`tier-graph-api` **defines** conformance; this repository **executes** it.
`tests/conformance/test_normative_alignment.py` cross-checks
`fixtures/manifest.yaml` against the vendored normative catalogue at
[`vendor/tier-graph-api/0.1.0-draft/conformance/manifest.yaml`](../vendor/tier-graph-api/0.1.0-draft/README.md):
case coverage, directory slugs, competency questions, conformance classes, and
the operation under test.

An implementation may legitimately satisfy a case with a different operation. The
rule is that **no divergence may be silent** — anything that differs must be
declared under `normativeAlignment` with a status and a rationale:

| Status | Meaning |
|---|---|
| `subsumes` | The executed operation is strictly stronger than the normative one. |
| `covered-by-invariant` | The normative property is asserted as a computed invariant of another operation; `coveredBy` names the fields. |
| `gap` | **The normative behaviour is not executed.** The case passes its fixture but does not demonstrate the normative operation. |

Current divergences (also printed in `conformance-summary.md` under
*Normative alignment*, and marked `†` in the case table):

| Case | Normative | Executed | Status |
|---|---|---|---|
| T01 | `getRelationStateAtTime` | `getRelationHistory` | `subsumes` |
| T07 | `compareRelationIdentity` | `getRelationStateAtTime` | `covered-by-invariant` |
| T09 | `evaluateSourceStateAdmissibility` | `getRelationStateAtTime` | `covered-by-invariant` |

**There are no open gaps.** `_DECLARED_GAPS` in the alignment test is empty and
pinned, so a new one cannot appear silently.

`subsumes` is not taken on trust either: `test_subsumption_is_executed_not_merely_declared`
verifies that the normative operation's answer is *derivable* from the executed
one — for probe instants around every source-state boundary, the state of the
history segment covering an instant must equal what `getRelationStateAtTime`
reports there. A declaration alone would be a human judgement, not a property.


## Limitations of fixture-based validation

- The fixture provider is single-perspective: `observerTime` (transaction time)
  is accepted for interface parity but does not vary fixture data.
- Fixtures are minimal by design; they assert the invariant a case targets, not
  exhaustive behavior.
- Passing the fixture suite demonstrates conformance of the *implementation
  against the pinned specification draft*. It is not a certification of the
  normative specification itself, which lives in `tier-graph-api`.
