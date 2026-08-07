# T07 — Positive and negative propositions remain distinct

**Operation:** `getRelationStateAtTime`  
**Competency questions:** CQ2, CQ3

## Purpose

Tests the separation between proposition polarity and evidence stance.

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
