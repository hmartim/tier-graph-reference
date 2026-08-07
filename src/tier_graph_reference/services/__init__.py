"""Core services, wired over a ``TierStore`` and a ``TemporalGroundingProvider``.

All services receive their grounding provider by dependency injection; none
import a concrete grounding substrate. ``ServiceContext`` is a convenience that
constructs the full set from one store + one provider, and is reused by both the
offline conformance runner and the optional FastAPI facade.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..grounding.base import TemporalGroundingProvider
from ..store.base import TierStore, WritableTierStore
from .admissibility import AdmissibilityService
from .audit import AuditService
from .authoring import EvidenceAuthoringService, EvidenceSubmissionOutcome
from .identity import IdentityComparison, RelationIdentityService
from .paths import PathService, TraversalTrace
from .projection import ProjectionService
from .relation_state import RelationStateService

__all__ = [
    "AdmissibilityService",
    "AuditService",
    "EvidenceAuthoringService",
    "EvidenceSubmissionOutcome",
    "IdentityComparison",
    "PathService",
    "ProjectionService",
    "RelationIdentityService",
    "RelationStateService",
    "ServiceContext",
    "TraversalTrace",
]


@dataclass(frozen=True)
class ServiceContext:
    """A fully wired set of services over one store and one grounding provider."""

    store: TierStore
    grounding: TemporalGroundingProvider
    identity: RelationIdentityService
    admissibility: AdmissibilityService
    relation_state: RelationStateService
    projection: ProjectionService
    paths: PathService
    audit: AuditService
    #: ``None`` when the store is read-only. Authoring is an optional
    #: conformance class, so a read-only deployment stays valid.
    authoring: EvidenceAuthoringService | None

    @classmethod
    def build(
        cls, store: TierStore, grounding: TemporalGroundingProvider
    ) -> ServiceContext:
        relation_state = RelationStateService(store, grounding)
        projection = ProjectionService(store, relation_state)
        authoring = (
            EvidenceAuthoringService(store) if isinstance(store, WritableTierStore) else None
        )
        return cls(
            store=store,
            grounding=grounding,
            identity=RelationIdentityService(),
            admissibility=AdmissibilityService(store, grounding),
            relation_state=relation_state,
            projection=projection,
            paths=PathService(store, grounding, projection, relation_state),
            audit=AuditService(store, grounding, relation_state),
            authoring=authoring,
        )

    def require_authoring(self) -> EvidenceAuthoringService:
        if self.authoring is None:
            raise TypeError(
                "authoring operations require a writable TierStore; "
                f"{type(self.store).__name__} is read-only"
            )
        return self.authoring
