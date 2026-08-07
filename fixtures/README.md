# TIER-Graph Public Conformance Fixtures

This directory contains ten minimal, public, executable fixtures for the
`tier-graph-reference` repository.

The fixtures intentionally separate:

- `input.json`: TIER-derived entities, relations, evidence, and provenance;
- `profile-fixture.json`: minimal external grounding facts;
- `request.json`: the operation to execute;
- `expected.json`: the normalized expected result.

No production SAT-Graph database is included.

## Temporal convention

All intervals in **this** profile are half-open datetimes:
`[admissibleFrom, admissibleTo)`. A missing `admissibleTo` means open-ended.

**The convention belongs to the profile, not to the core.** The temporal
grounding contract does not prescribe how a profile represents source states; it
only requires that admissibility be decidable and reproducible. Two profiles used
with this implementation therefore differ, deliberately:

| Profile | Convention |
|---|---|
| `public-legal-fixture` (this pack) | half-open datetime intervals `[start, end)` |
| curated SAT-Graph profile (non-public) | **inclusive** date-granular endpoints `[start, end]` — a version whose end date is `2000-02-13` is applicable through that whole day |

The adapter preserves whatever convention a profile declares; it does not
normalize one into the other. This is why the boundary defect found during the
real-substrate run (an *exclusive* end-date comparison applied to *inclusive*
date-granular ends, see `REAL_SUBSTRATE_VALIDATION.md`) is not in tension with
the half-open assertions here — the two profiles are answering under different,
separately declared policies.

## Legal status

The constitutional examples use public legal facts and illustrative opaque
identifiers. The fixture profile is a compact conformance artifact, not an
official or complete publication of the Brazilian Constitution or SAT-Graph.

## Cases

- T01: persistent relation across source states;
- T02: later introduction;
- T03: one evidence unit supporting several relations;
- T04: withdrawn historical precondition;
- T05: composite cross-item evidence;
- T06: unknown versus absent qualifier;
- T07: positive versus negative proposition;
- T08: re-extraction without duplicate evidence;
- T09: prospective applicability after vacatio;
- T10: anachronistic path exclusion.
