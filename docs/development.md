# Development

## Environment

```bash
py -m venv .venv                    # Windows: py   ·   elsewhere: python3 -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell   ·   bash: source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.12+.

## The local gate

```bash
python scripts/validate_fixtures.py        # structure + schema + TIER-model validity
python scripts/run_conformance.py          # T01-T10, writes results/
python scripts/reject_private_artifacts.py # privacy guard
pytest                                     # unit + integration + conformance + adapter
ruff check .                               # lint + import order
mypy src                                   # strict type check
```

CI runs the same checks (see `.github/workflows/`).

## Building the TIER-only SQLite database

```bash
python scripts/build_sample_tier_db.py
# -> build/sample-tier.db  (gitignored, rebuilt on demand)
```

The schema contains only TIER-derived tables:

```
derived_entity, derived_relation, relation_qualifier,
relation_evidence, evidence_anchor, provenance_activity,
evidence_provenance_activity, review_event, admission_policy
```

It never contains `item`, `version`, `text_unit`, `action`,
`applicability_interval`, or `validity_interval`. The build calls
`assert_no_source_tables()` to verify this. External references remain opaque
strings such as `public-legal:tu-art6-1988`.

## Running the optional API

```bash
pip install -e ".[api]"
uvicorn tier_graph_reference.api.app:app --reload
# open http://127.0.0.1:8000/docs
```

The facade seeds a demo dataset from a fixture case (env `TIER_DEMO_FIXTURE`,
default `T01`). Route handlers are thin and call the same services as the runner.

## Configuring the SAT-Graph adapter

See [sat-graph-adapter.md](sat-graph-adapter.md). In short: install the `http`
extra and set `SATGRAPH_API_BASE_URL` (and optionally `SATGRAPH_API_KEY`). The
adapter is optional and validated with mocked responses only.


## Layout

See [architecture.md](architecture.md) for the module map and layer boundaries.

## Limitations of fixture-based validation

- Single-perspective grounding (`observerTime` accepted but inert in fixtures).
- Fixtures assert targeted invariants, not exhaustive behavior.
- Conformance here is of the *implementation against the pinned spec draft*, not
  a certification of the normative specification itself.
