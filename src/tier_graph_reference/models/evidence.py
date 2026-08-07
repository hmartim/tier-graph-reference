"""Evidence models: references, selectors, anchors, and relation evidence.

Conjunctive vs. alternative evidence is structural:

- multiple **anchors inside one** ``RelationEvidence`` are *conjunctive*: the
  record is admissible only when *every* anchor's owning source state is
  admissible (see T05);
- multiple ``RelationEvidence`` records for the same relation are *alternative*
  bases (see T01).
"""

from __future__ import annotations

import json
from typing import NamedTuple

from pydantic import ConfigDict

from .common import ReviewStatus, Stance, TierModel


class EvidenceUnitRef(TierModel):
    """An opaque reference to an evidence unit inside a grounding profile.

    The core never interprets what an evidence unit *is* in the external source
    substrate (e.g. a SAT-Graph ``TextUnit``); it only carries the opaque
    ``profileId`` + ``evidenceUnitId`` and asks the grounding provider about
    admissibility.
    """

    profileId: str
    evidenceUnitId: str


class EvidenceSelector(TierModel):
    """A within-unit selector (e.g. a text position range).

    Selector shapes are open-ended, so extra fields are permitted here.
    """

    model_config = ConfigDict(extra="allow")

    type: str


class EvidenceAnchor(TierModel):
    """One anchor of a relation-evidence record."""

    evidenceUnit: EvidenceUnitRef
    role: str | None = None
    selector: EvidenceSelector | None = None


class EvidenceKey(NamedTuple):
    """The identity of an evidence *occurrence*: ``⟨relationId, anchors, stance⟩``.

    Anchors are canonicalized to a **sorted, de-duplicated tuple** -- a set, as
    the conjunctive reading requires: submitting the same anchors in a different
    order, or repeating one, denotes the same evidential basis (``u ∧ u ≡ u``).
    Each anchor contributes ``⟨profileId, evidenceUnitId, selector⟩``: selectors
    participate in evidence identity (spec/04 §4.4), while ``role`` does not --
    it is a profile-specific annotation that "does NOT alter the default
    conjunctive semantics".

    Deliberately excluded: provenance activity, model, confidence, generation
    time, and review status. None of those constitute a distinct evidential
    basis; treating them as identity-bearing would inflate apparent corroboration
    on every re-extraction, which is exactly what T08 forbids.
    """

    relationId: str
    anchors: tuple[tuple[str, str, str], ...]
    stance: str


def _canonical_selector(selector: EvidenceSelector | None) -> str:
    """Order-insensitive canonical form of a selector, or ``""`` when absent."""
    if selector is None:
        return ""
    return json.dumps(selector.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


class RelationEvidence(TierModel):
    """An evidence record linking a relation to one or more evidence units."""

    id: str
    relationId: str
    anchors: list[EvidenceAnchor]
    stance: Stance = Stance.SUPPORTS
    reviewStatus: ReviewStatus = ReviewStatus.PROPOSED
    provenanceActivityIds: list[str] = []

    @property
    def evidence_unit_ids(self) -> list[str]:
        """Evidence-unit identifiers referenced by this record's anchors, in order."""
        return [anchor.evidenceUnit.evidenceUnitId for anchor in self.anchors]

    @property
    def identity_key(self) -> EvidenceKey:
        """This occurrence's :class:`EvidenceKey` after canonical normalization."""
        return EvidenceKey(
            relationId=self.relationId,
            anchors=tuple(
                sorted(
                    {
                        (
                            anchor.evidenceUnit.profileId,
                            anchor.evidenceUnit.evidenceUnitId,
                            _canonical_selector(anchor.selector),
                        )
                        for anchor in self.anchors
                    }
                )
            ),
            stance=self.stance.value,
        )
