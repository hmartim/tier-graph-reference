"""SAT-Graph adapter integration tests using mocked HTTP responses only.

These never touch a private database, credentials, or a live service. The core
conformance suite does not depend on any of this.
"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx")
import httpx

from tier_graph_reference.adapters.sat_graph import (
    SatGraphClient,
    SatGraphGroundingConfig,
    SatGraphHttpGroundingProvider,
)
from tier_graph_reference.models import (
    EvidenceAnchor,
    EvidenceUnitRef,
    RelationEvidence,
    parse_instant,
)


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/text-units/tu-x":
        return httpx.Response(200, json={"id": "tu-x", "sourceType": "Version", "sourceId": "v-x"})
    if path == "/versions/v-x":
        return httpx.Response(
            200,
            json={
                "id": "v-x",
                "itemId": "item-x",
                "applicabilityInterval": ["2020-01-01T00:00:00Z", None],
            },
        )
    if path == "/items/item-x/applicable-versions":
        at = request.url.params.get("at", "")
        applicable = ["v-x"] if at >= "2020-01-01T00:00:00Z" else []
        return httpx.Response(200, json=[{"id": vid} for vid in applicable])
    return httpx.Response(404, json={"detail": "not found"})


def _provider() -> SatGraphHttpGroundingProvider:
    client = SatGraphClient(
        base_url="https://sat-graph.example", transport=httpx.MockTransport(_handler)
    )
    config = SatGraphGroundingConfig(base_url="https://sat-graph.example", profile_version="test")
    return SatGraphHttpGroundingProvider(config, client=client)


_EVIDENCE = RelationEvidence(
    id="e",
    relationId="r",
    anchors=[EvidenceAnchor(evidenceUnit=EvidenceUnitRef(profileId="p", evidenceUnitId="tu-x"))],
)


def test_admissibility_decided_by_endpoint() -> None:
    provider = _provider()
    before = provider.evaluate_evidence(_EVIDENCE, parse_instant("2019-01-01T00:00:00Z"))
    after = provider.evaluate_evidence(_EVIDENCE, parse_instant("2021-01-01T00:00:00Z"))
    assert before.admissible is False
    assert after.admissible is True


def test_resolve_source_state_maps_text_unit_to_version() -> None:
    provider = _provider()
    state = provider.resolve_source_state("tu-x")
    assert state is not None
    assert state.id == "v-x"


def test_profile_reports_configured_version() -> None:
    provider = _provider()
    assert provider.profile().version == "test"


def test_from_env_requires_base_url() -> None:
    with pytest.raises(RuntimeError):
        SatGraphGroundingConfig.from_env({})
