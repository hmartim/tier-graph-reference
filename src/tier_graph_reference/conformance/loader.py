"""Load the fixture manifest and conformance cases from disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..models import INTERVAL_KEYS

CASE_FILES = ("input.json", "profile-fixture.json", "request.json", "expected.json")


class FixtureError(ValueError):
    """Raised when a fixture payload violates a structural invariant."""


def _assert_no_relation_intervals(case_id: str, raw_input: dict[str, Any]) -> None:
    """Enforce R3 at the fixture level, before Pydantic validation.

    ``extra="forbid"`` already makes such a relation unconstructible, but the
    resulting ValidationError does not say *why* the key is forbidden. Scanning
    the raw document turns an authoring mistake into a message that names the
    invariant.
    """
    for relation in raw_input.get("relations", []):
        offending = sorted(INTERVAL_KEYS & set(relation))
        if offending:
            raise FixtureError(
                f"{case_id}: relation {relation.get('id', '<no id>')!r} carries "
                f"authoritative interval key(s) {offending}. A DerivedRelation must not "
                f"copy source-state intervals (R3); temporal state is derived through "
                f"the grounding profile."
            )


@dataclass(frozen=True)
class ConformanceCase:
    """One executable conformance case, with its four payloads and declarations."""

    case_id: str
    title: str
    directory: Path
    operation: str
    conformance_class: str
    grounding_profile_id: str
    grounding_profile_version: str
    case_definition_reference: dict[str, Any]
    competency_questions: list[str]
    #: Declared divergence from the normative catalogue, when the fixture runs a
    #: different operation. ``None`` means the operation matches. See
    #: tests/conformance/test_normative_alignment.py.
    normative_alignment: dict[str, Any] | None
    input: dict[str, Any]
    profile: dict[str, Any]
    request: dict[str, Any]
    expected: dict[str, Any]


@dataclass(frozen=True)
class FixtureManifest:
    """The parsed ``manifest.yaml``."""

    implements: str
    specification_version: str
    fixture_set_version: str
    cases: list[ConformanceCase] = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def load_manifest(fixtures_dir: str | Path) -> FixtureManifest:
    """Load the manifest and every case it registers."""
    root = Path(fixtures_dir)
    manifest_raw = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))

    cases: list[ConformanceCase] = []
    for entry in manifest_raw.get("cases", []):
        case_dir = root / entry["directory"]
        payloads = {name: _read_json(case_dir / name) for name in CASE_FILES}
        _assert_no_relation_intervals(entry["id"], payloads["input.json"])
        cases.append(
            ConformanceCase(
                case_id=entry["id"],
                title=entry.get("title", entry["id"]),
                directory=case_dir,
                operation=entry["operation"],
                conformance_class=entry.get("conformanceClass", "Query API Conformance"),
                grounding_profile_id=entry.get("groundingProfileId", ""),
                grounding_profile_version=entry.get("groundingProfileVersion", ""),
                case_definition_reference=entry.get("caseDefinitionReference", {}),
                competency_questions=list(entry.get("competencyQuestions", [])),
                normative_alignment=entry.get("normativeAlignment"),
                input=payloads["input.json"],
                profile=payloads["profile-fixture.json"],
                request=payloads["request.json"],
                expected=payloads["expected.json"],
            )
        )

    return FixtureManifest(
        implements=manifest_raw.get("implements", ""),
        specification_version=manifest_raw.get("specificationVersion", ""),
        fixture_set_version=manifest_raw.get("fixtureSetVersion", ""),
        cases=cases,
    )


def default_fixtures_dir() -> Path:
    """Best-effort location of the repository ``fixtures/`` directory."""
    # src/tier_graph_reference/conformance/loader.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3] / "fixtures"
