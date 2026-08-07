"""Relation routes: fetch, evidential state, history, identity comparison."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models import parse_instant
from ..dependencies import Context

router = APIRouter(tags=["relations"])


@router.get("/relations", operation_id="listRelations")
def list_relations(ctx: Context) -> list[dict[str, Any]]:
    return [relation.model_dump(mode="json") for relation in ctx.store.list_relations()]


@router.get("/relations/compare", operation_id="compareRelationIdentity")
def compare_relations(
    ctx: Context,
    relationIdA: str = Query(...),
    relationIdB: str = Query(...),
) -> dict[str, Any]:
    """Compare two relation candidates for identity (see T06)."""
    try:
        a = ctx.store.require_relation(relationIdA)
        b = ctx.store.require_relation(relationIdB)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ctx.identity.compare(a, b).model_dump(mode="json")


@router.get("/relations/{relation_id}", operation_id="getRelationById")
def get_relation(relation_id: str, ctx: Context) -> dict[str, Any]:
    relation = ctx.store.get_relation(relation_id)
    if relation is None:
        raise HTTPException(status_code=404, detail=f"unknown relation: {relation_id}")
    return relation.model_dump(mode="json")


@router.get("/relations/{relation_id}/state", operation_id="getRelationStateAtTime")
def relation_state(
    relation_id: str,
    ctx: Context,
    at: str = Query(..., description="RFC3339 instant"),
) -> dict[str, Any]:
    try:
        snapshot = ctx.relation_state.state_at(relation_id, parse_instant(at), at_label=at)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return snapshot.model_dump(mode="json")


@router.get("/relations/{relation_id}/history", operation_id="getRelationHistory")
def relation_history(
    relation_id: str,
    ctx: Context,
    startAt: str = Query(...),
    endAt: str = Query(...),
) -> dict[str, Any]:
    try:
        entries = ctx.relation_state.history(
            relation_id, start=parse_instant(startAt), end=parse_instant(endAt)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "relationId": relation_id,
        "statePeriods": [entry.model_dump(mode="json", by_alias=True) for entry in entries],
    }
