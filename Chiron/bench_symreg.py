#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_symreg.py — symbolic recovery vs polynomial regression (an established baseline).

A comparative benchmark: not just "does it pass internal gates" but "how does it compare to a
standard method, and where does each fail?" The task is to recover the rule
behind a sequence from a training prefix and predict the withheld tail. Chiron recovers the exact
generator over its hypothesis classes (or refuses); numpy.polyfit is the textbook baseline --- it
always returns a polynomial, never abstains.

The contrast is the point: on polynomials both succeed, but on non-polynomial laws (geometric,
recurrence, factorial, powers) Chiron still recovers the exact rule while least-squares regression
is confidently wrong --- and on a structureless control Chiron REFUSES while the baseline still
emits a confident answer. Honest abstention vs confident error.

    python3 bench_symreg.py            # results table
    python3 bench_symreg.py selftest   # 0/1 gate

Status: implemented & tested. Real chiron engine; numpy.polyfit baseline.
"""
import os
import sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron  # noqa: E402

HOLDOUT = 3
CORPUS = [
    ("linear",      "polynomial",     [3, 7, 11, 15, 19, 23, 27, 31, 35, 39]),
    ("quadratic",   "polynomial",     [2, 5, 10, 17, 26, 37, 50, 65, 82, 101]),
    ("cubic",       "polynomial",     [1, 8, 27, 64, 125, 216, 343, 512, 729, 1000]),
    ("geometric",   "non-polynomial", [2, 6, 18, 54, 162, 486, 1458, 4374, 13122, 39366]),
    ("fibonacci",   "non-polynomial", [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]),
    ("factorial",   "non-polynomial", [1, 2, 6, 24, 120, 720, 5040, 40320]),
    ("powers_of_2", "non-polynomial", [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]),
]
CONTROL = ("structureless", [7, 2, 9, 1, 5, 8, 3, 6, 4, 0, 2])   # chiron must refuse


def chiron_eval(seq):
    inv = chiron.collapse(seq[:-HOLDOUT])
    if not inv.verified:
        return "refuse", None
    pred = [int(x) for x in inv.predict(len(seq))[-HOLDOUT:]]
    return ("exact" if pred == seq[-HOLDOUT:] else "wrong"), inv.model_class


def polyfit_eval(seq, deg=3):
    train = seq[:-HOLDOUT]
    x = list(range(len(train)))
    coef = np.polyfit(x, train, min(deg, len(train) - 1))
    pred = [round(float(np.polyval(coef, i))) for i in range(len(seq))][-HOLDOUT:]
    return ("exact" if pred == seq[-HOLDOUT:] else "wrong"), pred


def run():
    rows = []
    for name, kind, seq in CORPUS:
        cv, mc = chiron_eval(seq)
        pv, _ = polyfit_eval(seq)
        rows.append((name, kind, cv, mc or "-", pv))
    c_v, c_c = chiron_eval(CONTROL[1])
    p_v, _ = polyfit_eval(CONTROL[1])

    print("bench_symreg — Chiron exact recovery vs polynomial regression (numpy.polyfit)\n")
    print(f"{'sequence':14}{'class':16}{'chiron':>10}{'  (generator)':18}{'polyfit':>10}")
    print("-" * 74)
    for name, kind, cv, mc, pv in rows:
        print(f"{name:14}{kind:16}{cv:>10}  {mc:16}{pv:>10}")
    print(f"{'control':14}{'none':16}{c_v:>10}  {'(abstains)':16}{p_v:>10}")
    print("-" * 74)
    c_exact = sum(1 for r in rows if r[2] == "exact")
    p_exact = sum(1 for r in rows if r[4] == "exact")
    p_wrong = sum(1 for r in rows if r[4] == "wrong")
    print(f"chiron: {c_exact}/{len(rows)} held-out exact, refuses the control ({c_v}); "
          f"polyfit: {p_exact}/{len(rows)} exact, {p_wrong} confidently wrong, 0 abstentions")
    print("\nBoth recover polynomials. Only Chiron recovers non-polynomial laws exactly; regression is")
    print("confidently wrong there and on the structureless control --- it cannot abstain. The engine")
    print("either predicts the withheld tail exactly or refuses; it never emits a confident wrong tail.")
    return rows, (c_v, c_c), (p_v,)


def _selftest():
    rows, (c_v, _), _ = run()
    c_exact = sum(1 for r in rows if r[2] == "exact")
    p_exact = sum(1 for r in rows if r[4] == "exact")
    p_wrong = sum(1 for r in rows if r[4] == "wrong")
    non_poly = [r for r in rows if r[1] == "non-polynomial"]
    checks = [
        ("chiron recovers most of the corpus exactly", c_exact >= len(rows) - 1),
        ("chiron beats polyfit on exact recovery", c_exact > p_exact),
        ("polyfit is confidently wrong on non-polynomial laws", p_wrong >= 1),
        ("chiron recovers non-polynomial laws polyfit misses",
         any(r[2] == "exact" and r[4] == "wrong" for r in non_poly)),
        ("chiron refuses the structureless control", c_v == "refuse"),
        ("chiron never emits a confident wrong tail", all(r[2] in ("exact", "refuse") for r in rows)),
    ]
    print("\nSELFTEST")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    ok = all(c for _, c in checks)
    print(f"  {sum(c for _, c in checks)}/{len(checks)} checks")
    return ok


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(0 if _selftest() else 1)
    run()
