#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
apply_license_headers — stamp the PolyForm Noncommercial SPDX header onto every
Python file in the vault, idempotently.

In a per-script architecture each file is meant to stand alone and emit its own
attributed artifact (the certificates already stamp owner=Jacob Iannotti); the
source should match. This inserts the header AFTER any shebang and any coding
line, and never doubles up if it is already present.

    python3 apply_license_headers.py            # dry-run: list what WOULD change
    python3 apply_license_headers.py --write     # apply in place
    python3 apply_license_headers.py --write --root ..   # cover the whole repo

Reports a diff-style summary. Safe to run repeatedly.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

HEADER = [
    "# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0",
    "# Required Notice: Copyright © 2026 Jacob Iannotti. "
    "Commercial rights reserved. See LICENSE.md.",
]
MARKER = "SPDX-License-Identifier"

SKIP_DIRS = {"__pycache__", "artifacts", ".git", ".venv", "node_modules"}


def _insert(src: str) -> Tuple[str, bool]:
    """Return (new_src, changed). Idempotent."""
    if MARKER in src.split("\n", 6)[0:6].__str__():  # cheap early check
        # precise check: marker within first 6 lines
        head = src.splitlines()[:6]
        if any(MARKER in ln for ln in head):
            return src, False

    lines = src.split("\n")
    insert_at = 0
    # keep shebang first
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    # keep coding line right after (PEP 263 allows it on line 1 or 2)
    if len(lines) > insert_at and "coding" in lines[insert_at] and lines[insert_at].lstrip().startswith("#"):
        insert_at += 1

    new = lines[:insert_at] + HEADER + lines[insert_at:]
    return "\n".join(new), True


def run(root: str, write: bool) -> List[str]:
    changed: List[str] = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                src = open(path, encoding="utf-8").read()
            except Exception:
                continue
            head = src.splitlines()[:6]
            if any(MARKER in ln for ln in head):
                continue
            new, did = _insert(src)
            if did:
                changed.append(os.path.relpath(path, root))
                if write:
                    open(path, "w", encoding="utf-8").write(new)
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Apply PolyForm SPDX headers idempotently.")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
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
