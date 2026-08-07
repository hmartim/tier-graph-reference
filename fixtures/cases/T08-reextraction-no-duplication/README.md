# T08 — Re-extraction does not duplicate evidence

**Operation:** `createEvidence`  
**Competency questions:** CQ2

## Purpose

Tests evidence identity and provenance accumulation across repeated pipeline executions.

The case **replays the re-extraction** rather than reading back a prepared result:
`input.json` starts with *no* evidence, and `request.json` submits the same
evidential basis twice — same relation, same anchor, same selector, same stance —
under two different provenance activities, with a deliberately different candidate
`id` on the second submission. Whether that second submission creates a new record
or appends to the existing occurrence is decided by
`EvidenceAuthoringService.create_evidence`, not by the fixture.

`distinctSubmittedKeyCount: 1` is the non-vacuity witness: it proves the two
submissions really did share one `EvidenceKey`. Without it the case could pass on
submissions that merely happened to differ, demonstrating nothing about
de-duplication.

## Public-data boundary

`input.json` contains only TIER-derived entities, relations, evidence, and provenance.  
`profile-fixture.json` is a minimal test-specific grounding profile. It is not a copy of a production SAT-Graph database.

## Files

- `input.json` — TIER-derived objects (entities and the relation only; evidence is created by the run).
- `profile-fixture.json` — minimal evidence-unit ownership and source-state admissibility facts.
- `request.json` — the two `createEvidence` submissions.
- `expected.json` — normalized expected result.

## Temporal convention

Intervals are half-open: `[admissibleFrom, admissibleTo)`. A missing `admissibleTo` means open-ended.
