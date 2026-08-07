"""Shared helpers for the runnable examples."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tier_graph_reference.conformance.loader import (  # noqa: E402
    ConformanceCase,
    default_fixtures_dir,
    load_manifest,
)
from tier_graph_reference.grounding.fixture import FixtureGroundingProvider  # noqa: E402
from tier_graph_reference.services import ServiceContext  # noqa: E402
from tier_graph_reference.store.memory import MemoryTierStore  # noqa: E402


def load_case(case_id: str) -> ConformanceCase:
    manifest = load_manifest(default_fixtures_dir())
    for case in manifest.cases:
        if case.case_id == case_id:
            return case
    raise SystemExit(f"unknown case: {case_id}")


def context_for(case: ConformanceCase) -> ServiceContext:
    store = MemoryTierStore.from_input(case.input)
    grounding = FixtureGroundingProvider.from_dict(case.profile)
    return ServiceContext.build(store, grounding)
