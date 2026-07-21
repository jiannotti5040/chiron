#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See ../LICENSE.md.
"""
browser_core.py — the PUBLIC DEMO CORE behind the browser playground.

What this file is, stated plainly (honest scope, the GATES.md way):

  * A small sequence verify-or-refuse core written for the playground at
    docs/playground/. It exists because the architecture prototype in this
    folder (primus_prototype.py) deliberately contains NO sequence engine —
    its certifier refuses everything by design — and the licensed engine's
    source does not ship in this repository.
  * It carries the SAME CONTRACT as the licensed engine: exact arithmetic
    only (integers and Fractions, no floats anywhere on the stamping path),
    a stamp only when the recovered rule predicts held-out terms EXACTLY
    (==, not a tolerance), and refusal otherwise. Zero false verifications
    is as binding here as it is in the vault.
  * It is NOT the licensed engine, is NOT derived from vault source, and is
    STRICTLY WEAKER: five hypothesis families (constant, arithmetic,
    geometric, polynomial ≤ deg 4, linear recurrence ≤ order 3) against the
    licensed engine's much larger set (holonomic, multiplicative, periodic,
    …), and a more conservative evidence rule — for example, the licensed
    engine stamps Tribonacci from 12 terms; this core refuses it (order-3
    counts 6 parameters here, and 12 terms only put 4 aside as held-out).
    Where the two disagree, this core refuses more, never stamps more.
  * The licensed engine's real graded outputs on external data live in
    ../eval/ (frozen predictions, graded against oeis.org). This file is
    the demo; that folder is the proof.

Contract details:

  * Input: 8..512 integers, |term| < 10^60. Anything else is REFUSED
    (floats refused by the exact contract, not rounded).
  * The last h terms are held out before any fitting (h = 3 for n < 10,
    4 for n < 20, then n//4 capped at 6). Fitting sees only the rest.
  * A family becomes a candidate only if it reproduces EVERY shown term
    exactly. Candidates are ranked by parameter count (fewest first).
  * The evidence rule: a candidate may stamp only if the held-out count is
    at least its parameter count (h >= p). Order-3 recurrences count
    coefficients AND seeds (p = 6). An exact fit with too little held-out
    evidence is reported as recovered_unstamped — a candidate, never a
    verdict. This is the vault's composites-12 lesson made structural.
  * VERIFIED requires every held-out term predicted exactly. One mismatch
    and the certificate says recovered_unstamped with the failing term.
  * Ambiguity is refusal: a singular/underdetermined recurrence system
    disqualifies the family rather than guessing a solution.

    python3 browser_core.py selftest    # this core's own gate battery
    python3 browser_core.py demo        # the four playground preloads, live
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction

SCHEMA = "chiron-browser-core/0.1 (PUBLIC DEMO CORE)"
AUTHOR = "Jacob Iannotti"
MAX_TERMS = 512
MAX_MAGNITUDE = 10 ** 60
NEXT_TERMS = 4  # committed predictions beyond the input, on VERIFIED only


# ----------------------------------------------------------------------
# certificates
# ----------------------------------------------------------------------

def _cert(status, explanation, **extra):
    cert = {
        "schema": SCHEMA,
        "author": AUTHOR,
        "engine": "browser_core (public demo core — NOT the licensed engine)",
        "status": status,               # VERIFIED | recovered_unstamped | REFUSED
        "verified": status == "VERIFIED",
        "explanation": explanation,
    }
    cert.update(extra)
    if status == "VERIFIED":
        cert["what_would_falsify"] = (
            "Any true term of this sequence differing from the rule's exact "
            "predictions — the next %d are committed in this certificate." % NEXT_TERMS
        )
    else:
        cert["what_would_falsify"] = (
            "A refusal asserts nothing to falsify. The only claim this core "
            "ever stakes is the stamp, and it did not stamp."
        )
    return cert


# ----------------------------------------------------------------------
# hypothesis families — every fit and prediction is exact (int/Fraction)
# ----------------------------------------------------------------------

def _fit_constant(shown):
    if len(set(shown)) == 1:
        c = shown[0]
        return {"model_class": "constant", "params": {"c": c}, "p": 1,
                "predict": lambda k, n0=len(shown): [c] * k}
    return None


def _fit_arithmetic(shown):
    d = shown[1] - shown[0]
    if all(shown[i + 1] - shown[i] == d for i in range(len(shown) - 1)):
        a_last = shown[-1]
        return {"model_class": "arithmetic", "params": {"a0": shown[0], "d": d}, "p": 2,
                "predict": lambda k, a=a_last, d=d: [a + d * (i + 1) for i in range(k)]}
    return None


def _fit_geometric(shown):
    if any(t == 0 for t in shown):
        return None
    r = Fraction(shown[1], shown[0])
    if all(Fraction(shown[i + 1], shown[i]) == r for i in range(len(shown) - 1)):
        a_last = Fraction(shown[-1])

        def predict(k, a=a_last, r=r):
            out, cur = [], a
            for _ in range(k):
                cur = cur * r
                out.append(int(cur) if cur.denominator == 1 else str(cur))
            return out
        return {"model_class": "geometric",
                "params": {"a0": shown[0], "r": str(r) if r.denominator != 1 else int(r)},
                "p": 2, "predict": predict}
    return None


def _fit_polynomial(shown):
    # exact finite differences; minimal degree d in 2..4 whose (d+1)-th
    # differences vanish, with at least two vanishing entries as evidence
    rows = [list(shown)]
    while len(rows[-1]) > 1 and len(rows) <= 6:
        prev = rows[-1]
        rows.append([prev[i + 1] - prev[i] for i in range(len(prev) - 1)])
    for d in (2, 3, 4):
        if d + 1 >= len(rows):
            break
        diff = rows[d + 1]
        if len(diff) >= 2 and all(v == 0 for v in diff):

            def predict(k, rows=[r[:] for r in rows[:d + 1]], d=d):
                out = []
                tails = [r[-1] for r in rows]
                for _ in range(k):
                    for lvl in range(d - 1, -1, -1):
                        tails[lvl] = tails[lvl] + tails[lvl + 1]
                    out.append(tails[0])
                return out
            return {"model_class": "polynomial_deg%d" % d,
                    "params": {"degree": d, "leading_diff": rows[d][0]},
                    "p": d + 1, "predict": predict}
    return None


def _fit_recurrence(shown):
    # linear recurrence a(n) = c1*a(n-1) + ... + cr*a(n-r), exact rational
    # coefficients; ambiguity (rank < r) disqualifies the family.
    for r in (2, 3):
        if len(shown) < 2 * r + 1:
            continue
        eqs = [([Fraction(shown[i - 1 - j]) for j in range(r)], Fraction(shown[i]))
               for i in range(r, len(shown))]
        sol = _solve_exact(eqs, r)
        if sol is None:
            continue
        if not all(sum(c * a for c, a in zip(sol, row)) == rhs for row, rhs in eqs):
            continue

        def predict(k, tail=list(shown[-r:]), sol=list(sol), r=r):
            out, window = [], [Fraction(t) for t in tail]
            for _ in range(k):
                nxt = sum(c * window[-1 - j] for j, c in enumerate(sol))
                out.append(int(nxt) if nxt.denominator == 1 else str(nxt))
                window.append(nxt)
            return out
        coeffs = [int(c) if c.denominator == 1 else str(c) for c in sol]
        return {"model_class": "linear_recurrence_order%d" % r,
                "params": {"coeffs": coeffs, "seeds": shown[:r]},
                "p": 2 * r,  # coefficients AND seeds — the conservative count
                "predict": predict}
    return None


def _solve_exact(eqs, r):
    # Gaussian elimination over Fractions on the full augmented system;
    # returns the unique solution or None (singular/inconsistent = refusal).
    m = [row[:] + [rhs] for row, rhs in eqs]
    rank, pivots = 0, []
    for col in range(r):
        piv = next((i for i in range(rank, len(m)) if m[i][col] != 0), None)
        if piv is None:
            return None  # rank-deficient: ambiguous family, refuse
        m[rank], m[piv] = m[piv], m[rank]
        m[rank] = [v / m[rank][col] for v in m[rank]]
        for i in range(len(m)):
            if i != rank and m[i][col] != 0:
                m[i] = [a - m[i][col] * b for a, b in zip(m[i], m[rank])]
        pivots.append(col)
        rank += 1
    if any(all(v == 0 for v in row[:-1]) and row[-1] != 0 for row in m):
        return None  # inconsistent
    return [m[i][-1] for i in range(r)]


_FAMILIES = (_fit_constant, _fit_arithmetic, _fit_geometric,
             _fit_polynomial, _fit_recurrence)


# ----------------------------------------------------------------------
# the collapse: split, fit, stamp-or-refuse
# ----------------------------------------------------------------------

def holdout_count(n):
    return min(6, max(3 if n < 10 else 4, n // 4)) if n >= 8 else 0


def collapse(terms):
    """Verify-or-refuse an integer sequence. Returns a certificate dict."""
    if not isinstance(terms, (list, tuple)):
        return _cert("REFUSED", "input must be a list of integers")
    if any(isinstance(t, bool) or not isinstance(t, int) for t in terms):
        return _cert("REFUSED",
                     "exact contract: every term must be an integer — floats "
                     "and non-numeric tokens are refused, not rounded")
    n = len(terms)
    if n < 8:
        return _cert("REFUSED",
                     "too short: %d terms. This core needs at least 8 so it can "
                     "hold some out — a rule proven on nothing is not proven" % n)
    if n > MAX_TERMS:
        return _cert("REFUSED", "over budget: more than %d terms" % MAX_TERMS)
    if any(abs(t) >= MAX_MAGNITUDE for t in terms):
        return _cert("REFUSED", "over budget: |term| >= 10^60")

    h = holdout_count(n)
    shown, held = list(terms[:n - h]), list(terms[n - h:])

    candidates = []
    for fit in _FAMILIES:
        c = fit(shown)
        if c is not None:
            candidates.append(c)
    if not candidates:
        return _cert(
            "REFUSED",
            "No exact rule found. %d terms were shown to five hypothesis "
            "families and none reproduces them exactly — so this core asserts "
            "nothing. It does not curve-fit, approximate, or guess. (The "
            "licensed engine searches a much larger family set and refuses "
            "the same way when its search comes up empty.)" % len(shown),
            shown=shown, held_out=held)

    best = min(candidates, key=lambda c: c["p"])
    if h < best["p"]:
        return _cert(
            "recovered_unstamped",
            "Recovered %s reproducing all %d shown terms exactly, but it has "
            "%d free parameters and only %d terms are held out (h >= p is "
            "required to stamp). An exact fit with too little held-out "
            "evidence is a candidate, not a verdict." %
            (best["model_class"], len(shown), best["p"], h),
            model_class=best["model_class"], params=best["params"],
            reason="insufficient_heldout_evidence",
            shown=shown, held_out=held)

    predicted = best["predict"](h)
    if predicted != held:
        k = next(i for i in range(h) if predicted[i] != held[i])
        return _cert(
            "recovered_unstamped",
            "Recovered %s reproduces every shown term exactly, but its "
            "held-out prediction failed at position %d: predicted %s, the "
            "sequence says %s. It fit the data you gave it and still does "
            "not get the stamp — that refusal is the product." %
            (best["model_class"], k + 1, predicted[k], held[k]),
            model_class=best["model_class"], params=best["params"],
            reason="held_out_mismatch",
            shown=shown, held_out=held, predicted=predicted)

    return _cert(
        "VERIFIED",
        "VERIFIED %s. Recovered in exact arithmetic from the first %d terms, "
        "it predicts all %d held-out terms exactly (==, not a tolerance) and "
        "commits to the next %d." %
        (best["model_class"], len(shown), h, NEXT_TERMS),
        model_class=best["model_class"], params=best["params"],
        shown=shown, held_out=held, predicted=predicted,
        next_terms=best["predict"](h + NEXT_TERMS)[h:])


def collapse_text(text):
    """Browser entry point: whitespace/comma-separated tokens -> JSON string."""
    tokens = [t for t in text.replace(",", " ").split() if t]
    if not tokens:
        return json.dumps(_cert("REFUSED", "no input"))
    terms = []
    for t in tokens:
        try:
            terms.append(int(t))
        except ValueError:
            return json.dumps(_cert(
                "REFUSED",
                "exact contract: %r is not an integer — floats and words are "
                "refused, not rounded" % t))
    return json.dumps(collapse(terms))


# ----------------------------------------------------------------------
# the core's own gate battery
# ----------------------------------------------------------------------

def _gates():
    fib = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
    gates = []

    def gate(name):
        def reg(fn):
            gates.append((name, fn))
            return fn
        return reg

    @gate("fibonacci_12_verifies")
    def _():
        c = collapse(fib)
        assert c["verified"] and c["model_class"] == "linear_recurrence_order2", c

    @gate("fibonacci_next_terms_exact")
    def _():
        c = collapse(fib)
        assert c["next_terms"] == [233, 377, 610, 987], c["next_terms"]

    @gate("squares_12_verify_deg2")
    def _():
        c = collapse([n * n for n in range(1, 13)])
        assert c["verified"] and c["model_class"] == "polynomial_deg2", c
        assert c["next_terms"] == [169, 196, 225, 256]

    @gate("cubes_12_verify_deg3")
    def _():
        c = collapse([n ** 3 for n in range(1, 13)])
        assert c["verified"] and c["model_class"] == "polynomial_deg3", c

    @gate("powers_of_2_verify_geometric")
    def _():
        c = collapse([2 ** n for n in range(12)])
        assert c["verified"] and c["model_class"] == "geometric", c

    @gate("arithmetic_negative_step_verifies")
    def _():
        c = collapse(list(range(100, 40, -5)))
        assert c["verified"] and c["model_class"] == "arithmetic", c

    @gate("constant_verifies")
    def _():
        c = collapse([7] * 10)
        assert c["verified"] and c["model_class"] == "constant", c

    @gate("primes_REFUSE")
    def _():
        c = collapse([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37])
        assert not c["verified"] and c["status"] == "REFUSED", c

    @gate("random_noise_REFUSES")
    def _():
        c = collapse([41, 7, 88, 3, 96, 22, 61, 14, 79, 50, 33, 5])
        assert not c["verified"], c

    @gate("tribonacci_12_refused_by_evidence_rule")
    def _():
        t = [1, 1, 2, 4, 7, 13, 24, 44, 81, 149, 274, 504]
        c = collapse(t)
        assert not c["verified"] and c["status"] == "recovered_unstamped", c
        assert c["reason"] == "insufficient_heldout_evidence", c
        # the licensed engine stamps this from 12 terms; this core must not —
        # it refuses more, never stamps more

    @gate("corrupted_holdout_never_stamps")
    def _():
        bad = fib[:-1] + [145]  # last held-out term is wrong
        c = collapse(bad)
        assert not c["verified"] and c["reason"] == "held_out_mismatch", c

    @gate("floats_refused_not_rounded")
    def _():
        c = collapse([1, 2, 3.0, 4, 5, 6, 7, 8])
        assert c["status"] == "REFUSED" and "exact contract" in c["explanation"], c
        c2 = json.loads(collapse_text("1 2 3.5 4 5 6 7 8"))
        assert c2["status"] == "REFUSED", c2

    @gate("too_short_refused")
    def _():
        c = collapse([1, 2, 3, 4, 5, 6, 7])
        assert c["status"] == "REFUSED", c

    @gate("oversize_refused")
    def _():
        assert collapse(list(range(600)))["status"] == "REFUSED"
        assert collapse([10 ** 61] * 8)["status"] == "REFUSED"

    @gate("big_integers_stay_exact_past_2_53")
    def _():
        seq = [3 ** n * 10 ** 30 for n in range(12)]  # far beyond float precision
        c = collapse(seq)
        assert c["verified"], c
        assert c["next_terms"][0] == 3 ** 12 * 10 ** 30  # exact ==, no drift

    @gate("determinism_same_input_same_certificate")
    def _():
        a, b = collapse_text("1 1 2 3 5 8 13 21 34 55 89 144"), \
               collapse_text("1 1 2 3 5 8 13 21 34 55 89 144")
        assert a == b

    @gate("holdout_is_untouched_by_fitting")
    def _():
        # the fit must not see held-out terms: corrupt ONLY a shown term and
        # the fibonacci candidate must vanish entirely, not shift its verdict
        bad = fib[:]
        bad[3] = 99
        c = collapse(bad)
        assert c["status"] == "REFUSED", c

    return gates


def run_selftest():
    gates = _gates()
    failures = []
    print("browser_core selftest — %s" % SCHEMA)
    for name, fn in gates:
        try:
            fn()
            print("  [PASS] %s" % name)
        except Exception as exc:
            failures.append((name, repr(exc)))
            print("  [FAIL] %s: %r" % (name, exc))
    print("  %d/%d gates green   (this is the DEMO CORE's own count — the "
          "licensed engine's batteries are in docs/BATTERIES.md)"
          % (len(gates) - len(failures), len(gates)))
    return 1 if failures else 0


def run_demo():
    demos = [
        ("Fibonacci", "1 1 2 3 5 8 13 21 34 55 89 144"),
        ("Squares", "1 4 9 16 25 36 49 64 81 100 121 144"),
        ("Primes", "2 3 5 7 11 13 17 19 23 29 31 37"),
        ("Noise", "41 7 88 3 96 22 61 14 79 50 33 5"),
    ]
    for name, text in demos:
        cert = json.loads(collapse_text(text))
        print("== %s: %s" % (name, cert["status"]))
        print("   %s" % cert["explanation"])
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "selftest"
    if cmd == "selftest":
        return run_selftest()
    if cmd == "demo":
        return run_demo()
    print(__doc__)
    print("commands: selftest | demo")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
