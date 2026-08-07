#!/usr/bin/env python3
"""Run the TIER-Graph conformance suite and write reports to ``results/``."""

from __future__ import annotations

import sys

import _bootstrap  # noqa: F401  (adds src/ to sys.path when run from a checkout)


def main() -> int:
    from tier_graph_reference.conformance.runner import main as run

    return run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
