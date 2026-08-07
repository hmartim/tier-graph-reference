# Architecture

## Two repositories, one direction

```
tier-graph-api
   normative schemas and operations
                |
                v
tier-graph-reference        (this repository)
   core services and TIER store
                |
                v
   TemporalGroundingProvider
      /                    \
Fixture provider       SAT-Graph adapter
   required for          optional legal
   conformance             integration
```

- **`tier-graph-api`** is the *sole* normative source: object semantics, JSON
  models, API operations, relation identity, evidence semantics, temporal
  grounding requirements, conformance-case definitions, and admission-policy
  semantics.
- **`tier-graph-reference`** is *one* implementation of that specification. The
  dependency direction is strictly `tier-graph-reference → tier-graph-api`, never
  the reverse. This repository does not redefine normative semantics; where
  implementation docs explain a rule, they refer to the corresponding
  specification section.
- **SAT-Graph** is *one optional* legal grounding adapter. The reference
  implementation works with any `TemporalGroundingProvider`; conformance is
  demonstrated entirely on the built-in fixture provider.

The implemented specification version is pinned at **`tier-graph-api`
v0.1.0-draft**; the vendored copy and its checksums are documented in
[../vendor/tier-graph-api/0.1.0-draft/README.md](../vendor/tier-graph-api/0.1.0-draft/README.md).

## TIER vs. SAT-Graph

**TIER** (Temporally Indexed Evidence-Linked Relations) is a layer of *derived
relations* whose evidential status is a function of time. **SAT-Graph** is one
possible *source substrate* that can ground those relations in real legal
sources. They are deliberately separate:

| Concern | TIER-derived layer | Source substrate (e.g. SAT-Graph) |
|---|---|---|
| Objects | entities, relations, evidence, provenance, reviews, policies | items, versions, text units, actions |
| Time | *derived* through grounding | *authoritative* validity/applicability intervals |
| Stored here | yes (`TierStore`) | never |
| Accessed how | directly | only through a `TemporalGroundingProvider` |

The core never imports a source-substrate model. An evidence anchor carries only
an opaque `EvidenceUnitRef` (`profileId` + `evidenceUnitId`); the grounding
provider alone knows how to resolve it and decide admissibility.

## Layers

```
             ┌─────────────────────────────────────────────┐
   query →   │  Services (pure functions of store+grounding)│
             │  identity · admissibility · relation-state   │
             │  projection · paths · audit                  │
             └───────────────┬───────────────┬──────────────┘
                             │               │
                   reads TIER objects   "admissible at t?"
                             │               │
                   ┌─────────▼──────┐  ┌──────▼───────────────────┐
                   │   TierStore    │  │ TemporalGroundingProvider │
                   │ memory │ sqlite│  │ fixture │ sat-graph-http  │
                   └────────────────┘  └───────────────────────────┘
```

### Models (`models/`)
Pydantic v2 models that **implement** the normative object model. Identifiers are
opaque strings; identity is never derived from mutable labels. `DerivedRelation`
carries no temporal interval — a verified invariant.

### Store (`store/`)
`TierStore` is the abstract read boundary; `WritableTierStore` adds authoring.
`MemoryTierStore` is the default. `SQLiteTierStore` is an optional TIER-only
relational store whose schema contains no source-substrate tables.

### Grounding (`grounding/`)
`TemporalGroundingProvider` owns all admissibility semantics.
`FixtureGroundingProvider` reads a `profile-fixture.json`. The optional
`SatGraphHttpGroundingProvider` lives under `adapters/sat_graph/` and is
re-exported at `grounding.sat_graph_http` for convenience.

### Services (`services/`)
Each service receives its store and grounding provider by dependency injection
(`ServiceContext.build`). No core service imports a SAT-Graph model.

- **identity** — conservative relation-identity comparison.
- **admissibility** — conjunctive evidence admissibility.
- **relation_state** — evidential state and history.
- **projection** — the time-indexed set of admitted relations.
- **paths** — admissible-path search over the projection, with exclusion
  explanations.
- **audit** — structured trails.

### Conformance (`conformance/`)
`loader` reads the manifest and cases; `operations` dispatches each fixture
operation to the services; `compare` performs partial-match comparison; `runner`
executes the suite and `report` renders the JSON + Markdown reports with the
version pin and per-class rollup.

### API (`api/`)
An **optional** FastAPI facade. Handlers are thin: they call the same services as
the offline runner. The generated OpenAPI is an implementation artifact, not the
normative source; operational endpoints (e.g. `/healthz`) are non-normative.

## Key invariants

The normative statement of these lives in the specification
([`tier-graph-api`](https://github.com/hmartim/tier-graph-api), `spec/00`–`spec/13`);
this repository must conform to it. The load-bearing ones:

1. TIER store separate from every source substrate.
2. No authoritative intervals copied onto `DerivedRelation`.
3. Conjunctive evidence within one record; alternatives as separate records.
4. `unknown` ≠ `absent`; unresolved identity-bearing qualifier blocks merge.
5. Polarity (proposition) separate from stance (evidence).
6. Evidential state ∈ {supported, refuted, contested, unsupported}.
7. Path candidates from the projection, not an all-time graph filtered afterward.
