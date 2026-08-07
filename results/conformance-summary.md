# TIER-Graph conformance summary

- **Implements:** tier-graph-api v0.1.0-draft
- **Specification version:** 0.1.0-draft
- **Reference implementation:** v0.1.0
- **Fixture set:** v0.1.0
- **Executed at:** 2026-08-07T17:49:03Z
- **Result:** 10/10 passed (0 failed)

## Conformance classes

> Two different measures, easily confused. **Case-operation gaps** counts conformance *cases* whose normative operation is not executed (see *Normative alignment* below). **Class coverage** is whether every operation belonging to a class is implemented. Zero gaps does not imply full class coverage.

| Class | Status | Passed | Total |
|---|---|---|---|
| Authoring Conformance | partial | 1 | 1 |
| Core Model Conformance | passed | 2 | 2 |
| Path Conformance | passed | 1 | 1 |
| Query API Conformance | passed | 4 | 4 |
| Temporal Grounding Conformance | passed | 2 | 2 |
| Analytical Extension Conformance | experimental | - | - |
| SAT-Graph Adapter Integration | mocked | - | - |

- **Authoring Conformance** — Partially covered: createEvidence (evidence identity and de-duplication) is implemented and exercised by T08. The remaining authoring operations (appendProvenanceActivity, recordReviewEvent) are out of scope for v0.1.0.

## Cases

| Case | Operation | Class | Result | Duration (ms) |
|---|---|---|---|---|
| T01 † — Persistent relation across successive source states | `getRelationHistory` | Query API Conformance | PASS | 1.372 |
| T02 — Relation introduced in a later source state | `getRelationStateAtTime` | Query API Conformance | PASS | 0.786 |
| T03 — One evidence unit supports several relations | `getRelationsByEvidenceUnit` | Query API Conformance | PASS | 0.018 |
| T04 — Withdrawn historical precondition | `getRelationStateAtTime` | Query API Conformance | PASS | 0.217 |
| T05 — Composite cross-item support | `evaluateEvidenceAdmissibility` | Temporal Grounding Conformance | PASS | 0.065 |
| T06 — Unknown versus absent qualifier | `compareRelationIdentity` | Core Model Conformance | PASS | 0.04 |
| T07 † — Positive and negative propositions remain distinct | `getRelationStateAtTime` | Core Model Conformance | PASS | 0.191 |
| T08 — Re-extraction does not duplicate evidence | `createEvidence` | Authoring Conformance | PASS | 0.244 |
| T09 † — Prospective applicability after vacatio | `getRelationStateAtTime` | Temporal Grounding Conformance | PASS | 0.11 |
| T10 — Anachronistic path exclusion | `findAdmissiblePaths` | Path Conformance | PASS | 0.398 |

## Normative alignment (†)

- **Normative case-operation gaps: 0**
- Cases diverging from the catalogue's operation: 3 of 10

These cases run a different operation than the normative catalogue in `tier-graph-api` specifies. Every divergence is declared; see `fixtures/manifest.yaml`.

| Case | Normative operation | Executed operation | Status |
|---|---|---|---|
| T01 | `getRelationStateAtTime` | `getRelationHistory` | subsumes |
| T07 | `compareRelationIdentity` | `getRelationStateAtTime` | covered-by-invariant |
| T09 | `evaluateSourceStateAdmissibility` | `getRelationStateAtTime` | covered-by-invariant |

