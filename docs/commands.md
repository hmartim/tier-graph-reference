# Install and test commands

Quick reference for setting up the environment and running the full local gate.

## Install

```powershell
# Windows / PowerShell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

```bash
# macOS / Linux (bash)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Test / verify (the full local gate)

Run these from the repository root with the virtualenv active. All must pass; CI
runs the same checks on every pull request.

```powershell
python scripts/validate_fixtures.py         # structure + JSON Schema + TIER-model validity
python scripts/run_conformance.py           # execute T01-T10, write results/
python scripts/check_results_current.py     # published results must match a fresh run
python scripts/reject_private_artifacts.py  # privacy guard (no tracked DBs/creds/.env)
pytest                                       # unit + integration + conformance + adapter
ruff check .                                 # lint + import order
mypy src                                     # strict type check
```

Expected outcome (v0.1.0): fixtures valid · **10/10 conformance passed** ·
privacy check passed · pytest passes · ruff clean · mypy clean.

## Optional extras

```powershell
# Optional HTTP facade (implementation artifact, not the normative API)
pip install -e ".[api]"
uvicorn tier_graph_reference.api.app:app --reload   # then open http://127.0.0.1:8000/docs

# Build the TIER-only sample SQLite DB (gitignored, rebuilt on demand)
python scripts/build_sample_tier_db.py              # -> build/sample-tier.db

# Optional SAT-Graph adapter (mocked in tests; needs configuration to run live)
pip install -e ".[http]"
$env:SATGRAPH_API_BASE_URL = "https://your-sat-graph.example"   # PowerShell
```
