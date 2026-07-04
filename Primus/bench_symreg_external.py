#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
bench_symreg_external.py — head-to-head vs an established symbolic-regression
baseline (gplearn genetic programming) on the SAME live-OEIS protocol as
oeis_live.py: see 12 terms, predict the next 4 exactly.

The point is not that GP is bad — it is a different tool with a different
contract. The comparison isolates the property Primus actually claims:
**calibrated confidence.** Primus stamps a result only when it exactly
predicts unseen data and refuses otherwise; a regressor always returns its
best fit, with no native notion of "I don't know."

Scoring, per sequence:
  exact-4/4        continuation exactly right (after rounding to integers)
  wrong            continuation wrong
  (Primus only) refused — no stamp, no guess

Requires: pip install gplearn scikit-learn. Skips gracefully if absent.
Usage:  python3 bench_symreg_external.py [--population 800] [--generations 25]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse  # noqa: E402

SHOW, GRADE = 12, 4


def primus_row(terms):
    shown, held = terms[:SHOW], terms[SHOW:SHOW + GRADE]
    try:
        inv = collapse(shown)
    except Exception:
        return "refused", None
    if not inv.verified:
        return "refused", None
    try:
        pred = [int(round(float(x))) for x in inv.predict(SHOW + GRADE)[SHOW:]]
    except Exception:
        return "refused", None
    return ("exact" if pred == held else "wrong"), pred


def _gplearn_sklearn_compat():
    """gplearn 0.4.2 calls BaseEstimator._validate_data, removed in
    scikit-learn 1.6. Restore it as a thin wrapper over the modern
    free function so the baseline runs on current sklearn."""
    from sklearn.base import BaseEstimator
    if hasattr(BaseEstimator, "_validate_data"):
        return
    from sklearn.utils.validation import validate_data as _vd

    def _validate_data(self, X="no_validation", y="no_validation", **kw):
        return _vd(self, X=X, y=y, **kw)

    BaseEstimator._validate_data = _validate_data


def gplearn_row(terms, population, generations, seed=0):
    _gplearn_sklearn_compat()
    from gplearn.genetic import SymbolicRegressor
    shown, held = terms[:SHOW], terms[SHOW:SHOW + GRADE]
    X = np.arange(SHOW, dtype=float).reshape(-1, 1)
    y = np.array(shown, dtype=float)
    est = SymbolicRegressor(
        population_size=population, generations=generations,
        function_set=("add", "sub", "mul", "div"),
        parsimony_coefficient=0.001, random_state=seed, verbose=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        est.fit(X, y)
        Xt = np.arange(SHOW, SHOW + GRADE, dtype=float).reshape(-1, 1)
        pred_f = est.predict(Xt)
    pred = [int(round(float(v))) if np.isfinite(v) and abs(v) < 2.0**53 else None
            for v in pred_f]
    return ("exact" if pred == held else "wrong"), pred


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=800)
    ap.add_argument("--generations", type=int, default=25)
    ap.add_argument("--cache", default=os.path.join(_HERE, "oeis_corpus_cache.json"))
    ap.add_argument("--only", nargs="*", help="restrict to these A-numbers")
    args = ap.parse_args(argv)

    try:
        import gplearn  # noqa: F401
    except ImportError:
        print("gplearn not installed (pip install gplearn scikit-learn) — skipping.")
        return 0

    with open(args.cache) as f:
        corpus = json.load(f)["sequences"]
    if args.only:
        corpus = {k: v for k, v in corpus.items() if k in set(args.only)}

    tally = {"primus": {"exact": 0, "wrong": 0, "refused": 0},
             "gplearn": {"exact": 0, "wrong": 0}}
    print(f"{'A-number':10s} {'primus':>18s} {'gplearn':>18s}   name")
    for anum, meta in sorted(corpus.items()):
        terms = meta["terms"]
        if len(terms) < SHOW + GRADE:
            continue
        pg, _ = primus_row(terms)
        gg, _ = gplearn_row(terms, args.population, args.generations)
        tally["primus"][pg] += 1
        tally["gplearn"][gg] += 1
        print(f"{anum:10s} {pg:>18s} {gg:>18s}   {meta.get('name','')[:40]}")
    print("\nprimus :", tally["primus"],
          "\ngplearn:", tally["gplearn"])
    print("\nThe cell that matters: 'wrong' — confident continuations that are "
          "false. Primus converts would-be wrongs into refusals; a regressor "
          "cannot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
