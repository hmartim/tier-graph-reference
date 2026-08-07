"""Entity routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ..dependencies import Context

router = APIRouter(tags=["entities"])


@router.get("/entities", operation_id="listEntities")
def list_entities(ctx: Context) -> list[dict[str, Any]]:
    return [entity.model_dump(mode="json") for entity in ctx.store.list_entities()]


@router.get("/entities/{entity_id}", operation_id="getEntityById")
def get_entity(entity_id: str, ctx: Context) -> dict[str, Any]:
    entity = ctx.store.get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"unknown entity: {entity_id}")
    return entity.model_dump(mode="json")
