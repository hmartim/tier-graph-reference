# T10 — Anachronistic path exclusion

**Operation:** `findAdmissiblePaths`  
**Competency questions:** CQ7, CQ8

## Purpose

Tests temporal-topology admissibility: an all-time path must not influence retrieval before every step is admissible.

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
