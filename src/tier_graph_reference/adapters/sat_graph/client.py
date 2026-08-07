"""A thin, configurable HTTP client for the SAT-Graph API.

No endpoint is hard-coded to a host and no credentials are embedded in source:
the base URL and API key come from configuration (typically environment
variables). Endpoint path templates are configurable so the client can track a
verified SAT-Graph API version. Tests drive this client with mocked transports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .models import SatGraphTextUnit, SatGraphVersion

if TYPE_CHECKING:  # pragma: no cover - typing only
    import httpx


@dataclass
class SatGraphEndpoints:
    """Configurable endpoint path templates (verify against the SAT-Graph spec)."""

    text_unit: str = "/text-units/{textUnitId}"
    version: str = "/versions/{versionId}"
    applicable_versions: str = "/items/{itemId}/applicable-versions"
    valid_versions: str = "/items/{itemId}/valid-versions"


@dataclass
class SatGraphClient:
    """Minimal SAT-Graph HTTP client used by the grounding adapter."""

    base_url: str
    api_key: str | None = None
    endpoints: SatGraphEndpoints = field(default_factory=SatGraphEndpoints)
    timeout: float = 10.0
    transport: Any = None  # httpx.BaseTransport | None; injected in tests
    _client: httpx.Client | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        import httpx

        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = self.api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            transport=self.transport,
        )

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        if self._client is not None:
            self._client.close()

    def __enter__(self) -> SatGraphClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- requests ----------------------------------------------------------
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        assert self._client is not None
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def get_text_unit(self, text_unit_id: str) -> SatGraphTextUnit:
        data = self._get(self.endpoints.text_unit.format(textUnitId=text_unit_id))
        return SatGraphTextUnit.model_validate(data)

    def get_version(self, version_id: str) -> SatGraphVersion:
        data = self._get(self.endpoints.version.format(versionId=version_id))
        return SatGraphVersion.model_validate(data)

    def get_applicable_version_ids(
        self, item_id: str, at: str, observer_time: str | None = None
    ) -> list[str]:
        params: dict[str, Any] = {"at": at}
        if observer_time is not None:
            params["observerTime"] = observer_time
        data = self._get(
            self.endpoints.applicable_versions.format(itemId=item_id), params=params
        )
        # SAT-Graph deployments may return numeric ids; normalize to strings so
        # membership tests against string source-state ids remain correct.
        return [str(entry["id"]) for entry in data if "id" in entry]
