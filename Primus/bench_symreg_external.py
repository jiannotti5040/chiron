#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
bench_symreg_external.py — head-to-head vs an established symbolic-regression
baseline (gplearn genetic programming) on the SAME live-OEIS protocol as
oeis_live.py: see 12 terms, predict the next 4 exactly.

The point is not that GP is bad — it is a different tool with a different
contract. The comparison isolates the property Primus actually claims:
**calibrated confidence.** Primus stamps a result only when it exactly
predicts unseen data and refuses otherwise; a regressor always returns its
best fit, with no native notion of "I don't know."

Three systems, per sequence:
  primus       collapse with held-out proof; refuses outside its classes
  gplearn GP   raw regressor — always answers, cannot refuse
  gated GP     primus.conjecture: the SAME regressor behind the exact gate
               (GP trains on 8 of the 12 shown terms; a candidate stamps
               only if it reproduces all 12 exactly, incl. the 4 it never
               saw). The gate's job is to convert GP's wrong answers into
               refusals; `stamped-wrong` is the cell that must stay 0.

Scoring, per sequence:
  exact-4/4        continuation exactly right (after rounding to integers)
  wrong            continuation wrong
  refused          no stamp, no guess (primus and gated GP only)

Budget note: raw GP does one fit per sequence; gated GP does up to
restarts x 2 fits (a constant-free phase, then a with-constants phase), so
it is not a compute-parity comparison — it is a CONTRACT comparison.

Requires: pip install gplearn scikit-learn. Skips gracefully if absent.
Usage:  python3 bench_symreg_external.py [--population 800] [--generations 25]
        python3 bench_symreg_external.py --only A000290 A000578
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


def gated_row(terms, population, generations, seed=0):
    """The same GP, behind the exact gate (primus.conjecture). The stamp
    requires exact reproduction of all 12 shown terms including a 4-term
    search holdout; a stamped expression then predicts the 4 graded terms
    by exact evaluation. Wrong proposals must die at the gate, so the only
    honest outcomes are exact, refused — or stamped-wrong, the failure cell
    this benchmark exists to count."""
    from fractions import Fraction

    from primus.conjecture import conjecture, parse_expression, eval_tree

    shown, held = terms[:SHOW], terms[SHOW:SHOW + GRADE]
    cert = conjecture(shown, seed=seed, population=population,
                      generations=generations, holdout=GRADE, restarts=1,
                      engine_first=False)
    if cert["status"] != "VERIFIED":
        return "refused", None
    expr = cert["expression"][len("a(n) = "):]
    try:
        tree = parse_expression(expr)
        pred = []
        for i in range(SHOW, SHOW + GRADE):
            v = eval_tree(tree, Fraction(i))
            if v.denominator != 1:
                return "stamped-wrong", None
            pred.append(int(v))
    except Exception:
        return "stamped-wrong", None
    return ("exact" if pred == held else "stamped-wrong"), pred


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=800)
    ap.add_argument("--generations", type=int, default=25)
    ap.add_argument("--cache", default=os.path.join(_HERE, "oeis_corpus_cache.json"))
    ap.add_argument("--only", nargs="*", help="restrict to these A-numbers")
    ap.add_argument("--json", action="store_true", help="emit JSON rows")
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
             "gplearn": {"exact": 0, "wrong": 0},
             "gated": {"exact": 0, "stamped-wrong": 0, "refused": 0}}
    rows = []
    if not args.json:
        print(f"{'A-number':10s} {'primus':>14s} {'gplearn':>14s} {'gated GP':>14s}   name")
    for anum, meta in sorted(corpus.items()):
        terms = meta["terms"]
        if len(terms) < SHOW + GRADE:
            continue
        pg, _ = primus_row(terms)
        gg, _ = gplearn_row(terms, args.population, args.generations)
        cg, _ = gated_row(terms, args.population, args.generations)
        tally["primus"][pg] += 1
        tally["gplearn"][gg] += 1
        tally["gated"][cg] += 1
        rows.append({"anum": anum, "primus": pg, "gplearn": gg, "gated": cg})
        if args.json:
            print(json.dumps(rows[-1]))
        else:
            print(f"{anum:10s} {pg:>14s} {gg:>14s} {cg:>14s}   {meta.get('name','')[:40]}")
    if args.json:
        print(json.dumps({"tally": tally}))
        return 0
    print("\nprimus  :", tally["primus"],
          "\ngplearn :", tally["gplearn"],
          "\ngated GP:", tally["gated"])
    print("\nThe cells that matter: gplearn 'wrong' (confident and false — a "
          "regressor cannot refuse) vs gated GP 'stamped-wrong' (must be 0: "
          "the gate's whole job is converting wrong guesses into refusals).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
