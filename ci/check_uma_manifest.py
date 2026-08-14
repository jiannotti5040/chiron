#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Verify UMA Suite/MANIFEST.sha256 under the project's own errata convention.

`MANIFEST.sha256` is a sealed, chain-hashed provenance artifact. The project's
rule, stated in `MANIFEST_ERRATA.md`, is that it is preserved byte-identical
and every subsequent change to the tree it describes is recorded in the errata
rather than edited into the manifest.

A naive verifier reports that manifest as failing on more than half its
entries, which reads as tampering and is wrong twice over: some paths were
deliberately changed and recorded, and five entries cover `.pytest_cache`
files that pytest rewrites on every run and can never verify.

This separates the three cases so a real mismatch is visible:

  * verified        — digest matches the manifest
  * recorded        — digest differs and the current digest appears in the errata
  * volatile        — a path the errata declares permanently unverifiable
  * UNEXPLAINED     — digest differs and nothing accounts for it

Only the last is a failure.

    python3 ci/check_uma_manifest.py
"""
from __future__ import annotations

import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUITE = os.path.join(ROOT, "UMA Suite")
MANIFEST = os.path.join(SUITE, "MANIFEST.sha256")
ERRATA = os.path.join(SUITE, "MANIFEST_ERRATA.md")

VOLATILE = (".pytest_cache", "__pycache__")


def errata_digests() -> set:
    """Every SHA-256 the errata records as an accepted post-seal value."""
    if not os.path.isfile(ERRATA):
        return set()
    text = open(ERRATA, encoding="utf-8").read()
    return set(re.findall(r"\b([0-9a-f]{64})\b", text))


def main() -> int:
    if not os.path.isfile(MANIFEST):
        print("uma-manifest: no manifest; skipping")
        return 0

    accepted = errata_digests()
    verified = recorded = volatile = missing = 0
    unexplained = []

    for line in open(MANIFEST, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            continue
        _chain, digest, _size, path = parts
        path = path.strip()
        relative = path[2:] if path.startswith("./") else path
        if any(marker in relative for marker in VOLATILE):
            volatile += 1
            continue
        full = os.path.join(SUITE, relative)
        if not os.path.isfile(full):
            missing += 1
            continue
        actual = hashlib.sha256(open(full, "rb").read()).hexdigest()
        if actual == digest:
            verified += 1
        elif actual in accepted:
            recorded += 1
        else:
            unexplained.append((relative, actual[:16]))

    print("uma-manifest: %d verified · %d recorded in errata · %d volatile · "
          "%d missing" % (verified, recorded, volatile, missing))
    if unexplained:
        print("uma-manifest: FAIL — %d entries differ with nothing accounting "
              "for them:" % len(unexplained))
        for relative, prefix in unexplained[:20]:
            print("  %s  now %s…" % (relative, prefix))
        print("  Record the change in MANIFEST_ERRATA.md, or restore the file. "
              "Do not edit MANIFEST.sha256.")
        return 1
    print("uma-manifest: PASS — every difference is accounted for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
