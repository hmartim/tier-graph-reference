#!/usr/bin/env python3
"""Validate the public fixtures: structure, JSON, schema, and TIER semantics.

Checks, per case:

1. all required files present and valid JSON;
2. case metadata validates against ``fixtures/fixture.schema.json``;
3. ``input.json`` loads into the TIER models (no source-substrate leakage);
4. ``profile-fixture.json`` loads into the grounding models;
5. the case's operation is one the runner can execute.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401  (adds src/ to sys.path when run from a checkout)

REQUIRED_FILES = (
    "README.md",
    "input.json",
    "profile-fixture.json",
    "request.json",
    "expected.json",
)


def _load_schema(fixtures_dir: Path) -> dict | None:
    schema_path = fixtures_dir / "fixture.schema.json"
    if not schema_path.exists():
        return None
    return json.loads(schema_path.read_text(encoding="utf-8"))


def main() -> int:
    from tier_graph_reference.conformance.operations import supported_operations
    from tier_graph_reference.grounding.fixture import FixtureGroundingProvider
    from tier_graph_reference.store.memory import MemoryTierStore

    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    cases_dir = fixtures_dir / "cases"
    schema = _load_schema(fixtures_dir)
    operations = set(supported_operations())

    failures: list[str] = []
    checked = 0

    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        present = {p.name for p in case_dir.iterdir() if p.is_file()}
        missing = set(REQUIRED_FILES) - present
        if missing:
            failures.append(f"{case_dir.name}: missing {sorted(missing)}")
            continue

        try:
            payloads = {
                name: json.loads((case_dir / name).read_text(encoding="utf-8"))
                for name in REQUIRED_FILES
                if name.endswith(".json")
            }
        except json.JSONDecodeError as exc:
            failures.append(f"{case_dir.name}: invalid JSON: {exc}")
            continue

        if schema is not None:
            try:
                import jsonschema

                jsonschema.validate(payloads["input.json"], schema)
            except Exception as exc:
                failures.append(f"{case_dir.name}: schema validation failed: {exc}")

        try:
            MemoryTierStore.from_input(payloads["input.json"])
        except Exception as exc:
            failures.append(f"{case_dir.name}: input.json does not load into TIER models: {exc}")

        try:
            FixtureGroundingProvider.from_dict(payloads["profile-fixture.json"])
        except Exception as exc:
            failures.append(f"{case_dir.name}: profile-fixture.json invalid: {exc}")

        operation = payloads["request.json"].get("operation")
        if operation not in operations:
            failures.append(f"{case_dir.name}: unknown operation {operation!r}")

        checked += 1

    if failures:
        print("Fixture validation FAILED:")
        for line in failures:
            print(f"  - {line}")
        return 1

    print(f"All {checked} fixtures are structurally, schematically, and semantically valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
