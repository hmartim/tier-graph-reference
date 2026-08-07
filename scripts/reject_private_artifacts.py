#!/usr/bin/env python3
"""Fail if any private artifact would be published.

Enforces the privacy boundary in CI (and locally). Rejects databases,
credentials, key material, environment files, private data directories, and
files whose *content* looks like a secret.

The gate answers the question that matters -- *will a private artifact be
published?* -- and not the irrelevant one -- *does the researcher hold private
data in their own workspace?* It therefore inspects what Git **tracks** (and, by
extension, what ``git archive`` would ship), not the working tree. A curated
SAT-Graph export under ``data/private/`` may and must exist locally to produce a
real-substrate run; it simply must never become tracked.

When Git is unavailable (e.g. an unpacked source tarball), the scan falls back to
the working tree minus ignored directories, so the check still means something.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_GLOBS = (
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "*.duckdb",
    "*.parquet",
    "*.mdb",
    "*.accdb",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    ".env",
    ".env.*",
    "credentials*",
)

#: Content patterns that must never appear in a tracked file. Names and
#: extensions are not enough: a secret pasted into a .py or .md passes a
#: filename check. This guards against a future commit, not a present defect.
#: The assignment pattern requires an actual value, so prose that merely names
#: an environment variable does not trip it.
FORBIDDEN_CONTENT = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token)\b"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9/+=_-]{12,}"
    ),
)

FORBIDDEN_DIR_PREFIXES = ("secrets/", "data/private/", "data/local/")

# Only used by the no-Git fallback.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "node_modules",
}


def _tracked_paths(root: Path) -> list[str] | None:
    """Paths Git tracks, or ``None`` when this is not a usable Git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [p for p in result.stdout.split("\0") if p]


def _fallback_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if set(rel.parts) & SKIP_DIRS:
            continue
        paths.append(rel.as_posix())
    return paths


def _offenders(root: Path, paths: list[str]) -> list[str]:
    found: list[str] = []
    for rel_posix in paths:
        if any(rel_posix.startswith(prefix) for prefix in FORBIDDEN_DIR_PREFIXES):
            found.append(f"{rel_posix} (inside a private directory)")
            continue
        name = rel_posix.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(name, pattern) for pattern in FORBIDDEN_GLOBS):
            found.append(rel_posix)
            continue
        path = root / rel_posix
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable: the name check above already applied
        for pattern in FORBIDDEN_CONTENT:
            if pattern.search(text):
                found.append(f"{rel_posix} (content matches a secret pattern)")
                break
    return found


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tracked = _tracked_paths(root)
    if tracked is None:
        scope = "working tree (Git unavailable)"
        paths = _fallback_paths(root)
    else:
        scope = "tracked files"
        paths = tracked

    offenders = _offenders(root, paths)
    if offenders:
        print(f"Private-artifact check FAILED ({scope}). These must not be published:")
        for line in sorted(offenders):
            print(f"  - {line}")
        print()
        print("Untrack them (`git rm --cached <path>`) and confirm .gitignore covers them.")
        return 1

    print(
        f"Private-artifact check passed ({len(paths)} {scope}): "
        "no databases, credentials, key material, env files, private data "
        "directories, or secret-shaped content."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
