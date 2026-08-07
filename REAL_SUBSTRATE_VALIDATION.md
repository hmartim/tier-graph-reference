# Real-substrate validation record (sanitized)

This file is the public, auditable record of a grounding and
temporal-projection run executed against a **curated, non-public SAT-Graph
instance** of Brazilian constitutional norms, through the SAT-Graph HTTP
adapter in this repository (`src/tier_graph_reference/adapters/sat_graph/`).

The public conformance baseline remains the fixture-based suite T01–T10 in
this repository, which is independently reproducible. The run recorded here
is **additional** validation over a real substrate: it cannot be reproduced
by third parties (the curated database is not publicly distributable), but
its execution is identifiable, dated, and bound to specific code versions
and to public legal facts, so the aggregate claims can be audited.

## Execution summary

| Field | Value |
|---|---|
| Execution date (UTC) | `2026-08-06T20:18:04Z` |
| Grounding profile | `sat-graph-curated`, version `2026-08-05` |
| Cases executed | SAT-T01, SAT-T02, SAT-T04, SAT-T10 (mirroring public T01, T02, T04, T10) |
| Result | **4/4 PASS** |
| Response-manifest SHA-256 | `5ec7b6fbb9d3505fff28a7695654e7bd2b6ad7a82ea8eca95be391591d738692` |
| Implementation version | `tier-graph-reference` `v0.1.0` (the tag resolves to the release commit) |
| SAT-Graph API version | `0.1.0` |
| Substrate revision | recorded internally (private) |

The manifest hash is a SHA-256 over the **structural** fields of the API
responses only (relation ids, states, intervals, evidence-record ids,
exclusion reason codes) — it contains no normative text and no internal
substrate identifiers, and does not reveal the database contents.


## What was validated

Assertions are semantic and anchored in the public amendment dates listed
below, never in frozen copies of previous outputs. Each case checks the same
ontological property as its public counterpart, including the computed
invariants the public suite asserts.

- **SAT-T01** (`getRelationHistory`): the full state history of a derived
  relation over Article 6 of the 1988 Brazilian Constitution, partitioned
  exactly at the public amendment boundaries, each period `supported` by the
  evidence record of its own textual state, the final period open-ended, and
  no source interval copied into the derived layer.
- **SAT-T02** (`getRelationStateAtTime`): point-in-time evaluation before
  and after a constitutional amendment introduced a new social right
  (`unsupported` → `supported`), with publication dates not controlling
  admissibility.
- **SAT-T04** (`getRelationStateAtTime`): a proposition made obsolete by a
  constitutional amendment (Article 226 §6, prior-separation requirement
  for divorce) transitioning `supported` → `unsupported`. Retention is
  checked **separately** from the state transition and from review status:
  the evidence admissible before the amendment is re-read from the store and
  must still exist, must be temporally inadmissible afterwards, and must not
  have been retired curatorially — so the withdrawal is demonstrably a
  consequence of source-state temporality rather than of deletion.
- **SAT-T10** (`findAdmissiblePaths`): temporal-topology admissibility — a
  multi-relation path excluded at a query instant where one supporting
  evidence unit resolves to a non-admissible source state
  (`EVIDENCE_SOURCE_STATE_NOT_ADMISSIBLE`), and admitted at a later instant.
  Returning no path is *also* what an all-time traversal followed by
  post-hoc filtering would produce, so the instrumented traversal trace is
  asserted as well: candidate generation was offered only relations
  belonging to the temporal projection, touched no inadmissible relation,
  and was never offered the future-only relation. The projection is verified
  to be non-trivial at the earlier instant, without which the trace would
  prove nothing. Each returned step is additionally checked to carry its own
  evidential state: admission by a policy is not evidential support, and a
  path answer that drops the per-step state cannot distinguish the two.

## Public legal boundaries used in assertions

| Date | Public fact |
|---|---|
| 1988-10-05 | Promulgation of the Brazilian Federal Constitution |
| 2000-02-14 | EC 26/2000 — housing added to Article 6 |
| 2010-02-04 | EC 64/2010 — food added to Article 6 |
| 2010-07-13 | EC 66/2010 — Article 226 §6 amended (prior-separation requirement for divorce removed) |
| 2015-09-15 | EC 90/2015 — transportation added to Article 6 |

## Temporal convention of this profile

The curated SAT-Graph profile uses **inclusive, date-granular** interval
endpoints `[start, end]`. The public fixture profile
(`public-legal-fixture`) uses **half-open datetime** intervals
`[start, end)`. Both are valid: the TIER-Graph grounding contract does not
prescribe how a profile represents source states, and the adapter preserves
the convention each profile declares rather than normalizing one into the
other. The difference is stated here so that the half-open assertions in the
public suite and the inclusive-endpoint finding below are not read as
inconsistent.

## Defect surfaced by this integration

Bringing the adapter up against the curated substrate surfaced a defect in
the substrate's admissibility endpoint: an **exclusive** end-date comparison
applied to **inclusive** date-granular interval ends produced a one-day
admissibility gap at every amendment boundary (a version whose end date is
`2000-02-13` is applicable through that entire day). The fix — making the
comparison inclusive at date granularity — was applied in
the substrate and is covered there by a regression test. The run recorded
above executes against the corrected substrate and reproduces the amendment
boundaries exactly.

This is reported as an integration finding about the substrate's
admissibility endpoint, not as a general evaluation of the platform. It is
an instance of the class of temporal error that a point-in-time profile is
meant to make observable.

## What is intentionally not published

- The curated database and any normative text contents.
- Internal substrate identifiers (item, version, and text-unit ids).
- The raw per-case response payloads and the private runner/overlay
  (kept outside version control under `data/private/`).
