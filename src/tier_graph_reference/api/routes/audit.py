"""Audit routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models import parse_instant
from ..dependencies import Context

router = APIRouter(tags=["audit"])


@router.get("/audit/relations/{relation_id}", operation_id="getRelationAuditTrail")
def relation_audit(
    relation_id: str,
    ctx: Context,
    at: str | None = Query(None),
) -> dict[str, Any]:
    try:
        return ctx.audit.relation_audit_trail(
            relation_id, parse_instant(at) if at else None
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit/relations/{relation_id}/explain-state", operation_id="explainRelationState")
def explain_state(
    relation_id: str,
    ctx: Context,
    at: str = Query(...),
) -> dict[str, Any]:
    try:
        return ctx.audit.explain_relation_state(relation_id, parse_instant(at))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit/evidence/{evidence_id}", operation_id="getEvidenceAuditTrailDetailed")
def evidence_audit(
    evidence_id: str,
    ctx: Context,
    at: str | None = Query(None),
) -> dict[str, Any]:
    try:
        return ctx.audit.evidence_audit_trail(
            evidence_id, parse_instant(at) if at else None
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
