"""Make ``tier_graph_reference`` importable when running scripts from a checkout.

If the package is installed (``pip install -e .``) this is a no-op; otherwise it
adds ``src/`` to ``sys.path`` so the scripts work directly from the repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
