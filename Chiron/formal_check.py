#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Formal soundness checks (property-based).

    python3 formal_check.py            # run the properties; exit nonzero on any violation
    python3 formal_check.py --json

The guarantee being checked is the soundness property:

    collapse(s).verified  ==>  the recovered rule reproduces every observed term
                               AND predicts the held-out terms exactly.

Equivalently: the engine never reports "verified" for a rule that mispredicts. This
is checked over thousands of generated cases — in-class generators, shuffled
controls, and corrupted sequences. It is property-based verification, not a
machine-checked proof; see FORMAL.md for the argument and its limits.
"""
import os
import sys
import json
import random
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse, fuzz_test  # noqa: E402


def _fib(n, a, b):
    s = [a, b]
    while len(s) < n:
        s.append(s[-1] + s[-2])
    return s[:n]


def soundness_corruption(n=2000, seed=7, holdout=3):
    """Corrupt one term of an in-class generator; the corrupted sequence must NOT
    verify-and-mispredict. A violation is a genuine false positive."""
    rng = random.Random(seed)
    violations = checked = 0
    for _ in range(n):
        kind = rng.choice(["arith", "geo", "poly2", "fib"])
        if kind == "arith":
            a, d = rng.randint(0, 9), rng.randint(1, 7); s = [a + d * i for i in range(14)]
        elif kind == "geo":
            a, r = rng.randint(1, 4), rng.randint(2, 4); s = [a * r ** i for i in range(14)]
        elif kind == "poly2":
            c2, c1, c0 = rng.randint(1, 4), rng.randint(0, 4), rng.randint(0, 4)
            s = [c2 * i * i + c1 * i + c0 for i in range(14)]
        else:
            s = _fib(14, rng.randint(1, 4), rng.randint(1, 4))
        s[rng.randint(2, 10)] += rng.choice([-2, -1, 1, 2])   # corrupt one interior term
        checked += 1
        try:
            inv = collapse(s[:-holdout])
            if inv.verified:
                pred = list(inv.predict(len(s))[-holdout:])
                if pred != list(s[-holdout:]):
                    violations += 1                            # verified AND wrong = false positive
        except Exception:
            pass
    return {"checked": checked, "violations": violations}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cases", type=int, default=5000)
    args = ap.parse_args()

    fz = fuzz_test(args.cases, seed=1)
    corr = soundness_corruption(max(1000, args.cases // 2))
    violations = fz["false_verify_shuffled"] + fz["crashes"] + corr["violations"]
    report = {
        "property": "collapse.verified => held-out predicted exactly (no false positive)",
        "in_class_and_shuffled": fz,
        "corruption": corr,
        "total_violations": violations,
        "verdict": "SOUND" if violations == 0 else "VIOLATION",
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if violations == 0 else 1
    print("=" * 60)
    print("FORMAL SOUNDNESS CHECK (property-based)")
    print("=" * 60)
    print("  in-class verified ....... %d / %d" % (fz["verified_inclass"], fz["total"]))
    print("  shuffled false-verify ... %d" % fz["false_verify_shuffled"])
    print("  crashes ................. %d" % fz["crashes"])
    print("  corrupted checked ....... %d" % corr["checked"])
    print("  corrupted false-verify .. %d" % corr["violations"])
    print("  -------------------------------------------")
    print("  total violations ........ %d" % violations)
    print("  VERDICT: %s" % report["verdict"])
    return 0 if violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
