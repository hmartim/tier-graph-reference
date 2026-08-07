# SAT-Graph adapter (optional legal integration)

SAT-Graph is **one optional, substitutable** temporal grounding integration. It
is **not** required for TIER-Graph conformance: the public suite runs entirely on
the fixture provider. The core services never import a SAT-Graph model; the
adapter lives outside the core under `adapters/sat_graph/`.

```
src/tier_graph_reference/adapters/sat_graph/
├── models.py     # adapter-only SatGraphTextUnit / SatGraphVersion
├── client.py     # thin, configurable HTTP client (no host/creds in source)
├── mapping.py    # EvidenceUnitRef→TextUnit, SourceState→Version, ...
└── provider.py   # SatGraphHttpGroundingProvider + SatGraphGroundingConfig
```

It is re-exported at `tier_graph_reference.grounding.sat_graph_http` for a stable
import path. Using it requires the `httpx` extra:

```bash
pip install -e ".[http]"     # or ".[dev]"
```

## Configuration (no secrets in source)

There is no hard-coded endpoint and no embedded credential. Configure via the
environment:

| Variable | Meaning |
|---|---|
| `SATGRAPH_API_BASE_URL` | Base URL of the SAT-Graph API (required). |
| `SATGRAPH_API_KEY` | API key sent in the `Authorization` header (optional). |
| `SATGRAPH_PROFILE_ID` | Profile id to report (default `sat-graph`). |
| `SATGRAPH_PROFILE_VERSION` | Profile version to report (default `unknown`). |

```python
from tier_graph_reference.adapters.sat_graph import (
    SatGraphGroundingConfig, SatGraphHttpGroundingProvider,
)
from tier_graph_reference.services import ServiceContext
from tier_graph_reference.store.memory import MemoryTierStore

config = SatGraphGroundingConfig.from_env()   # reads SATGRAPH_API_BASE_URL, ...
grounding = SatGraphHttpGroundingProvider(config)
ctx = ServiceContext.build(MemoryTierStore.from_input(my_tier_objects), grounding)
```

## Mappings (adapter-only)

| TIER reference | SAT-Graph identifier |
|---|---|
| `EvidenceUnitRef.evidenceUnitId` | `TextUnit` id |
| source state | `Version` id (a `TextUnit.sourceId`) |
| source identity | `Item` id (a `Version.itemId`) |
| transition provenance | `Action` id (a `Version.terminatedByActionId`) |

These mappings belong only to the adapter. `TextUnit`, `Version`, `Item`, and
`Action` are never exposed as TIER-Graph core types. Override
`SatGraphMapping` if a deployment uses a different convention.

## Admissibility is decided by the endpoint

The adapter never fabricates intervals locally. To evaluate a source state at
time `t` it calls the SAT-Graph `getApplicableVersions` endpoint and checks
membership. Endpoint path templates are configurable (`SatGraphEndpoints`) so the
client can track a verified SAT-Graph API version; the defaults follow the
published SAT-Graph API (`/text-units/{textUnitId}`, `/versions/{versionId}`,
`/items/{itemId}/applicable-versions`). Verify them against your SAT-Graph
deployment before use.

## Testing

Adapter tests use **mocked HTTP responses only** (`httpx.MockTransport`) — see
`tests/adapters/sat_graph/`. They never require the private SAT-Graph database,
credentials, local source access, or ingestion/curation code. The normal
conformance suite passes without installing or configuring the adapter.
