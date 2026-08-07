# Security Policy

## Reporting a vulnerability

If you discover a security or privacy issue, please report it privately through
the repository's security advisory feature rather than opening a public issue.
We aim to acknowledge reports within a few working days.

## What counts as a privacy issue here

This repository enforces a strict **privacy boundary** (see
[docs/privacy-boundary.md](docs/privacy-boundary.md)). Report as a security/privacy
issue any accidental inclusion of:

- a SAT-Graph source substrate (`item`, `version`, `text_unit`, `action`,
  applicability/validity interval tables), even partially;
- production databases (`*.db`, `*.sqlite`, `*.duckdb`);
- credentials, API keys, `.env` files, or production configuration;
- non-public source documents or internal identifiers.

## Automated defenses

- `.gitignore` blocks database, credential, and environment files.
- `scripts/reject_private_artifacts.py` runs in CI and fails the build if any
  forbidden artifact is present in the tree.

If any of these controls can be bypassed, that is itself a reportable issue.
