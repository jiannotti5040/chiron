#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Refuse committed iCloud/Finder conflicted copies.

The vault lives in a cloud-synced directory. When two machines touch the same
file the provider writes a second one beside it -- `Endpoint.swift` becomes
`Endpoint 2.swift` -- and a `git add -A` commits the copy without anyone
seeing it. Fifty-three arrived in a single commit that way. Two of them broke
the iOS build, because Swift saw every type declared twice, and one broke the
license gate by duplicating an audit file the gate deliberately excludes.

`.gitignore` blocks the common extensions. This gate is the backstop for the
paths that pattern misses, and it is deliberately narrower than the ignore
rule: it fails only on a file whose original exists beside it, so a document
legitimately named `Blank 13.pdf` -- there are two in the UMA source
materials -- is left alone.

    python3 ci/check_duplicates.py
"""
from __future__ import annotations

import filecmp
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUFFIX = re.compile(r" \d+(\.[A-Za-z0-9]+)$")


def main() -> int:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT,
                             capture_output=True, text=True).stdout.split("\n")
    findings = []
    for rel in tracked:
        if not rel or not SUFFIX.search(rel):
            continue
        original = SUFFIX.sub(r"\1", rel)
        full, orig_full = os.path.join(ROOT, rel), os.path.join(ROOT, original)
        if not os.path.isfile(orig_full) or not os.path.isfile(full):
            continue          # no original beside it — a real filename
        try:
            if filecmp.cmp(full, orig_full, shallow=False):
                findings.append((rel, original))
        except OSError:
            continue

    if findings:
        print("duplicates: FAIL — %d conflicted copy/copies committed:" % len(findings))
        for dupe, original in findings[:40]:
            print("  %s  (identical to %s)" % (dupe, original))
        print("\nDelete the copy, not the original. Both are byte-identical, so "
              "nothing is lost.")
        return 1

    print("duplicates: PASS — no conflicted copies among %d tracked files"
          % len([t for t in tracked if t]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
