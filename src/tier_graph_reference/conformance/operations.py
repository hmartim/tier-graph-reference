"""Operation dispatch: turn a fixture ``request.json`` into a normalized result.

Each handler calls the same services used by the FastAPI facade and returns a
JSON-native dict. Handlers may include a superset of fields; the partial-match
comparator asserts only what a given case's ``expected.json`` declares. This lets
one handler (e.g. ``getRelationStateAtTime``) serve several cases that assert
different invariants.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Any

from ..models import (
    EXCLUDED_REVIEW_STATUSES,
    INTERVAL_KEYS,
    ProvenanceActivity,
    RelationEvidence,
    iso_z,
    parse_instant,
)
from ..services import ServiceContext
from ..store.base import TierStore


class UnknownOperationError(ValueError):
    """Raised when a fixture requests an operation with no registered handler."""


def execute(operation: str, args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    handler = _HANDLERS.get(operation)
    if handler is None:
        raise UnknownOperationError(operation)
    return handler(args, ctx)


# --------------------------------------------------------------------------
# Invariant helpers
# --------------------------------------------------------------------------
def _r3_relation_interval_keys(store: TierStore) -> dict[str, Any]:
    """Report on R3: no authoritative interval is copied onto a DerivedRelation.

    The count is always 0 and *cannot* be otherwise: ``TierModel`` sets
    ``extra="forbid"``, so a relation carrying an interval key cannot be
    constructed. That is a stronger guarantee than a runtime check, but it is a
    structural one -- so the report names what enforces it rather than implying
    an executed test. Fixture-level enforcement lives in the loader, which scans
    the raw JSON before validation.
    """
    found = sum(
        1
        for relation in store.list_relations()
        if any(key in relation.model_dump() for key in INTERVAL_KEYS)
    )
    return {"found": found, "enforcedBy": "model-schema (extra=forbid)"}


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------
def _get_relation_history(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    relation_id = args["relationId"]
    entries = ctx.relation_state.history(
        relation_id,
        start=parse_instant(args["startAt"]),
        end=parse_instant(args["endAt"]),
    )
    return {
        "relationId": relation_id,
        "statePeriods": [entry.model_dump(mode="json", by_alias=True) for entry in entries],
        "invariants": {
            "relationCount": len(ctx.store.list_relations()),
            "evidenceRecordCount": len(ctx.store.list_evidence()),
            "r3RelationIntervalKeys": _r3_relation_interval_keys(ctx.store),
        },
    }


def _get_relation_state_at_time(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    if "times" in args:
        return _relation_state_over_times(args, ctx)
    return _relation_state_over_relations(args, ctx)


def _relation_state_over_times(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    relation_id = args["relationId"]
    times = args["times"]
    instants = [parse_instant(t) for t in times]
    states = [
        ctx.relation_state.state_at(
            relation_id, instant, at_label=label
        ).model_dump(mode="json", exclude_none=True)
        for label, instant in zip(times, instants, strict=True)
    ]
    result: dict[str, Any] = {
        "states": states,
        "invariants": {
            "relationCount": len(ctx.store.list_relations()),
            "distinctRelationCount": _distinct_relation_count(ctx, [relation_id]),
            "r3RelationIntervalKeys": _r3_relation_interval_keys(ctx.store),
        },
        "boundaryCauseRefs": ctx.relation_state.boundary_causes(relation_id, instants),
    }
    result.update(_historical_retention(relation_id, instants, ctx))
    result.update(_vacatio_checks(relation_id, ctx))
    return result


def _relation_state_over_relations(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    relation_ids = args["relationIds"]
    at = args["at"]
    states = [
        ctx.relation_state.state_at(rid, parse_instant(at), at_label=at).model_dump(
            mode="json", exclude_none=True
        )
        for rid in relation_ids
    ]
    return {
        "states": states,
        "invariants": {
            "relationCount": len(ctx.store.list_relations()),
            "distinctRelationCount": _distinct_relation_count(ctx, relation_ids),
            "pairwiseIdentity": _pairwise_identity(ctx, relation_ids),
            "r3RelationIntervalKeys": _r3_relation_interval_keys(ctx.store),
        },
    }


def _distinct_relation_count(ctx: ServiceContext, relation_ids: list[str]) -> int:
    """Count relations that actually resolve in the store.

    Deliberately not ``len(relation_ids)``: echoing the request back proves
    nothing about what the store holds.
    """
    return len({rid for rid in relation_ids if ctx.store.get_relation(rid) is not None})


def _pairwise_identity(ctx: ServiceContext, relation_ids: list[str]) -> list[dict[str, Any]]:
    """Compare every pair of candidates through the identity service.

    This is the assertion T07 needs: that the candidates are *non-mergeable*,
    not merely that the request named several identifiers.
    """
    resolved = sorted({rid for rid in relation_ids if ctx.store.get_relation(rid) is not None})
    comparisons: list[dict[str, Any]] = []
    for id_a, id_b in itertools.combinations(resolved, 2):
        comparison = ctx.identity.compare(
            ctx.store.require_relation(id_a), ctx.store.require_relation(id_b)
        )
        comparisons.append(
            {
                "relationIdA": id_a,
                "relationIdB": id_b,
                "decision": comparison.decision.value,
                "mergeAllowed": comparison.mergeAllowed,
                "differingDimensions": sorted(comparison.differingDimensions),
            }
        )
    return comparisons


def _historical_retention(
    relation_id: str, instants: list[Any], ctx: ServiceContext
) -> dict[str, Any]:
    """Observe that evidence admissible early is *retained* but inadmissible late.

    Retention and review eligibility are reported separately on purpose. Marking
    withdrawn evidence ``superseded`` is a legitimate curatorial act; the claim
    under test is that the record is not *deleted*, and that its withdrawal
    follows from source-state temporality rather than from erasure or curation.
    ``evaluate_evidence`` consults only the anchors' source states, so it is
    already review-blind.
    """
    if len(instants) < 2:
        return {}
    early, late = min(instants), max(instants)
    ids: list[str] = []
    retained: list[bool] = []
    inadmissible_late: list[bool] = []
    review_statuses: list[str] = []
    for evidence in ctx.store.get_relation_evidence(relation_id):
        if not ctx.grounding.evaluate_evidence(evidence, early).admissible:
            continue
        ids.append(evidence.id)
        still = ctx.store.get_evidence(evidence.id)  # re-read; do not reuse the loop object
        retained.append(still is not None)
        inadmissible_late.append(
            still is not None
            and not ctx.grounding.evaluate_evidence(still, late).admissible
        )
        review_statuses.append(still.reviewStatus.value if still is not None else "missing")
    if not ids:  # non-vacuity guard: all([]) is True
        return {}
    order = sorted(range(len(ids)), key=lambda i: ids[i])
    return {
        "historicalEvidenceIds": [ids[i] for i in order],
        "historicalEvidenceRetained": all(retained),
        "historicalEvidenceTemporallyInadmissibleAtLateTime": all(inadmissible_late),
        "reviewStatusAtLateTime": [review_statuses[i] for i in order],
    }


def _vacatio_checks(relation_id: str, ctx: ServiceContext) -> dict[str, Any]:
    """Interrogate the provider at the publication instant itself.

    Publication establishes existence; it must not admit a provision before its
    applicability begins. Evaluated directly against the grounding provider, so
    the queried times need not include the publication date.
    """
    checks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for evidence in ctx.store.get_relation_evidence(relation_id):
        if evidence.reviewStatus in EXCLUDED_REVIEW_STATUSES:
            continue
        for unit_id in evidence.evidence_unit_ids:
            state = ctx.grounding.resolve_source_state(unit_id)
            if state is None or state.publishedAt is None or state.id in seen:
                continue
            if state.publishedAt >= state.admissibleFrom:
                continue  # no vacatio window to exercise
            seen.add(state.id)
            checks.append(
                {
                    "sourceStateId": state.id,
                    "publishedAt": iso_z(state.publishedAt),
                    "admissibleFrom": iso_z(state.admissibleFrom),
                    "admissibleAtPublication": ctx.grounding.evaluate_source_state(
                        state.id, state.publishedAt
                    ),
                    "admissibleAtApplicability": ctx.grounding.evaluate_source_state(
                        state.id, state.admissibleFrom
                    ),
                }
            )
    if not checks:  # non-vacuity guard
        return {}
    checks.sort(key=lambda c: str(c["sourceStateId"]))
    return {
        "vacatioChecks": checks,
        "publicationDateDoesNotControlAdmission": all(
            check["admissibleAtPublication"] is False
            and check["admissibleAtApplicability"] is True
            for check in checks
        ),
    }


def _get_relations_by_evidence_unit(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    relations = ctx.store.get_relations_by_evidence_unit(
        args["profileId"], args["evidenceUnitId"]
    )
    families: list[str] = []
    for relation in relations:
        if relation.predicateFamily not in families:
            families.append(relation.predicateFamily)
    return {
        "relationIds": [relation.id for relation in relations],
        "predicateFamilies": families,
        "count": len(relations),
    }


def _evaluate_evidence_admissibility(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    evidence_id = args["evidenceId"]
    results = []
    for t in args["times"]:
        outcome = ctx.admissibility.evaluate(evidence_id, parse_instant(t))
        payload = outcome.model_dump(mode="json")
        payload["at"] = t  # echo the exact requested instant
        results.append(payload)
    semantics, witnesses = _multi_anchor_semantics(results)
    return {
        "results": results,
        "semantics": semantics,
        # The count is published for audit; the boolean is what fixtures assert,
        # because the comparator supports equality only and the requirement is
        # "at least one", not "exactly one".
        "partialWitnessCount": witnesses,
        "hasPartialWitness": witnesses > 0,
    }


def _multi_anchor_semantics(results: list[dict[str, Any]]) -> tuple[str, int]:
    """Infer the multi-anchor combination rule from the observed outcomes.

    A record is conjunctive if, at a time where only *some* anchors resolve to
    admissible source states, the record is inadmissible. Times where all or no
    anchors are admissible cannot distinguish conjunction from disjunction, so
    the witness count is reported: with no partial time the fixture proves
    nothing and the result is ``undetermined``.
    """
    partials = [
        r
        for r in results
        if 0 < sum(1 for ok in r["anchorResults"].values() if ok) < len(r["anchorResults"])
    ]
    if not partials:
        return "undetermined", 0
    if any(r["admissible"] for r in partials):
        return "disjunctive", len(partials)
    return "conjunctive", len(partials)


def _compare_relation_identity(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    relation_a = ctx.store.require_relation(args["relationIdA"])
    relation_b = ctx.store.require_relation(args["relationIdB"])
    comparison = ctx.identity.compare(relation_a, relation_b)
    return comparison.model_dump(mode="json")


def _get_evidence_audit_trail(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    return ctx.audit.evidence_audit_trail(args["evidenceId"])


def _create_evidence(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    """Execute a sequence of createEvidence submissions (T08).

    The submissions are *replayed for real* against the store: nothing here reads
    back a pre-arranged outcome. Whether re-extraction duplicates a basis is
    decided by the service, not by the fixture.
    """
    authoring = ctx.require_authoring()
    outcomes = []
    submitted_keys = set()
    relation_ids = []
    for submission in args["submissions"]:
        candidate = RelationEvidence.model_validate(submission["evidence"])
        activity_raw = submission.get("provenanceActivity")
        activity = (
            ProvenanceActivity.model_validate(activity_raw) if activity_raw is not None else None
        )
        submitted_keys.add(candidate.identity_key)
        relation_ids.append(candidate.relationId)
        outcomes.append(authoring.create_evidence(candidate, activity).model_dump(mode="json"))

    relation_id = relation_ids[0]
    stored = ctx.store.get_relation_evidence(relation_id)
    evidence_ids = {outcome["evidenceId"] for outcome in outcomes}
    return {
        "outcomes": outcomes,
        "evidenceRecordCount": len(stored),
        "independentEvidenceCount": authoring.independent_evidence_count(relation_id),
        # Non-vacuity witness: proves the submissions really did share one key.
        # Without it the case could "pass" on submissions that merely happened to
        # differ, which would demonstrate nothing about deduplication.
        "distinctSubmittedKeyCount": len(submitted_keys),
        "stableEvidenceId": len(evidence_ids) == 1,
        "activityIds": sorted({a for e in stored for a in e.provenanceActivityIds}),
    }


def _find_admissible_paths(args: dict[str, Any], ctx: ServiceContext) -> dict[str, Any]:
    results = []
    for t in args["times"]:
        paths, excluded, trace = ctx.paths.find_paths_traced(
            args["sourceEntityId"],
            args["targetEntityId"],
            parse_instant(t),
            args["policyId"],
            int(args["maxDepth"]),
        )
        entry: dict[str, Any] = {
            "at": t,
            "paths": [path.model_dump(mode="json", exclude_none=True) for path in paths],
            # Per query time, not aggregated: the projection saturates at later
            # times, where a leaking and a conforming traversal are identical.
            # The discriminating power lives in the entries where
            # projectionIsNonTrivial is true.
            "trace": {
                # Lists and counts are published for audit. The *normative*
                # properties are the computed booleans: fixtures assert those,
                # so a conforming implementation that narrows the candidate set
                # further (reachability, predicate family, direction) is not
                # rejected for offering a strict subset of the projection.
                "offeredRelationIds": sorted(trace.offeredRelationIds),
                "visitedRelationIds": sorted(trace.visitedRelationIds),
                "returnedRelationIds": sorted(trace.returnedRelationIds),
                "projectedRelationIds": sorted(trace.projectedRelationIds),
                "allTimeRelationCount": trace.allTimeRelationCount,
                "projectedRelationCount": len(trace.projectedRelationIds),
                "projectionIsNonTrivial": trace.projection_is_non_trivial,
                "leakageWitnessRelationIds": trace.leakage_witness_relation_ids,
                "candidateGenerationUsesProjectedGraph": trace.uses_projected_graph,
            },
        }
        if excluded:
            entry["excluded"] = [
                explanation.model_dump(mode="json", exclude_none=True)
                for explanation in excluded
            ]
        results.append(entry)
    policy = ctx.store.require_policy(args["policyId"])
    return {
        "results": results,
        # The resolved policy, not just its id. Two runs sharing a policyId but
        # differing in Pi_review would otherwise look identical while admitting
        # different evidence -- reproducible in appearance only.
        "policy": {
            "id": policy.id,
            "admittedStates": [state.value for state in policy.admittedStates],
            "groundingReviewStatuses": sorted(
                status.value for status in policy.grounding_review_statuses()
            ),
        },
    }


_HANDLERS: dict[str, Callable[[dict[str, Any], ServiceContext], dict[str, Any]]] = {
    "getRelationHistory": _get_relation_history,
    "getRelationStateAtTime": _get_relation_state_at_time,
    "getRelationsByEvidenceUnit": _get_relations_by_evidence_unit,
    "evaluateEvidenceAdmissibility": _evaluate_evidence_admissibility,
    "compareRelationIdentity": _compare_relation_identity,
    "getEvidenceAuditTrail": _get_evidence_audit_trail,
    "createEvidence": _create_evidence,
    "findAdmissiblePaths": _find_admissible_paths,
}


def supported_operations() -> list[str]:
    return sorted(_HANDLERS)
