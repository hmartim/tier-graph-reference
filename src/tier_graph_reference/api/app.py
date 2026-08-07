"""Optional FastAPI facade over the TIER-Graph reference services.

The facade is an **implementation artifact**, not the normative API source. Its
handlers are thin: they call the same services used by the offline conformance
runner. Non-normative operational endpoints (e.g. ``/healthz``) are marked as
such.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .. import IMPLEMENTS, SPECIFICATION_VERSION, __version__
from .dependencies import build_default_context
from .routes import audit, entities, evidence, paths, profiles, projections, relations


def create_app() -> FastAPI:
    app = FastAPI(
        title="TIER-Graph reference implementation",
        version=__version__,
        description=(
            "Reference facade for the TIER-Graph API. "
            f"Implements {IMPLEMENTS}. "
            "This document is an implementation artifact, not the normative spec."
        ),
    )
    app.state.context = build_default_context()

    for module in (profiles, entities, relations, evidence, projections, paths, audit):
        app.include_router(module.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, Any]:
        return {
            "implements": IMPLEMENTS,
            "specificationVersion": SPECIFICATION_VERSION,
            "referenceImplementationVersion": __version__,
            "docs": "/docs",
        }

    @app.get("/healthz", tags=["operational"], summary="Health check (non-normative)")
    def healthz() -> dict[str, str]:
        # Operational endpoint; not part of the normative API surface.
        return {"status": "ok", "x-tier-reference": "non-normative"}

    return app


app = create_app()
