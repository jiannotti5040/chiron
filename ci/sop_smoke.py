#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
sop_smoke — run the commands the SOP documents, exactly as written, so a
documented command that breaks turns the build red.

The failure this exists to prevent: a user copy-pastes a command from the
docs and it dies (an inline `# comment` a shell rejects, a `<placeholder>`
the shell tries to glob, a moved script). If the docs say you can run it,
this proves you can.

    python3 ci/sop_smoke.py

stdlib only. Runs from the vault root.
"""
from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

# (label, argv, must_contain) — argv is a real command line, no shell.
CASES = [
    ("collapse Fibonacci (SOP 1.1)",
     [PY, "-c",
      "import sys; sys.path.insert(0, r'%s'); "
      "from primus.engine import collapse; "
      "print(collapse([1,1,2,3,5,8,13,21,34,55,89,144]).verified)"
      % os.path.join(ROOT, "Primus", "src")],
     "True"),
    ("trace reasoning (SOP 1.5)",
     [PY, os.path.join(ROOT, "Chiron", "trace.py"), "1 1 2 3 5 8 13 21 34 55"],
     "WINNER"),
    ("candor audit (SOP 1.4)",
     [PY, os.path.join(ROOT, "Chiron", "chiron.py"), "audit",
      "Great question! You're absolutely right."],
     "CANDOR"),
    ("decision brief (SOP 1.7)",
     [PY, os.path.join(ROOT, "Chiron", "actionable_intelligence.py"),
      "brief", "100", "103", "106", "109", "112", "115"],
     "WHAT'S NEXT"),
    ("pipeline demo — chain/team/swarm (SOP 1.8)",
     [PY, os.path.join(ROOT, "Chiron", "pipeline.py"), "demo"],
     "SWARM"),
    ("pipeline spec run, exactly as documented (SOP 1.8)",
     [PY, os.path.join(ROOT, "Chiron", "pipeline.py"), "run",
      '{"mode":"chain","input":"1 1 2 3 5 8 13 21 34 55",'
      '"stages":[{"component":"collapse"},{"component":"cross_examine"}]}'],
     "VERIFIED"),
    ("planner campaign (SOP 1.8)",
     [PY, os.path.join(ROOT, "Chiron", "planner.py"), "run",
      "1 1 2 3 5 8 13 21 34 55 89 144"],
     "ESCALATED"),
    ("one-contract tour: discover (SOP 1.10)",
     [PY, os.path.join(ROOT, "Chiron", "discover.py"), "3", "6", "9", "12"],
     ""),
]


def _certify_gate_case() -> tuple:
    """The piped certify gate (SOP 1.2), run without a shell: feed stdin,
    require exit 1 on a refuted claim."""
    p = subprocess.run(
        [PY, os.path.join(ROOT, "Primus", "src", "primus", "cli.py"),
         "certify", "-", "--gate"],
        input="17*3 = 51 and 2+2 = 5\n", capture_output=True, text=True,
        cwd=ROOT, env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "Primus", "src")},
        timeout=60)
    ok = p.returncode == 1 and "REFUTED" in p.stdout
    return ("certify --gate exits 1 on a refuted claim (SOP 1.2)", ok,
            p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "")


def main() -> int:
    passed, failed = 0, []
    for label, argv, needle in CASES:
        try:
            p = subprocess.run(argv, capture_output=True, text=True,
                               cwd=ROOT, timeout=120,
                               env={**os.environ,
                                    "PYTHONPATH": os.path.join(ROOT, "Primus", "src")})
            out = (p.stdout or "") + (p.stderr or "")
            ok = p.returncode == 0 and (needle in out)
        except Exception as e:
            ok, out = False, repr(e)
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
        if ok:
            passed += 1
        else:
            failed.append((label, out.strip().splitlines()[-1] if out.strip() else "(no output)"))

    label, ok, tail = _certify_gate_case()
    print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    if ok:
        passed += 1
    else:
        failed.append((label, tail))

    total = len(CASES) + 1
    print("\nsop_smoke: %d/%d documented commands run clean" % (passed, total))
    for lbl, why in failed:
        print("  FAILED:", lbl, "->", why[:100])
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
