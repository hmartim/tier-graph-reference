"""Execute the conformance suite and write deterministic reports."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import __version__
from ..grounding.fixture import FixtureGroundingProvider
from ..services import ServiceContext
from ..store.memory import MemoryTierStore
from .compare import diff
from .loader import ConformanceCase, FixtureManifest, default_fixtures_dir, load_manifest
from .operations import execute
from .report import build_report, build_summary_md


def run_case(case: ConformanceCase) -> dict[str, Any]:
    """Execute one case and return its structured result."""
    store = MemoryTierStore.from_input(case.input)
    grounding = FixtureGroundingProvider.from_dict(case.profile)
    ctx = ServiceContext.build(store, grounding)

    started = time.perf_counter()
    error: str | None = None
    actual: dict[str, Any] = {}
    try:
        actual = execute(case.operation, case.request.get("arguments", {}), ctx)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    duration_ms = round((time.perf_counter() - started) * 1000, 3)

    explanation = [error] if error else diff(case.expected, actual)
    return {
        "caseId": case.case_id,
        "title": case.title,
        "operation": case.operation,
        "conformanceClass": case.conformance_class,
        "implementationVersion": __version__,
        "groundingProfileId": case.grounding_profile_id,
        "groundingProfileVersion": case.grounding_profile_version,
        "caseDefinitionReference": case.case_definition_reference,
        "normativeAlignment": case.normative_alignment,
        "passed": not explanation,
        "durationMs": duration_ms,
        "expected": case.expected,
        "actual": actual,
        "explanation": explanation,
    }


def run_suite(manifest: FixtureManifest) -> dict[str, Any]:
    executed_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    case_results = [run_case(case) for case in manifest.cases]
    return build_report(
        implements=manifest.implements,
        fixture_set_version=manifest.fixture_set_version,
        executed_at=executed_at,
        case_results=case_results,
    )


def write_reports(report: dict[str, Any], results_dir: str | Path) -> tuple[Path, Path]:
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "conformance-results.json"
    md_path = out / "conformance-summary.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(build_summary_md(report) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the TIER-Graph conformance suite.")
    parser.add_argument(
        "--fixtures", default=str(default_fixtures_dir()), help="Path to the fixtures/ directory."
    )
    parser.add_argument(
        "--results",
        default=str(default_fixtures_dir().parent / "results"),
        help="Directory for report output.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Only print the final pass/fail line."
    )
    args = parser.parse_args(argv)

    manifest = load_manifest(args.fixtures)
    report = run_suite(manifest)
    json_path, md_path = write_reports(report, args.results)

    if not args.quiet:
        for case in report["cases"]:
            status = "PASS" if case["passed"] else "FAIL"
            print(f"  [{status}] {case['caseId']} {case['operation']}")
            if not case["passed"]:
                for line in case["explanation"]:
                    print(f"         - {line}")
        print()
        print(f"Report:  {json_path}")
        print(f"Summary: {md_path}")

    print(
        f"{report['implements']}: {report['passed']}/{report['total']} passed, "
        f"{report['failed']} failed."
    )
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
