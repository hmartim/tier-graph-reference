# Privacy boundary

This repository demonstrates the TIER-Graph API **without publishing any private
SAT-Graph database**, ingestion pipeline, curation environment, credentials, or
production configuration.

## Must not appear here

- the author's complete SAT-Graph SQLite database;
- production `item`, `version`, `text_unit`, or `action` tables;
- applicability/validity interval tables from the source substrate;
- private ingestion or curation code;
- internal identifiers not intended for disclosure;
- production API credentials, `.env` files, or production configuration;
- confidential or restricted source documents.

## May appear here

- public TIER entities, relations, and evidence records;
- opaque illustrative evidence-unit identifiers;
- minimal, test-specific mappings from evidence units to source states;
- minimal, test-specific admissibility intervals (in `profile-fixture.json`);
- public legal quotations within licensing/quotation limits;
- expected temporal results;
- a small SQLite file containing only the TIER-derived layer (rebuilt on demand);
- an adapter skeleton showing how a real SAT-Graph API could be called;
- a fixture-backed grounding profile implemented from public test data.

## Why fixture grounding does not disclose the private database

`profile-fixture.json` is a **minimal fixture-backed temporal grounding profile
used for reproducible conformance testing**. It is not a SAT-Graph database and
not a complete SAT-Graph export. It contains only the few source-state
admissibility facts a given test needs, expressed abstractly as:

```
EvidenceUnitRef  →  SourceStateRef  →  temporal admissibility
```

The runner never learns that, in some private environment, those roles are played
by SAT-Graph `TextUnit` and `Version` objects. That knowledge lives only in the
optional SAT-Graph adapter and is exercised separately with mocked responses.

## No copied authoritative temporal state

The TIER store never persists source validity/applicability intervals on
`DerivedRelation`. Intervals inside `profile-fixture.json` belong to the fixture
grounding provider, not to the TIER-derived data layer. The conformance runner
computes a `copiedRelationIntervals` invariant and asserts it stays `0`.

No grounding cache is implemented in this release. If one were added, it would be
clearly labelled as a cache (profile id + version, retrieval time, source
revision/observer time, invalidation metadata) and never presented as the
authoritative temporal source.

## Enforcement

- **`.gitignore`** blocks `*.db`, `*.sqlite`, `*.sqlite3`, `*.duckdb`, `.env`,
  `.env.*`, `credentials*`, `secrets/`, `data/private/`, `data/local/`.
- **`scripts/reject_private_artifacts.py`** actively fails the build (in CI and
  locally) if any such artifact exists in the tree.
- **`SQLiteTierStore.assert_no_source_tables()`** verifies the TIER-only schema
  never contains source-substrate tables.
