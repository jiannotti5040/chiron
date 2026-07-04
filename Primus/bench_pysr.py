#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_pysr.py — the same live-OEIS head-to-head (see 12 terms, predict 4
exactly) against PySR, the strongest widely-used symbolic-regression
baseline. PySR requires Julia and a heavyweight install, so this harness is
shipped ready-to-run and skips gracefully where PySR is absent:

    pip install pysr           # first run downloads Julia deps (minutes)
    python3 bench_pysr.py

Scoring is identical to bench_symreg_external.py. The comparison isolates
calibrated confidence: PySR returns its best equation for every input;
Primus stamps only what it exactly verifies on held-out terms and refuses
the rest. Count the 'wrong' cells.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse  # noqa: E402

SHOW, GRADE = 12, 4


def primus_row(terms):
    shown, held = terms[:SHOW], terms[SHOW:SHOW + GRADE]
    try:
        inv = collapse(shown)
        if not inv.verified:
            return "refused", None
        pred = [int(round(float(x))) for x in inv.predict(SHOW + GRADE)[SHOW:]]
        return ("exact" if pred == held else "wrong"), pred
    except Exception:
        return "refused", None


def pysr_row(terms, niterations):
    from pysr import PySRRegressor
    shown, held = terms[:SHOW], terms[SHOW:SHOW + GRADE]
    X = np.arange(SHOW, dtype=float).reshape(-1, 1)
    y = np.array(shown, dtype=float)
    model = PySRRegressor(niterations=niterations,
                          binary_operators=["+", "-", "*", "/"],
                          unary_operators=[], progress=False,
                          model_selection="best", random_state=0,
                          deterministic=True, procs=0)
    model.fit(X, y)
    Xt = np.arange(SHOW, SHOW + GRADE, dtype=float).reshape(-1, 1)
    pred_f = model.predict(Xt)
    pred = [int(round(float(v))) if np.isfinite(v) and abs(v) < 2.0**53 else None
            for v in pred_f]
    return ("exact" if pred == held else "wrong"), pred


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--niterations", type=int, default=40)
    ap.add_argument("--cache", default=os.path.join(_HERE, "oeis_corpus_cache.json"))
    args = ap.parse_args(argv)
    try:
        import pysr  # noqa: F401
    except ImportError:
        print("PySR not installed (pip install pysr) — skipping. "
              "This harness runs the full head-to-head wherever PySR exists.")
        return 0
    with open(args.cache) as f:
        corpus = json.load(f)["sequences"]
    tally = {"primus": {"exact": 0, "wrong": 0, "refused": 0},
             "pysr": {"exact": 0, "wrong": 0}}
    for anum, meta in sorted(corpus.items()):
        terms = meta["terms"]
        if len(terms) < SHOW + GRADE:
            continue
        pg, _ = primus_row(terms)
        yg, _ = pysr_row(terms, args.niterations)
        tally["primus"][pg] += 1
        tally["pysr"][yg] += 1
        print(f"{anum}  primus={pg:8s}  pysr={yg:8s}  {meta.get('name','')[:40]}")
    print("\nprimus:", tally["primus"], "\npysr  :", tally["pysr"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
