"""TIER-Graph reference implementation.

TIER = Temporally Indexed Evidence-Linked Relations.

This package is one implementation of the normative ``tier-graph-api``
specification. The dependency direction is strictly
``tier-graph-reference -> tier-graph-api``; this package never redefines
normative semantics.
"""

from __future__ import annotations

#: Version of this reference implementation.
__version__ = "0.1.0"

#: The normative specification version this release implements.
SPECIFICATION_VERSION = "0.1.0-draft"

#: Convenience banner used in reports and CLIs.
IMPLEMENTS = f"tier-graph-api v{SPECIFICATION_VERSION}"

__all__ = ["IMPLEMENTS", "SPECIFICATION_VERSION", "__version__"]
