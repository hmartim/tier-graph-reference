#!/usr/bin/env python3
"""Query a relation's evidential state at two instants (uses fixture T02).

Demonstrates that a relation is ``unsupported`` before its first admissible
source state and ``supported`` afterwards.
"""

from __future__ import annotations

from _common import context_for, load_case
from tier_graph_reference.models import parse_instant


def main() -> None:
    case = load_case("T02")
    ctx = context_for(case)
    relation_id = "dr-housing-social-right"

    for instant in ("1999-01-01T00:00:00Z", "2005-01-01T00:00:00Z"):
        snapshot = ctx.relation_state.state_at(
            relation_id, parse_instant(instant), at_label=instant
        )
        print(f"{instant}: {snapshot.state.value:12s} supporting={snapshot.supportingEvidenceIds}")


if __name__ == "__main__":
    main()
