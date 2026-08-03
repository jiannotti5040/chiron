#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
apply_license_headers — stamp the Apache-2.0 SPDX header onto every Python file
in the repository, idempotently, REPLACING any older header it finds.

In a per-script architecture each file is meant to stand alone and emit its own
attributed artifact (the certificates already stamp owner=Jacob Iannotti); the
source should match.

    python3 apply_license_headers.py            # dry-run: list what WOULD change
    python3 apply_license_headers.py --write    # apply in place
    python3 apply_license_headers.py --write --root .   # whole repo (default)

Reports a diff-style summary. Safe to run repeatedly.

WHY THIS REPLACES INSTEAD OF ONLY INSERTING
-------------------------------------------
The previous version only ever inserted, and guarded on the bare key
`SPDX-License-Identifier`. That made the 2026 relicensing from PolyForm
Noncommercial to Apache-2.0 a trap with two failure modes, both verified
empirically before this rewrite:

  * Swap only the HEADER text and leave the guard alone -> the guard still
    matches the OLD PolyForm line, every already-stamped file is skipped, and
    the run prints "STAMPED 0 file(s)" and exits 0. A silent no-op that
    REPORTS SUCCESS is the worst possible outcome for a relicense.

  * Tighten the guard to the full new id so it stops matching PolyForm ->
    the new pair is inserted ABOVE the old pair, leaving two contradictory
    SPDX identifiers in one file. The next run then reports 0 changed, so the
    damaged state is stable and never self-heals.

So: strip first, then insert. `_strip_old` removes any prior SPDX line, any
PolyForm "Required Notice:" line, and any bare copyright comment in the header
block, so re-running after a future license change actually converts rather
than silently doing nothing.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Tuple

HEADER = [
    "# SPDX-License-Identifier: Apache-2.0",
    "# Copyright 2026 Jacob Iannotti",
]

# Lines in the header block that this tool owns and may rewrite. Anything
# matching these is stripped before the current HEADER is inserted.
OWNED = (
    re.compile(r"^#\s*SPDX-License-Identifier:"),
    re.compile(r"^#\s*Required Notice:"),
    re.compile(r"^#\s*Copyright\s+(\(c\)\s*)?\d{4}\s+Jacob Iannotti", re.I),
)

# How far into the file a header line may appear to be considered part of the
# header block rather than body content.
HEADER_WINDOW = 8

SKIP_DIRS = {
    "__pycache__", "artifacts", ".git", ".venv", "venv", "env", "node_modules",
    # never ours to stamp / explicitly out of scope
    "Acciaio",
    # hash-pinned replay evidence: stamping changes the SHA-256 the capsule
    # manifest records, and `capsule verify` would then correctly REFUSE.
    "capsules",
    # regenerated caches and shadow checkouts
    ".claude", "graphify-out", "build", "dist", "site-packages",
    ".mypy_cache", ".pytest_cache", ".trash", "outputs",
}

# Individual files whose bytes are pinned by a manifest hash elsewhere in the
# repo. Stamping any of these breaks a working integrity gate.
SKIP_FILES = {
    "a063880_capsule.py",
}


def _strip_old(lines: List[str]) -> Tuple[List[str], bool]:
    """Remove any header lines this tool owns. Returns (lines, removed_any)."""
    out, removed = [], False
    for i, ln in enumerate(lines):
        if i < HEADER_WINDOW and any(p.match(ln) for p in OWNED):
            removed = True
            continue
        out.append(ln)
    return out, removed


def _insert(src: str) -> Tuple[str, bool]:
    """Return (new_src, changed). Idempotent: strips any old header first."""
    lines = src.split("\n")
    lines, _ = _strip_old(lines)

    insert_at = 0
    # keep shebang first
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # keep coding line right after (PEP 263 allows it on line 1 or 2)
    if (len(lines) > insert_at and "coding" in lines[insert_at]
            and lines[insert_at].lstrip().startswith("#")):
        insert_at += 1

    new = lines[:insert_at] + HEADER + lines[insert_at:]
    new_src = "\n".join(new)
    return new_src, new_src != src


def run(root: str, write: bool) -> List[str]:
    changed: List[str] = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(".py") or fn in SKIP_FILES:
                continue
            path = os.path.join(dirpath, fn)
            try:
                src = open(path, encoding="utf-8").read()
            except Exception:
                continue
            new, did = _insert(src)
            if did:
                changed.append(os.path.relpath(path, root))
                if write:
                    open(path, "w", encoding="utf-8").write(new)
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Apply Apache-2.0 SPDX headers idempotently, replacing older ones.")
    # default to the repo root (this file lives in Chiron/), not just Chiron/
    ap.add_argument("--root", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--write", action="store_true", help="apply in place (default: dry-run)")
    args = ap.parse_args(argv)

    changed = run(args.root, args.write)
    verb = "STAMPED" if args.write else "WOULD STAMP"
    print(f"[license] {verb} {len(changed)} file(s) under {os.path.relpath(args.root)}")
    for c in changed[:50]:
        print(f"  + {c}")
    if len(changed) > 50:
        print(f"  ... and {len(changed) - 50} more")
    if not args.write and changed:
        print("\n  dry-run only — re-run with --write to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
