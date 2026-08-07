"""Admissible-path service.

Path candidates are generated over the **time-indexed projection** at the query
time, never over an all-time graph filtered afterwards (see T10). The all-time
graph is consulted only to *explain* why a route is excluded — a diagnostic, not
candidate generation.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from ..grounding.base import TemporalGroundingProvider
from ..models import (
    EXCLUDED_REVIEW_STATUSES,
    ExclusionExplanation,
    GroundedPath,
    PathStep,
    Stance,
    iso_z,
)
from ..store.base import TierStore
from .projection import ProjectionService
from .relation_state import RelationStateService

REASON_SOURCE_STATE = "EVIDENCE_SOURCE_STATE_NOT_ADMISSIBLE"
REASON_NO_EVIDENCE = "NO_ADMISSIBLE_EVIDENCE"
REASON_POLICY = "STATE_NOT_ADMITTED_BY_POLICY"


class Edge(NamedTuple):
    """One directed relation edge in a traversal graph."""

    from_node: str
    to_node: str
    relation_id: str


@dataclass(frozen=True)
class TraversalTrace:
    """What candidate generation was *handed*, and what it actually visited.

    This exists to make R7 falsifiable. ``offeredRelationIds`` must be read from
    the very collection passed to :func:`_edge_paths` -- never rebuilt from the
    projection -- otherwise the field is true by construction and proves nothing.

    ``visitedRelationIds`` includes relations considered on abandoned branches: a
    leaking implementation reveals itself by *visiting* an inadmissible relation
    even when it never returns one.

    The all-time enumeration in ``_explain_excluded_routes`` is a diagnostic, not
    candidate generation, and never contributes here. Keeping the two apart is
    precisely the distinction R7 draws.
    """

    offeredRelationIds: frozenset[str]
    visitedRelationIds: frozenset[str]
    returnedRelationIds: frozenset[str]
    projectedRelationIds: frozenset[str]
    allTimeRelationCount: int

    @property
    def leakage_witness_relation_ids(self) -> list[str]:
        """Relations offered, visited, or returned that the projection does not admit."""
        return sorted(
            (self.offeredRelationIds - self.projectedRelationIds)
            | (self.visitedRelationIds - self.projectedRelationIds)
            | (self.returnedRelationIds - self.projectedRelationIds)
        )

    @property
    def projection_is_non_trivial(self) -> bool:
        """Whether the projection actually excludes something at this query time.

        When the projection saturates (every relation admitted), a leaking and a
        conforming implementation are indistinguishable, so the trace proves
        nothing. Fixtures must assert this is ``True`` for at least one query
        time, or the case is vacuous.
        """
        return self.allTimeRelationCount > len(self.projectedRelationIds)

    @property
    def uses_projected_graph(self) -> bool:
        """Whether candidate generation stayed inside the temporal projection.

        Containment, not equality. R7 requires that candidate generation be
        *constrained by* the projection -- not that it be offered all of it. A
        conforming implementation may narrow further before traversing (by
        reachability, ``predicateFamilies``, or ``direction``) and still offer a
        strict subset. Requiring equality would reject it. Equality happens to
        hold in this reference implementation; it is not an R7 requirement.
        """
        return (
            self.offeredRelationIds <= self.projectedRelationIds
            and self.visitedRelationIds <= self.offeredRelationIds
            # Internal consistency of the instrument: nothing may surface in an
            # answer without having been observed as visited. The final term is
            # transitively implied, and kept as an explicit direct diagnostic.
            and self.returnedRelationIds <= self.visitedRelationIds
            and self.returnedRelationIds <= self.projectedRelationIds
        )


class PathService:
    """Finds admissible paths and explains exclusions over the projected graph."""

    def __init__(
        self,
        store: TierStore,
        grounding: TemporalGroundingProvider,
        projection: ProjectionService,
        relation_state: RelationStateService,
    ) -> None:
        self._store = store
        self._grounding = grounding
        self._projection = projection
        self._relation_state = relation_state

    def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        at: datetime,
        policy_id: str,
        max_depth: int,
        observer_time: datetime | None = None,
    ) -> tuple[list[GroundedPath], list[ExclusionExplanation]]:
        paths, excluded, _ = self.find_paths_traced(
            source_entity_id, target_entity_id, at, policy_id, max_depth, observer_time
        )
        return paths, excluded

    def find_paths_traced(
        self,
        source_entity_id: str,
        target_entity_id: str,
        at: datetime,
        policy_id: str,
        max_depth: int,
        observer_time: datetime | None = None,
    ) -> tuple[list[GroundedPath], list[ExclusionExplanation], TraversalTrace]:
        """As :meth:`find_paths`, plus a trace of what candidate generation saw."""
        projected = self._projection.project(at, policy_id, observer_time)
        admitted_ids = {rel.relationId for rel in projected}
        candidate_edges: list[Edge] = [
            Edge(rel.sourceEntityId, rel.targetEntityId, rel.relationId) for rel in projected
        ]

        # Rule 5: observe the collection actually handed to the generator.
        visited: set[str] = set()
        relation_paths = _edge_paths(
            candidate_edges, source_entity_id, target_entity_id, max_depth, visited=visited
        )
        paths = [
            self._build_path(index, source_entity_id, target_entity_id, rels, at, policy_id,
                             observer_time)
            for index, rels in enumerate(relation_paths)
        ]
        trace = TraversalTrace(
            offeredRelationIds=frozenset(edge.relation_id for edge in candidate_edges),
            visitedRelationIds=frozenset(visited),
            returnedRelationIds=frozenset(
                rid for path in paths for rid in path.relation_ids
            ),
            projectedRelationIds=frozenset(admitted_ids),
            allTimeRelationCount=len(self._store.list_relations()),
        )

        excluded = self._explain_excluded_routes(
            source_entity_id, target_entity_id, max_depth, admitted_ids, at, observer_time
        )
        return paths, excluded, trace

    def validate_path(
        self,
        relation_ids: list[str],
        at: datetime,
        policy_id: str,
        observer_time: datetime | None = None,
    ) -> bool:
        admitted_ids = {
            rel.relationId for rel in self._projection.project(at, policy_id, observer_time)
        }
        return all(rid in admitted_ids for rid in relation_ids)

    def explain_exclusion(
        self,
        relation_ids: list[str],
        at: datetime,
        policy_id: str,
        observer_time: datetime | None = None,
    ) -> list[ExclusionExplanation]:
        admitted_ids = {
            rel.relationId for rel in self._projection.project(at, policy_id, observer_time)
        }
        return [
            self._explain_relation(rid, at, observer_time)
            for rid in relation_ids
            if rid not in admitted_ids
        ]

    # -- internals ---------------------------------------------------------
    def _build_path(
        self,
        index: int,
        source_entity_id: str,
        target_entity_id: str,
        relation_ids: list[str],
        at: datetime,
        policy_id: str,
        observer_time: datetime | None,
    ) -> GroundedPath:
        """Assemble a path, preserving each step's evidential state.

        The state is *not* recomputed loosely here: it is the same snapshot the
        projection used to admit the relation. Dropping it -- as this service
        previously did by reducing each edge to a bare identifier -- makes a
        refuted relation admitted under a recall policy indistinguishable from a
        supported one.
        """
        steps: list[PathStep] = []
        for ordinal, relation_id in enumerate(relation_ids):
            relation = self._store.require_relation(relation_id)
            snapshot = self._relation_state.state_at(
                relation_id, at, observer_time=observer_time
            )
            snapshot.policyId = policy_id
            steps.append(
                PathStep(
                    ordinal=ordinal,
                    relationId=relation_id,
                    fromEntityId=relation.sourceEntityId,
                    toEntityId=relation.targetEntityId,
                    evidentialState=snapshot,
                    admitted=True,
                    direction="outgoing",
                )
            )
        return GroundedPath(
            id=f"{source_entity_id}->{target_entity_id}#{index}",
            sourceEntityId=source_entity_id,
            targetEntityId=target_entity_id,
            steps=steps,
            profileId=self._grounding.profile().id,
            queryTime=iso_z(at),
            policyId=policy_id,
            admissible=all(step.admitted for step in steps),
        )

    def _explain_excluded_routes(
        self,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int,
        admitted_ids: set[str],
        at: datetime,
        observer_time: datetime | None,
    ) -> list[ExclusionExplanation]:
        # Diagnostic only: this enumeration is deliberately over the all-time graph
        # and must never be traced (see TraversalTrace).
        all_edges: list[Edge] = [
            Edge(rel.sourceEntityId, rel.targetEntityId, rel.id)
            for rel in self._store.list_relations()
        ]
        structural_routes = _edge_paths(all_edges, source_entity_id, target_entity_id, max_depth)
        explanations: list[ExclusionExplanation] = []
        seen: set[str] = set()
        for route in structural_routes:
            if all(rid in admitted_ids for rid in route):
                continue  # this route is fully admissible; nothing to explain
            for rid in route:
                if rid in admitted_ids or rid in seen:
                    continue
                seen.add(rid)
                explanations.append(self._explain_relation(rid, at, observer_time))
        return explanations

    def _explain_relation(
        self, relation_id: str, at: datetime, observer_time: datetime | None
    ) -> ExclusionExplanation:
        active = [
            evidence
            for evidence in self._store.get_relation_evidence(relation_id)
            if evidence.reviewStatus not in EXCLUDED_REVIEW_STATUSES
        ]
        if not active:
            return ExclusionExplanation(relationId=relation_id, reasonCode=REASON_NO_EVIDENCE)
        supporting = [e for e in active if e.stance is Stance.SUPPORTS]
        for evidence in supporting or active:
            result = self._grounding.evaluate_evidence(evidence, at, observer_time)
            if not result.admissible:
                return ExclusionExplanation(
                    relationId=relation_id,
                    reasonCode=REASON_SOURCE_STATE,
                    evidenceId=evidence.id,
                )
        # Evidence is admissible, but the resulting state is not admitted by the policy.
        return ExclusionExplanation(relationId=relation_id, reasonCode=REASON_POLICY)


def _edge_paths(
    edges: list[Edge],
    source: str,
    target: str,
    max_depth: int,
    *,
    visited: set[str] | None = None,
) -> list[list[str]]:
    """Deterministic depth-first enumeration of simple relation paths.

    Nodes are visited in edge-insertion order, so output is stable. ``max_depth``
    bounds the number of edges (relations) in a path.

    ``visited`` is an optional accumulator that collects every relation the search
    *considered*, including on branches it abandoned. It is how R7 conformance is
    observed; pass it only for candidate generation, never for diagnostics.
    """
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.from_node].append((edge.to_node, edge.relation_id))

    results: list[list[str]] = []

    def dfs(node: str, seen: frozenset[str], acc: list[str]) -> None:
        # ``acc`` must be non-empty: this operation returns *relational* paths, so
        # the trivial zero-length path from an entity to itself is not a result.
        # Graph theory admits it; this contract deliberately does not, because a
        # zero-step answer carries no evidence and no admissibility to report.
        # Pinned by test_zero_length_paths_are_not_returned.
        if node == target and acc:
            results.append(list(acc))
            return
        if len(acc) >= max_depth:
            return
        for next_node, relation_id in adjacency.get(node, []):
            if visited is not None:
                visited.add(relation_id)
            if next_node in seen:
                continue
            dfs(next_node, seen | {next_node}, [*acc, relation_id])

    dfs(source, frozenset({source}), [])
    return results
