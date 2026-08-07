"""The conformance report carries the version pin and per-class rollup."""

from __future__ import annotations

from tier_graph_reference.conformance.loader import default_fixtures_dir, load_manifest
from tier_graph_reference.conformance.runner import run_suite


def test_report_shape_and_pin() -> None:
    report = run_suite(load_manifest(default_fixtures_dir()))
    assert report["specificationVersion"] == "0.1.0-draft"
    assert report["implements"] == "tier-graph-api v0.1.0-draft"
    assert report["total"] == 10
    assert report["passed"] == 10
    assert report["failed"] == 0


def test_report_has_class_rollup_including_static_classes() -> None:
    report = run_suite(load_manifest(default_fixtures_dir()))
    names = {cls["name"] for cls in report["conformanceClasses"]}
    assert {"Core Model Conformance", "Query API Conformance", "Path Conformance"} <= names
    assert "SAT-Graph Adapter Integration" in names
    assert "Authoring Conformance" in names

    # Authoring is exercised only in part: createEvidence runs (T08), the rest of
    # the class does not. "passed 1/1" must not read as full class coverage.
    authoring = next(
        cls for cls in report["conformanceClasses"] if cls["name"] == "Authoring Conformance"
    )
    assert authoring["status"] == "partial"
    assert authoring["passed"] == 1
    assert "createEvidence" in authoring["note"]
    assert "out of scope" in authoring["note"]


def test_no_conformance_class_is_listed_twice() -> None:
    """A class must not appear both as a real rollup and as a static placeholder."""
    report = run_suite(load_manifest(default_fixtures_dir()))
    names = [cls["name"] for cls in report["conformanceClasses"]]
    assert len(names) == len(set(names)), f"duplicated class rows: {names}"


def test_published_results_are_not_stale() -> None:
    """The committed outputs must describe the current code.

    The release cites `results/` as the executed evidence, so those files are
    tracked. Tracking generated output is only safe if drift is detectable:
    this makes staleness a test failure rather than a matter of discipline.
    """
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_results_current.py")],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_each_case_carries_grounding_profile_version() -> None:
    report = run_suite(load_manifest(default_fixtures_dir()))
    for case in report["cases"]:
        assert case["groundingProfileId"] == "public-legal-fixture"
        assert case["groundingProfileVersion"] == "0.1.0"
        assert case["implementationVersion"]
