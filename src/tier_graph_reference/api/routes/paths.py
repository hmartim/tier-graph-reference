"""Path routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models import parse_instant
from ..dependencies import Context

router = APIRouter(tags=["paths"])


@router.get("/paths", operation_id="findAdmissiblePaths")
def find_paths(
    ctx: Context,
    sourceEntityId: str = Query(...),
    targetEntityId: str = Query(...),
    at: str = Query(...),
    policyId: str = Query(...),
    maxDepth: int = Query(4, ge=1),
) -> dict[str, Any]:
    """Find admissible paths over the time-indexed projection at ``at``."""
    try:
        paths, excluded = ctx.paths.find_paths(
            sourceEntityId, targetEntityId, parse_instant(at), policyId, maxDepth
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result: dict[str, Any] = {
        "at": at,
        "paths": [path.model_dump(mode="json") for path in paths],
        "candidateGenerationUsesProjectedGraph": True,
    }
    if excluded:
        result["excluded"] = [e.model_dump(mode="json", exclude_none=True) for e in excluded]
    return result
