#!/usr/bin/env python3
"""Build a TIER-only sample SQLite database from the public fixtures.

The database contains only TIER-derived tables (no SAT-Graph source substrate).
It is written under ``build/`` and is intentionally NOT committed (see
``.gitignore``); rebuild it on demand. External references remain opaque strings.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401  (adds src/ to sys.path when run from a checkout)


def main(argv: list[str] | None = None) -> int:
    from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest
    from tier_graph_reference.store.memory import MemoryTierStore
    from tier_graph_reference.store.sqlite import SQLiteTierStore

    parser = argparse.ArgumentParser(description="Build a TIER-only sample SQLite database.")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "build" / "sample-tier.db"),
    )
    args = parser.parse_args(argv)

    manifest = load_manifest(default_fixtures_dir())

    merged = MemoryTierStore()
    for case in manifest.cases:
        source = MemoryTierStore.from_input(case.input)
        for entity in source.list_entities():
            merged.put_entity(entity)
        for relation in source.list_relations():
            merged.put_relation(relation)
        for evidence in source.list_evidence():
            merged.put_evidence(evidence)
        for activity in source.list_provenance_activities():
            merged.put_provenance_activity(activity)
        for policy in source.list_policies():
            merged.put_policy(policy)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    store = SQLiteTierStore.create(out_path, source=merged)
    store.assert_no_source_tables()
    tables = sorted(store.table_names())
    store.close()

    print(f"Built TIER-only sample database: {out_path}")
    print(f"  entities:   {len(merged.list_entities())}")
    print(f"  relations:  {len(merged.list_relations())}")
    print(f"  evidence:   {len(merged.list_evidence())}")
    print(f"  tables:     {', '.join(tables)}")
    print("  source-substrate tables: none (verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
