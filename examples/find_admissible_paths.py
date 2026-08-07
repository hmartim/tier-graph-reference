#!/usr/bin/env python3
"""Find admissible paths at two instants (uses fixture T10).

Demonstrates that a path relying on a future source state is excluded before its
boundary and admitted afterwards, with a structured exclusion explanation.
"""

from __future__ import annotations

from _common import context_for, load_case
from tier_graph_reference.models import parse_instant


def main() -> None:
    case = load_case("T10")
    ctx = context_for(case)

    for instant in ("2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"):
        paths, excluded = ctx.paths.find_paths(
            "de-a", "de-c", parse_instant(instant), "strict-supported", max_depth=2
        )
        print(f"\n@ {instant}")
        if paths:
            for path in paths:
                print(f"  path: {' -> '.join(path.relationIds)}")
        else:
            print("  no admissible path")
        for exclusion in excluded:
            print(
                f"  excluded {exclusion.relationId}: {exclusion.reasonCode} "
                f"(evidence {exclusion.evidenceId})"
            )


if __name__ == "__main__":
    main()
