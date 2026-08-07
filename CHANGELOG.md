# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-07

First public release. Implements `tier-graph-api` **v0.1.0-draft**.

### Added

#### Model and storage

- Pydantic models for the TIER-derived layer — entities, qualifiers, relations,
  evidence, provenance activities, review events — and for query results:
  admissibility, evidential-state snapshots, relation history, projected
  relations, paths, and exclusion explanations. `DerivedRelation` carries no
  temporal interval of its own, and `extra="forbid"` makes an attempt to add one
  a validation error.
- `TierStore` storage boundary with an in-memory implementation
  (`MemoryTierStore`) and an optional TIER-only SQLite implementation
  (`SQLiteTierStore`). The SQLite schema contains no SAT-Graph source tables.
- `EvidenceKey` — `⟨relationId, anchors, stance⟩`, with anchors canonicalized to
  a sorted de-duplicated set and selectors participating in identity. `role`,
  provenance activity, model, confidence, generation time, and review status are
  deliberately excluded.

#### Grounding

- Pluggable `TemporalGroundingProvider` interface with a fixture-backed provider
  (`FixtureGroundingProvider`) used by every public conformance run, and an
  optional `SatGraphHttpGroundingProvider` adapter, mocked in tests.
- `AdmissionPolicy` completing the policy pair `π = ⟨Π_review, A_state⟩`.
  `rejected` and `superseded` review statuses are excluded as a core invariant no
  policy may relax; the choice between `{accepted}` and `{proposed, accepted}` is
  declared per policy. All ten public fixtures declare
  `minimumReviewStatus: accepted`.

#### Services

- Relation identity comparison, evidence admissibility, relation evidential
  state, time-indexed projection, admissible path search, evidence authoring
  (`createEvidence`, find-or-append on the evidence key), and audit.
- `PathService.find_paths_traced` returning a `TraversalTrace`
  (`offeredRelationIds`, `visitedRelationIds`, `returnedRelationIds`,
  `projectedRelationIds`). Candidate generation is constrained **by** the
  time-indexed projection: conformance is containment (`offered ⊆ projected`),
  not equality, so an implementation that narrows further before traversing
  remains conformant.
- Paths preserve per-step evidential state. Admission by a policy is not
  evidential support, and `GroundedPath.is_supported` derives the positive
  reading without adding a field the normative schema does not allow.

#### Conformance

- Ten public conformance fixtures (T01–T10) and an executable runner producing
  `results/conformance-results.json` and `results/conformance-summary.md`, both
  tracked so the release can cite executed evidence.
- Every reported assertion is **computed from the executed run** — never a
  literal, never an echo of the request arguments — and each is accompanied by a
  non-vacuity witness, because `all([])` is `True`.
- `tests/conformance/test_assertions_are_falsifiable.py`: ten named mutations,
  each of which must turn its case red *on the field announcing the violated
  property*. A mutation that merely breaks something unrelated fails the test.
- `tests/conformance/test_normative_alignment.py`: cross-checks
  `fixtures/manifest.yaml` against the vendored normative catalogue — case
  coverage, slugs, competency questions, conformance classes, and the operation
  under test. Divergences are permitted but must be **declared** under
  `normativeAlignment` with a status (`subsumes` / `covered-by-invariant` /
  `gap`) and a rationale; the set of `gap` cases is pinned so a new one cannot
  appear silently. `subsumes` is verified, not taken on trust.
- `tests/conformance/test_schema_conformance.py`: validates serialized results
  against the vendored schemas **as whole objects**, so `additionalProperties:
  false` and every required field are enforced.
- `scripts/check_results_current.py`: re-runs the suite and fails if the tracked
  results no longer match, ignoring only execution time and per-case durations.
  It runs in CI *before* regeneration, so a commit that forgot to refresh
  `results/` fails instead of being silently overwritten.

#### Vendored specification

- The normative conformance catalogue and the 44 normative JSON Schemas from
  `tier-graph-api` `v0.1.0-draft`, byte-for-byte, under
  `vendor/tier-graph-api/0.1.0-draft/`, with sha256 checksums recomputed by the
  test suite.

#### Privacy boundary

- `scripts/reject_private_artifacts.py`: rejects tracked databases, credentials,
  key material, environment files, private data directories, and secret-shaped
  file content. It inspects what Git **tracks** — answering "will a private
  artifact be published?" rather than "does the researcher hold private data
  locally?" — with a working-tree fallback for non-Git checkouts.

#### Interfaces and documentation

- Optional FastAPI facade exposing the core query operations over the same
  services used by the offline runner.
- Documentation covering the specification/implementation split, the
  TIER/SAT-Graph privacy boundary, the fixture format, running conformance,
  building a TIER-only SQLite database, and configuring the SAT-Graph adapter.
