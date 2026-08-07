# T09 — Prospective applicability after vacatio

**Operation:** `getRelationStateAtTime`  
**Competency questions:** CQ3, CQ6

## Purpose

Tests that publication does not replace the grounding profile's applicability boundary.

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
