"""FastAPI facade smoke tests (thin routes over the same services)."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from tier_graph_reference.api.app import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    os.environ["TIER_DEMO_FIXTURE"] = "T01"
    return TestClient(create_app())


def test_profile(client: TestClient) -> None:
    response = client.get("/profile")
    assert response.status_code == 200
    assert response.json()["id"] == "public-legal-fixture"


def test_relations_listed(client: TestClient) -> None:
    response = client.get("/relations")
    assert response.status_code == 200
    ids = {r["id"] for r in response.json()}
    assert "dr-education-social-right" in ids


def test_relation_history(client: TestClient) -> None:
    response = client.get(
        "/relations/dr-education-social-right/history",
        params={"startAt": "1988-10-05T00:00:00Z", "endAt": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 200
    periods = response.json()["statePeriods"]
    assert len(periods) == 4
    assert all(p["state"] == "supported" for p in periods)
    assert periods[0]["from"] == "1988-10-05T00:00:00Z"


def test_healthz_is_non_normative(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["x-tier-reference"] == "non-normative"


def test_unknown_relation_is_404(client: TestClient) -> None:
    assert client.get("/relations/does-not-exist").status_code == 404
