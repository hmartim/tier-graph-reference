#!/usr/bin/env python3
"""Print a relation's evidential-state history (uses fixture T01).

Demonstrates one relation supported across successive source states by different
alternative evidence records, without copying any interval onto the relation.
"""

from __future__ import annotations

from _common import context_for, load_case
from tier_graph_reference.models import parse_instant


def main() -> None:
    case = load_case("T01")
    ctx = context_for(case)
    entries = ctx.relation_state.history(
        "dr-education-social-right",
        start=parse_instant("1988-10-05T00:00:00Z"),
        end=parse_instant("2026-01-01T00:00:00Z"),
    )
    for entry in entries:
        to = entry.to or "open"
        print(f"[{entry.from_} -> {to}) {entry.state.value:11s} by {entry.supportingEvidenceIds}")


if __name__ == "__main__":
    main()
