# Contributing

Thank you for your interest in the TIER-Graph reference implementation.

This repository is a **reference implementation and conformance suite**, not the
normative specification. Normative semantics live in the separate
[`tier-graph-api`](https://github.com/hmartim/tier-graph-api) repository.
Changes that alter conformance semantics should be proposed there first; changes
here should implement or test a released specification version and clearly mark
any implementation-specific choices.

## Development setup

```bash
py -m venv .venv                 # on Windows use `py`; elsewhere `python3`
.venv\Scripts\activate           # PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Before opening a pull request

Run the full local gate:

```bash
python scripts/validate_fixtures.py
python scripts/run_conformance.py
python scripts/reject_private_artifacts.py
pytest
ruff check .
mypy src
```

All of the above must pass. CI runs the same checks on every pull request.

## The privacy boundary is not negotiable

Never add:

- any SAT-Graph source substrate (`item`, `version`, `text_unit`, `action`,
  applicability/validity interval tables);
- production databases, credentials, `.env` files, or internal identifiers;
- non-public source documents.

New fixtures must contain only TIER-derived objects plus a minimal
`profile-fixture.json` of grounding facts. See
[docs/privacy-boundary.md](docs/privacy-boundary.md) and
[docs/fixture-format.md](docs/fixture-format.md).

## Adding a conformance case

1. Create `fixtures/cases/T<NN>-<slug>/` with `input.json`,
   `profile-fixture.json`, `request.json`, `expected.json`, and `README.md`.
2. Register the case in `fixtures/manifest.yaml`.
3. Ensure `python scripts/validate_fixtures.py` and
   `python scripts/run_conformance.py` pass.

## Style

- Python 3.12+, full type annotations, Pydantic v2 models.
- `ruff` for linting and import order; `mypy --strict` for typing.
- Keep route handlers thin: they must call the same services as the runner.
