"""Projection routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models import parse_instant
from ..dependencies import Context

router = APIRouter(tags=["projections"])


@router.get("/projections", operation_id="getProjection")
def project(
    ctx: Context,
    at: str = Query(...),
    policyId: str = Query(...),
) -> dict[str, Any]:
    """Return the relations admitted at ``at`` under ``policyId``."""
    try:
        projected = ctx.projection.project(parse_instant(at), policyId)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "at": at,
        "policyId": policyId,
        "relations": [relation.model_dump(mode="json") for relation in projected],
    }
