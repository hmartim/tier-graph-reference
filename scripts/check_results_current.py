#!/usr/bin/env python3
"""Fail if the published conformance outputs are stale.

The release cites `results/conformance-results.json` and
`results/conformance-summary.md` as the executed evidence, so they must be
tracked -- a claim that points at a gitignored file is not a claim. The obvious
objection to committing generated output is that it silently goes stale; this
script removes the objection by making staleness a build failure instead of a
matter of discipline.

It re-runs the suite in memory and compares against what is committed, ignoring
only the two genuinely volatile fields (wall-clock execution time and per-case
duration). Anything else differing means the committed outputs no longer describe
the code.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import _bootstrap  # noqa: F401  (adds src/ to sys.path when run from a checkout)

_NORMALIZED = "<normalized>"
_EXECUTED_AT = re.compile(r"^- \*\*Executed at:\*\* .*$", re.MULTILINE)
_DURATION_CELL = re.compile(r"\| [0-9]+\.?[0-9]* \|$", re.MULTILINE)


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(report))
    normalized["executedAt"] = _NORMALIZED
    for case in normalized.get("cases", []):
        case["durationMs"] = 0
    return normalized


def _normalize_summary(text: str) -> str:
    text = _EXECUTED_AT.sub(f"- **Executed at:** {_NORMALIZED}", text)
    text = _DURATION_CELL.sub("| 0 |", text)
    # write_reports appends a trailing newline that build_summary_md does not emit.
    return text.rstrip("\n")


def main() -> int:
    from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest
    from tier_graph_reference.conformance.report import build_summary_md
    from tier_graph_reference.conformance.runner import run_suite

    root = Path(__file__).resolve().parents[1]
    json_path = root / "results" / "conformance-results.json"
    md_path = root / "results" / "conformance-summary.md"

    missing = [p.name for p in (json_path, md_path) if not p.is_file()]
    if missing:
        print(f"Published results missing: {', '.join(missing)}")
        print("Run: python scripts/run_conformance.py")
        return 1

    fresh = run_suite(load_manifest(default_fixtures_dir()))
    stale: list[str] = []

    committed_json = json.loads(json_path.read_text(encoding="utf-8"))
    if _normalize_report(committed_json) != _normalize_report(fresh):
        stale.append("results/conformance-results.json")

    if _normalize_summary(md_path.read_text(encoding="utf-8")) != _normalize_summary(
        build_summary_md(fresh)
    ):
        stale.append("results/conformance-summary.md")

    if stale:
        print("Published conformance results are STALE:")
        for name in stale:
            print(f"  - {name}")
        print()
        print("They no longer describe the current code and fixtures.")
        print("Regenerate and commit: python scripts/run_conformance.py")
        return 1

    print(
        "Published conformance results are current "
        f"({fresh['passed']}/{fresh['total']} passed; "
        "execution time and durations excluded from the comparison)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
