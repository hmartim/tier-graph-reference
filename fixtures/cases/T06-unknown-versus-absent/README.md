# T06 — Unknown versus absent qualifier

**Operation:** `compareRelationIdentity`  
**Competency questions:** CQ5

## Purpose

Tests conservative relation identity: unresolved truth-conditional qualification blocks automatic merging.

## Public-data boundary

`input.json` contains only TIER-derived entities, relations, evidence, and provenance.  
`profile-fixture.json` is a minimal test-specific grounding profile. It is not a copy of a production SAT-Graph database.

## Files

- `input.json` — TIER-derived objects.
- `profile-fixture.json` — minimal evidence-unit ownership and source-state admissibility facts.
- `request.json` — operation and arguments.
- `expected.json` — normalized expected result.

## Temporal convention

Intervals are half-open: `[admissibleFrom, admissibleTo)`. A missing `admissibleTo` means open-ended.
