"""Conformance loader, operation dispatch, comparison, runner, and report."""

from __future__ import annotations

from .compare import diff, matches
from .loader import ConformanceCase, FixtureManifest, default_fixtures_dir, load_manifest
from .operations import UnknownOperationError, execute, supported_operations
from .report import build_report, build_summary_md
from .runner import run_case, run_suite, write_reports

__all__ = [
    "ConformanceCase",
    "FixtureManifest",
    "UnknownOperationError",
    "build_report",
    "build_summary_md",
    "default_fixtures_dir",
    "diff",
    "execute",
    "load_manifest",
    "matches",
    "run_case",
    "run_suite",
    "supported_operations",
    "write_reports",
]
