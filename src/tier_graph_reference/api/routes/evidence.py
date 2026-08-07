"""Evidence routes: fetch, admissibility, audit, reverse lookup."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from ...models import parse_instant
from ..dependencies import Context

router = APIRouter(tags=["evidence"])


@router.get("/evidence/{evidence_id}", operation_id="getEvidenceById")
def get_evidence(evidence_id: str, ctx: Context) -> dict[str, Any]:
    evidence = ctx.store.get_evidence(evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"unknown evidence: {evidence_id}")
    return evidence.model_dump(mode="json", exclude_none=True)


@router.get("/evidence/{evidence_id}/admissibility", operation_id="evaluateEvidenceAdmissibility")
def evidence_admissibility(
    evidence_id: str,
    ctx: Context,
    at: str = Query(...),
) -> dict[str, Any]:
    try:
        result = ctx.admissibility.evaluate(evidence_id, parse_instant(at))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = result.model_dump(mode="json")
    payload["at"] = at
    return payload


@router.get("/evidence/{evidence_id}/audit", operation_id="getEvidenceAuditTrail")
def evidence_audit(evidence_id: str, ctx: Context) -> dict[str, Any]:
    try:
        return ctx.audit.evidence_audit_trail(evidence_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/evidence-units/{evidence_unit_id}/relations",
    operation_id="getRelationsByEvidenceUnit",
)
def relations_by_evidence_unit(
    evidence_unit_id: str,
    ctx: Context,
    profileId: str = Query(...),
) -> dict[str, Any]:
    relations = ctx.store.get_relations_by_evidence_unit(profileId, evidence_unit_id)
    families: list[str] = []
    for relation in relations:
        if relation.predicateFamily not in families:
            families.append(relation.predicateFamily)
    return {
        "relationIds": [relation.id for relation in relations],
        "predicateFamilies": families,
        "count": len(relations),
    }
