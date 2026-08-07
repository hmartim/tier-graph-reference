"""FastAPI dependencies: expose the shared ``ServiceContext`` to route handlers.

The facade is a thin layer: handlers resolve the same :class:`ServiceContext`
used by the offline conformance runner and call the same services. They never
re-implement semantics.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Request

from ..grounding.fixture import FixtureGroundingProvider
from ..services import ServiceContext
from ..store.memory import MemoryTierStore

_EMPTY_PROFILE = {"profile": {"id": "empty", "version": "0", "intervalConvention": "[from,to)"}}


def build_default_context() -> ServiceContext:
    """Seed a demo context from a fixture case (env ``TIER_DEMO_FIXTURE``), else empty.

    This makes ``uvicorn tier_graph_reference.api.app:app`` start with data so
    ``/docs`` is immediately explorable. It is a convenience for the demo facade,
    not part of any normative behavior.
    """
    try:
        from ..conformance.loader import default_fixtures_dir, load_manifest

        manifest = load_manifest(default_fixtures_dir())
        wanted = os.environ.get("TIER_DEMO_FIXTURE", "T01")
        case = next((c for c in manifest.cases if c.case_id == wanted), manifest.cases[0])
        store = MemoryTierStore.from_input(case.input)
        grounding = FixtureGroundingProvider.from_dict(case.profile)
        return ServiceContext.build(store, grounding)
    except Exception:
        store = MemoryTierStore()
        grounding = FixtureGroundingProvider.from_dict(_EMPTY_PROFILE)
        return ServiceContext.build(store, grounding)


def get_context(request: Request) -> ServiceContext:
    return request.app.state.context  # type: ignore[no-any-return]


Context = Annotated[ServiceContext, Depends(get_context)]
