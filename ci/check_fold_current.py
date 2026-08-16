#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Fail if the committed artifact does not match the source it was folded from.

`Chiron Monolith/chiron_monolith.py` is generated from `Chiron/*.py`. Editing a
source module without rebuilding leaves the shipped artifact describing code
that no longer exists, and the two incarnations stop being one organism.

CI has always checked this. The local battery did not, so the failure could
only be discovered after a push -- which is exactly how it was discovered.
This closes that gap: the same check, before the push.

The test is that rebuilding changes nothing. The builder resolves `Chiron/`
relative to its own location, so it cannot be run against a detached copy; it
runs in place and the artifact's original bytes are written back afterwards.
That restoration is exact -- the bytes are held in memory across the rebuild --
so a stale tree is reported and left exactly as it was found, rather than
silently repaired by the act of measuring it.

    python3 ci/check_fold_current.py
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONO_DIR = os.path.join(ROOT, "Chiron Monolith")
BUILDER = os.path.join(MONO_DIR, "build_monolith.py")
ARTIFACT = os.path.join(MONO_DIR, "chiron_monolith.py")


def main() -> int:
    if not (os.path.isfile(BUILDER) and os.path.isfile(ARTIFACT)):
        print("fold-current: no artifact or builder; skipping")
        return 0

    original = open(ARTIFACT, "rb").read()
    committed = hashlib.sha256(original).hexdigest()
    try:
        result = subprocess.run([sys.executable, "build_monolith.py"],
                                cwd=MONO_DIR, capture_output=True, text=True)
        if result.returncode != 0:
            print("fold-current: FAIL — the fold does not build:")
            print((result.stderr or result.stdout)[-1500:])
            return 1
        rebuilt = hashlib.sha256(open(ARTIFACT, "rb").read()).hexdigest()
    finally:
        # Leave the tree exactly as it was found, whatever the verdict.
        if open(ARTIFACT, "rb").read() != original:
            open(ARTIFACT, "wb").write(original)

    if rebuilt != committed:
        print("fold-current: FAIL — the committed artifact is stale.")
        print("  committed %s…" % committed[:16])
        print("  rebuilt   %s…" % rebuilt[:16])
        print("  A Chiron/*.py module changed without a rebuild. Run "
              "`python3 bin/chiron build` and commit the artifact.")
        return 1

    print("fold-current: PASS — the artifact matches its source (%s…)"
          % committed[:16])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
