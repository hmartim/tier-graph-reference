"""Grounding profile routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..dependencies import Context

router = APIRouter(tags=["profiles"])


@router.get("/profile", operation_id="getGroundingProfile")
def get_profile(ctx: Context) -> dict[str, Any]:
    """Return the active temporal grounding profile metadata."""
    return ctx.grounding.profile().model_dump(mode="json")
