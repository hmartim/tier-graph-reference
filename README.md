# TIER-Graph Reference Implementation

**TIER** — **T**emporally **I**ndexed **E**vidence-**L**inked **R**elations.

> **Implements:** `tier-graph-api` **v0.1.0-draft** — see
> [Specification dependency](#specification-dependency).

A minimal, well-tested reference implementation of the TIER-Graph API together
with an executable public conformance suite. It shows how the specification can
be implemented **without publishing any private SAT-Graph database**, ingestion
pipeline, curation environment, credentials, or production configuration.

> This repository is **not** the normative specification. Normative definitions
> live in [`tier-graph-api`](https://github.com/hmartim/tier-graph-api).
> This repository implements and tests a versioned release of that specification
> and clearly marks any implementation-specific choices.

The dependency direction is strictly **`tier-graph-reference` → `tier-graph-api`**,
never the reverse. SAT-Graph is **one optional legal grounding adapter**, not a
prerequisite: the reference implementation runs against any
`TemporalGroundingProvider`, and all public conformance runs on the built-in
fixture provider.

```
              tier-graph-api
        normative schemas and operations
                     │
                     ▼
            tier-graph-reference
         core services and TIER store
                     │
                     ▼
          TemporalGroundingProvider
             /                    \
     Fixture provider        SAT-Graph adapter
      required for              optional legal
       conformance                integration
```

## What TIER-Graph is

TIER-Graph is a layer of **derived relations** between entities, where each
relation's evidential status is a function of *time*. Rather than storing "fact X
is true from date A to date B", TIER records:

- a **`DerivedRelation`** (source → predicate → target, plus truth-conditional
  qualifiers) — a proposition, with **no** temporal interval of its own;
- one or more **`RelationEvidence`** records, each anchored to one or more
  **evidence units** in an external source;
- a pluggable **temporal grounding profile** that says *when each source state is
  admissible*.

A relation's **evidential state** at a time `t` (`supported`, `refuted`,
`contested`, `unsupported`) is then *computed* from which evidence is admissible
at `t`. Temporal truth is never copied onto the relation; it is always derived
through grounding. This is what makes histories, projections, and path queries
reproducible and auditable.

## Why the split between two repositories

| Repository | Role |
|---|---|
| `tier-graph-api` | Normative spec: concepts, OpenAPI, JSON Schema, ontology/SHACL, conformance-case definitions. |
| `tier-graph-reference` (this) | One executable implementation, the public fixtures, a conformance runner, and expected/actual results. |

The normative repository defines *what conformance means*; this repository
*demonstrates one way to satisfy it* without binding the spec to a language.

## Architecture at a glance

```
             ┌─────────────────────────────────────────────┐
   query →   │  Services                                    │
             │  identity · admissibility · relation-state   │
             │  projection · paths · audit                  │
             └───────────────┬───────────────┬──────────────┘
                             │               │
                   reads TIER objects   asks "admissible at t?"
                             │               │
                   ┌─────────▼──────┐  ┌──────▼───────────────────┐
                   │   TierStore    │  │ TemporalGroundingProvider │
                   │ memory │ sqlite│  │ fixture │ sat-graph-http  │
                   └────────────────┘  └───────────────────────────┘
                    TIER-derived only    external grounding facts
```

The two boundaries never mix: the **store** holds only TIER-derived objects; the
**grounding provider** owns all temporal admissibility semantics. See
[docs/architecture.md](docs/architecture.md).

## Quick start

```bash
py -m venv .venv                    # Windows: py   ·   elsewhere: python3 -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell   ·   bash: source .venv/bin/activate
pip install -e ".[dev]"

python scripts/validate_fixtures.py       # validate the 10 public fixtures
python scripts/run_conformance.py         # run T01–T10, write results/
python scripts/check_results_current.py   # published results must match a fresh run
python scripts/reject_private_artifacts.py  # no private artifact is tracked
pytest                                    # unit + integration + conformance tests
ruff check .                              # lint
mypy src                                  # type-check
```

Optional HTTP facade:

```bash
uvicorn tier_graph_reference.api.app:app --reload
# then open http://127.0.0.1:8000/docs
```

The full set of install/test commands (including optional extras) is collected in
[docs/commands.md](docs/commands.md).

## Conformance cases

| ID | Focus | Operation |
|----|-------|-----------|
| T01 | Persistent relation across successive source states | `getRelationHistory` |
| T02 | Relation introduced in a later source state | `getRelationStateAtTime` |
| T03 | One evidence unit supports several relations | `getRelationsByEvidenceUnit` |
| T04 | Withdrawn historical precondition | `getRelationStateAtTime` |
| T05 | Composite cross-item (conjunctive) support | `evaluateEvidenceAdmissibility` |
| T06 | Unknown vs. absent qualifier | `compareRelationIdentity` |
| T07 | Positive vs. negative proposition remain distinct | `getRelationStateAtTime` |
| T08 | Re-extraction does not duplicate evidence | `createEvidence` |
| T09 | Prospective applicability after *vacatio* | `getRelationStateAtTime` |
| T10 | Anachronistic path exclusion | `findAdmissiblePaths` |

Running the suite writes `results/conformance-results.json` (machine-readable)
and `results/conformance-summary.md` (human-readable). See
[docs/conformance.md](docs/conformance.md).

## Privacy boundary

This repository **must not** contain any private SAT-Graph database, production
`item` / `version` / `text_unit` / `action` tables, credentials, or `.env`
files. Public fixtures carry only TIER-derived objects plus a minimal
`profile-fixture.json` of grounding facts, which is a reproducibility artifact —
not a copy of a production source database. The boundary is enforced by
`.gitignore` and by `scripts/reject_private_artifacts.py` in CI. See
[docs/privacy-boundary.md](docs/privacy-boundary.md).

## Specification dependency

This implementation is pinned to **`tier-graph-api` v0.1.0-draft**.

- The version string `0.1.0-draft` appears in package metadata, the fixture
  manifest, and every conformance report.
- The normative **conformance catalogue** and the 44 normative **JSON Schemas**
  are vendored verbatim under
  [`vendor/tier-graph-api/0.1.0-draft/`](vendor/tier-graph-api/0.1.0-draft/README.md),
  with checksums recorded. `tests/conformance/test_normative_alignment.py`
  cross-checks the fixture manifest against the catalogue — case coverage, slugs,
  competency questions, conformance classes, and the operation under test — so
  drift between the two repositories fails the build. Divergences are permitted
  but must be **declared**, never silent.
  `tests/conformance/test_schema_conformance.py` validates serialized results
  against the vendored schemas as whole objects.
- The Pydantic models **implement** the specification's objects; they do not add,
  remove, or reinterpret normative fields. Any implementation-only field is
  marked non-normative and namespaced under `x-tier-reference`.

## Documentation

- [docs/architecture.md](docs/architecture.md) — spec vs. implementation, TIER vs. SAT-Graph, layers.
- [docs/privacy-boundary.md](docs/privacy-boundary.md) — what may and may not appear here.
- [docs/fixture-format.md](docs/fixture-format.md) — the four-file fixture format.
- [docs/conformance.md](docs/conformance.md) — how to run and read the suite.
- [docs/sat-graph-adapter.md](docs/sat-graph-adapter.md) — the optional HTTP grounding adapter.
- [docs/development.md](docs/development.md) — environment, TIER-only SQLite, limitations.

## License

[Apache-2.0](LICENSE).
