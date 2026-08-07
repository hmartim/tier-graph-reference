"""Build the machine-readable and human-readable conformance reports."""

from __future__ import annotations

from typing import Any

from .. import SPECIFICATION_VERSION, __version__

#: Classes that the fixture suite exercises only in part. The rollup counts the
#: cases that ran; the note says what the class still covers that they do not, so
#: "passed 1/1" is never read as full coverage of the class.
_PARTIAL_CLASS_NOTES: dict[str, str] = {
    "Authoring Conformance": (
        "Partially covered: createEvidence (evidence identity and de-duplication) is "
        "implemented and exercised by T08. The remaining authoring operations "
        "(appendProvenanceActivity, recordReviewEvent) are out of scope for v0.1.0."
    ),
}

#: Conformance classes that are not exercised by the offline fixture runner.
#: They are reported for transparency (see docs/conformance.md).
_STATIC_CLASSES: list[dict[str, str]] = [
    {
        "name": "Analytical Extension Conformance",
        "status": "experimental",
        "note": "Communities and causal gates are intentionally kept outside the core.",
    },
    {
        "name": "SAT-Graph Adapter Integration",
        "status": "mocked",
        "note": "Validated separately with mocked HTTP responses in tests/adapters/sat_graph.",
    },
]


def build_report(
    *,
    implements: str,
    fixture_set_version: str,
    executed_at: str,
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    total = len(case_results)
    passed = sum(1 for c in case_results if c["passed"])
    failed = total - passed

    return {
        "implements": implements or f"tier-graph-api v{SPECIFICATION_VERSION}",
        "specificationVersion": SPECIFICATION_VERSION,
        "referenceImplementationVersion": __version__,
        "fixtureSetVersion": fixture_set_version,
        "executedAt": executed_at,
        "total": total,
        "passed": passed,
        "failed": failed,
        "conformanceClasses": _class_rollup(case_results),
        "cases": case_results,
    }


def _class_rollup(case_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = {}
    for case in case_results:
        cls = case["conformanceClass"]
        bucket = grouped.setdefault(cls, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if case["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1

    rollup: list[dict[str, Any]] = []
    for name in sorted(grouped):
        counts = grouped[name]
        entry: dict[str, Any] = {
            "name": name,
            "status": "passed" if counts["failed"] == 0 else "failed",
            **counts,
        }
        note = _PARTIAL_CLASS_NOTES.get(name)
        if note is not None:
            entry["status"] = "partial" if counts["failed"] == 0 else "failed"
            entry["note"] = note
        rollup.append(entry)
    rollup.extend(_STATIC_CLASSES)
    return rollup


def _alignment_section(cases: list[dict[str, Any]]) -> list[str]:
    """Surface declared divergences from the normative catalogue.

    A `gap` means the normative behaviour is *not executed*. Reporting it beside
    the PASS column is the point: a case can pass its fixture while leaving the
    normative operation unexercised, and a reader must be able to see that
    without opening the manifest.
    """
    diverging = [c for c in cases if c.get("normativeAlignment")]
    gaps = [c for c in diverging if c["normativeAlignment"]["status"] == "gap"]

    lines = ["## Normative alignment (†)", ""]
    lines.append(f"- **Normative case-operation gaps: {len(gaps)}**")
    lines.append(
        f"- Cases diverging from the catalogue's operation: {len(diverging)} of {len(cases)}"
    )
    lines.append("")
    if not diverging:
        lines.append(
            "Every case executes the operation the normative catalogue specifies."
        )
        lines.append("")
        return lines

    lines.append(
        "These cases run a different operation than the normative catalogue in "
        "`tier-graph-api` specifies. Every divergence is declared; see "
        "`fixtures/manifest.yaml`."
    )
    lines.append("")
    lines.append("| Case | Normative operation | Executed operation | Status |")
    lines.append("|---|---|---|---|")
    for case in diverging:
        alignment = case["normativeAlignment"]
        lines.append(
            f"| {case['caseId']} | `{alignment['operation']}` | "
            f"`{case['operation']}` | {alignment['status']} |"
        )
    lines.append("")

    gaps = [c for c in diverging if c["normativeAlignment"]["status"] == "gap"]
    if gaps:
        ids = ", ".join(c["caseId"] for c in gaps)
        lines.append(
            f"> **Gap:** {ids} — the normative operation is **not executed** by this "
            f"implementation. The case passes its fixture, but does not demonstrate the "
            f"normative behaviour. See the rationale in `fixtures/manifest.yaml`."
        )
        lines.append("")
    return lines


def build_summary_md(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# TIER-Graph conformance summary")
    lines.append("")
    lines.append(f"- **Implements:** {report['implements']}")
    lines.append(f"- **Specification version:** {report['specificationVersion']}")
    lines.append(
        f"- **Reference implementation:** v{report['referenceImplementationVersion']}"
    )
    lines.append(f"- **Fixture set:** v{report['fixtureSetVersion']}")
    lines.append(f"- **Executed at:** {report['executedAt']}")
    lines.append(
        f"- **Result:** {report['passed']}/{report['total']} passed "
        f"({report['failed']} failed)"
    )
    lines.append("")

    lines.append("## Conformance classes")
    lines.append("")
    lines.append(
        "> Two different measures, easily confused. **Case-operation gaps** counts "
        "conformance *cases* whose normative operation is not executed (see *Normative "
        "alignment* below). **Class coverage** is whether every operation belonging to a "
        "class is implemented. Zero gaps does not imply full class coverage."
    )
    lines.append("")
    lines.append("| Class | Status | Passed | Total |")
    lines.append("|---|---|---|---|")
    for cls in report["conformanceClasses"]:
        passed = cls.get("passed", "-")
        total = cls.get("total", "-")
        lines.append(f"| {cls['name']} | {cls['status']} | {passed} | {total} |")
    lines.append("")
    for cls in report["conformanceClasses"]:
        if cls.get("note") and cls.get("total") is not None:
            # A class counted as passing but only partly covered must say so here:
            # "1/1" beside "partial" is otherwise easy to read as full coverage.
            lines.append(f"- **{cls['name']}** — {cls['note']}")
    if any(c.get("note") and c.get("total") is not None for c in report["conformanceClasses"]):
        lines.append("")

    lines.append("## Cases")
    lines.append("")
    lines.append("| Case | Operation | Class | Result | Duration (ms) |")
    lines.append("|---|---|---|---|---|")
    for case in report["cases"]:
        result = "PASS" if case["passed"] else "FAIL"
        marker = " †" if case.get("normativeAlignment") else ""
        lines.append(
            f"| {case['caseId']}{marker} — {case['title']} | `{case['operation']}` | "
            f"{case['conformanceClass']} | {result} | {case['durationMs']} |"
        )
    lines.append("")

    lines.extend(_alignment_section(report["cases"]))

    failures = [c for c in report["cases"] if not c["passed"]]
    if failures:
        lines.append("## Failures")
        lines.append("")
        for case in failures:
            lines.append(f"### {case['caseId']}")
            lines.append("")
            for line in case["explanation"]:
                lines.append(f"- {line}")
            lines.append("")

    return "\n".join(lines)
