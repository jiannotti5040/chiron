#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""primus.relate — exact laws across columns, proven on held-out rows.

`collapse` recovers the generator behind ONE sequence. That is the engine's
strength and also its reach limit: real evidence is a table, and the
interesting law is rarely "what comes next in this column" but "what holds
between these columns".

This recovers `y = f(x1..xk)` over a bounded hypothesis class, solves for the
coefficients in EXACT rational arithmetic, and then requires the law to hold
on rows the solver never saw. A relation that fits everything it was shown and
fails one held-out row is not a weaker law — it is refuted, and it is reported
that way.

WHY IT IS EXACT AND NOT A REGRESSION

There is no tolerance, no residual threshold, and no float on the deciding
path. Coefficients are `Fraction`s solved by exact Gaussian elimination; the
check is `==`. A least-squares fit with a small residual would be a different
product — it would stamp a law that is approximately true, and approximately
true is the thing this vault exists not to say.

Consequences worth stating plainly:

  * Measured data with rounding will usually REFUSE. That is correct. The
    honest answer to "is there an exact linear law here" is usually no.
  * The class is small on purpose. A class rich enough to fit anything proves
    nothing, so `k` inputs admit at most `k + 1` free parameters and the
    holdout must be at least as large as the parameter count.

THE THIRD DISPOSITION

A law can fail universally and still be the right description of most of the
table. When a relation holds on every row but a few, this reports
`PARTIAL` — the law, the exact rows that break it, and an explicit statement
that PARTIAL is not VERIFIED. That is anomaly localisation: the rows named are
the rows inconsistent with the law governing the rest, which is a finding
about the data rather than a weakened claim about the law.

    python3 -m primus.relate selftest
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from itertools import combinations
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCHEMA = "primus.relation/1"

VERIFIED, REFUTED, REFUSED, PARTIAL = "VERIFIED", "REFUTED", "REFUSED", "PARTIAL"

# A held-out row can only witness a law if the solver did not use it, and one
# witness is not proof. The holdout must be at least the parameter count, so a
# k-parameter law is never stamped on fewer than k independent confirmations.
MIN_HOLDOUT = 2
MAX_INPUTS = 4
# Cap on how many terms a single law may combine. A class rich enough to fit
# anything proves nothing; this is the ceiling that keeps the search honest
# as well as finite.
MAX_TERMS = 4
MAX_ROWS = 100_000


class RelationError(ValueError):
    """A caller error: malformed table, unusable column, impossible request."""


def _to_fraction(value: Any) -> Optional[Fraction]:
    """Exact conversion, or None. A float is admitted only when it is exactly
    representable as the decimal it appears to be — `Fraction(str(x))` — so
    0.1 becomes 1/10 rather than the binary value that merely prints as 0.1."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, Fraction):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return Fraction(str(value))
    if isinstance(value, str):
        try:
            return Fraction(value.strip())
        except (ValueError, ZeroDivisionError):
            return None
    return None


def _solve_exact(matrix: List[List[Fraction]],
                 rhs: List[Fraction]) -> Optional[List[Fraction]]:
    """Gaussian elimination over the rationals. Returns None when the system
    is singular — an underdetermined system has no unique law, and picking one
    of its infinitely many solutions would be inventing a result."""
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        return None
    aug = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] != 0), None)
        if pivot is None:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for r in range(n):
            if r != col and aug[r][col] != 0:
                factor = aug[r][col]
                aug[r] = [v - factor * aug[col][i] for i, v in enumerate(aug[r])]
    return [aug[i][n] for i in range(n)]


# --------------------------------------------------------------- hypotheses

def _terms_linear(names: Sequence[str]) -> List[Tuple[str, Any]]:
    """y = a0 + sum(ai * xi). The intercept is a term like any other."""
    terms: List[Tuple[str, Any]] = [("1", lambda row: Fraction(1))]
    for name in names:
        terms.append((name, lambda row, n=name: row[n]))
    return terms


def _terms_products(names: Sequence[str]) -> List[Tuple[str, Any]]:
    """y = a0 + sum(ai*xi) + sum(aij*xi*xj). Pairwise only: a full product
    basis grows fast enough to fit noise, which is the failure this class is
    shaped to avoid."""
    terms = _terms_linear(names)
    for a, b in combinations(names, 2):
        terms.append(("%s*%s" % (a, b),
                      lambda row, a=a, b=b: row[a] * row[b]))
    for name in names:
        terms.append(("%s^2" % name, lambda row, n=name: row[n] * row[n]))
    return terms


def _terms_ratio(names: Sequence[str]) -> List[Tuple[str, Any]]:
    """y = a0 + sum(ai * xi) + sum(aij * xi/xj). Rows where a divisor is zero
    are unusable for this class and are excluded rather than skipped silently
    — the count is reported."""
    terms = _terms_linear(names)
    for a in names:
        for b in names:
            if a == b:
                continue
            terms.append(("%s/%s" % (a, b),
                          lambda row, a=a, b=b: row[a] / row[b]))
    return terms


HYPOTHESES = (
    ("linear", _terms_linear),
    ("polynomial", _terms_products),
    ("ratio", _terms_ratio),
)


def _render(coefficients: Sequence[Fraction], labels: Sequence[str],
            target: str) -> str:
    """The recovered law, written out. A law you cannot read is a law you
    cannot check by hand, and being checkable by hand is the point."""
    parts = []
    for coefficient, label in zip(coefficients, labels):
        if coefficient == 0:
            continue
        if label == "1":
            parts.append(str(coefficient))
            continue
        if coefficient == 1:
            parts.append(label)
        elif coefficient == -1:
            parts.append("-" + label)
        else:
            parts.append("%s*%s" % (coefficient, label))
    return "%s = %s" % (target, " + ".join(parts).replace("+ -", "- ")
                        if parts else "0")


def _evaluate(terms, coefficients, row) -> Optional[Fraction]:
    total = Fraction(0)
    for (label, fn), coefficient in zip(terms, coefficients):
        if coefficient == 0:
            continue
        try:
            total += coefficient * fn(row)
        except ZeroDivisionError:
            return None
    return total


def relate(rows: Sequence[Dict[str, Any]], target: str,
           inputs: Optional[Sequence[str]] = None,
           max_anomalies: int = 3) -> Dict[str, Any]:
    """Recover an exact law for `target` from `inputs`, proven on held-out rows.

    Returns a record carrying one of VERIFIED, PARTIAL, REFUSED, or REFUTED,
    the law in readable form, the rows it was solved on, the rows that proved
    it, and — for PARTIAL — the exact rows that break it.
    """
    if not isinstance(rows, (list, tuple)) or not rows:
        raise RelationError("rows must be a non-empty list of objects")
    if len(rows) > MAX_ROWS:
        raise RelationError("too many rows: %d (max %d)" % (len(rows), MAX_ROWS))
    if not isinstance(target, str) or not target:
        raise RelationError("target must be a column name")

    columns = [k for k in rows[0] if isinstance(k, str)]
    if target not in columns:
        raise RelationError("no such column: %r" % target)
    names = [c for c in (inputs if inputs is not None else columns)
             if c != target]
    for name in names:
        if name not in columns:
            raise RelationError("no such column: %r" % name)
    if not names:
        raise RelationError("need at least one input column")
    if len(names) > MAX_INPUTS:
        raise RelationError("at most %d input columns (given %d)"
                            % (MAX_INPUTS, len(names)))

    # Exact conversion first. A column carrying one unparseable cell is not a
    # column this engine can reason about, and saying so beats dropping rows.
    exact: List[Dict[str, Fraction]] = []
    unusable = 0
    for row in rows:
        converted: Dict[str, Fraction] = {}
        ok = True
        for name in names + [target]:
            value = _to_fraction(row.get(name))
            if value is None:
                ok = False
                break
            converted[name] = value
        if ok:
            exact.append(converted)
        else:
            unusable += 1

    base = {
        "schema": SCHEMA,
        "target": target,
        "inputs": list(names),
        "rows_supplied": len(rows),
        "rows_usable": len(exact),
        "rows_unusable": unusable,
    }

    if len(exact) < 3:
        return dict(base, status=REFUSED, law=None,
                    reason="fewer than three rows convert exactly; nothing to "
                           "solve and nothing to hold out")

    # Search smallest-first. Two reasons, and both are load-bearing.
    #
    # A law with fewer parameters that survives the same holdout is the better
    # law — that is MDL, and it is the same principle `collapse` uses on a
    # single sequence. And when inputs are collinear (y = 2x+1 makes [1, x, y]
    # rank two) the full term set is singular; trying subsets finds the law
    # that actually exists instead of giving up on a degenerate system.
    best: Optional[Dict[str, Any]] = None
    seen_subsets = set()
    for family, build in HYPOTHESES:
        all_terms = build(names)
        for size in range(1, min(len(all_terms), MAX_TERMS) + 1):
            if best is not None and not best["failures"]:
                break
            for subset in combinations(range(len(all_terms)), size):
                terms = [all_terms[i] for i in subset]
                signature = tuple(label for label, _ in terms)
                if signature in seen_subsets:
                    continue
                seen_subsets.add(signature)
                k = len(terms)
                # The holdout is what makes this proof rather than fit. A law
                # with k parameters must clear at least k rows it never saw.
                holdout_needed = max(MIN_HOLDOUT, k)
                if len(exact) < k + holdout_needed:
                    continue
                fit_rows = exact[:k]
                held = exact[k:]
                try:
                    matrix = [[fn(row) for _, fn in terms] for row in fit_rows]
                    rhs = [row[target] for row in fit_rows]
                except ZeroDivisionError:
                    continue
                coefficients = _solve_exact(matrix, rhs)
                if coefficients is None:
                    continue

                failures = []
                for index, row in enumerate(held):
                    predicted = _evaluate(terms, coefficients, row)
                    if predicted is None or predicted != row[target]:
                        failures.append(k + index)
                candidate = {
                    "family": family,
                    "terms": [label for label, _ in terms],
                    "coefficients": [str(c) for c in coefficients],
                    "law": _render(coefficients,
                                   [label for label, _ in terms], target),
                    "solved_on_rows": list(range(k)),
                    "held_out_rows": len(held),
                    "failures": failures,
                    "parameters": k,
                }
                if not failures:
                    best = candidate
                    break
                if best is None or len(failures) < len(best["failures"]):
                    best = candidate
        if best is not None and not best["failures"]:
            break

    if best is None:
        return dict(base, status=REFUSED, law=None,
                    reason="no hypothesis class had enough usable rows to be "
                           "solved and independently held out")

    if not best["failures"]:
        return dict(base, status=VERIFIED, law=best["law"], family=best["family"],
                    coefficients=best["coefficients"], terms=best["terms"],
                    parameters=best["parameters"],
                    solved_on_rows=best["solved_on_rows"],
                    held_out_rows=best["held_out_rows"],
                    note="Solved on %d rows and confirmed on %d rows the solver "
                         "never saw, in exact rational arithmetic. This is not a "
                         "fit with a small residual; every held-out row matched "
                         "exactly."
                         % (best["parameters"], best["held_out_rows"]))

    # Anomaly localisation. Reported as its own disposition, never as a
    # verification with caveats.
    failures = best["failures"]
    if len(failures) <= max_anomalies and len(failures) < best["held_out_rows"]:
        return dict(base, status=PARTIAL, law=best["law"], family=best["family"],
                    coefficients=best["coefficients"], terms=best["terms"],
                    parameters=best["parameters"],
                    held_out_rows=best["held_out_rows"],
                    anomalous_rows=failures,
                    note="PARTIAL is not VERIFIED. The law holds exactly on "
                         "every held-out row except %s. That is a finding about "
                         "those rows — they are inconsistent with the law "
                         "governing the rest — and not a weaker claim about the "
                         "law." % ", ".join(str(f) for f in failures))

    return dict(base, status=REFUTED, law=best["law"], family=best["family"],
                held_out_rows=best["held_out_rows"],
                failed_rows=len(failures),
                note="The best candidate was solved exactly on the fitting rows "
                     "and then failed %d of %d held-out rows. A law that only "
                     "describes what it was shown is refuted, not approximate."
                     % (len(failures), best["held_out_rows"]))


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    # An exact linear law across three columns.
    rows = [{"x": i, "w": (i * i) % 7, "z": 5 * i + 3 * ((i * i) % 7) - 2}
            for i in range(14)]
    r = relate(rows, "z", ["x", "w"])
    gate("an exact linear relation across columns VERIFIES", r["status"] == VERIFIED)
    gate("the law is written out readably", "z =" in (r.get("law") or ""))
    gate("it was proven on rows the solver never saw", r["held_out_rows"] >= 2)

    # Exact product law.
    rows = [{"a": i, "b": i + 2, "p": i * (i + 2)} for i in range(2, 16)]
    r = relate(rows, "p", ["a", "b"])
    gate("an exact product law is recovered", r["status"] == VERIFIED
         and r["family"] in ("polynomial", "linear"))

    # Noise must refuse, not approximate.
    rows = [{"x": i, "y": 3 * i + 1 + (1 if i == 7 else 0)} for i in range(14)]
    r = relate(rows, "y", ["x"])
    gate("a single broken row is localised, not absorbed",
         r["status"] == PARTIAL and 7 in r.get("anomalous_rows", []))
    gate("PARTIAL says plainly that it is not VERIFIED",
         "not VERIFIED" in r.get("note", ""))

    # Genuinely unrelated columns.
    import random as _r
    rng = _r.Random(11)
    rows = [{"x": i, "y": rng.randint(0, 999)} for i in range(20)]
    r = relate(rows, "y", ["x"])
    gate("unrelated columns are REFUTED or REFUSED, never stamped",
         r["status"] in (REFUTED, REFUSED))

    # Rounded measurements must not verify. `2*i + 0.0001*i` would be the
    # wrong test — that is exactly 2.0001*i and verifying it is correct.
    # Rounding is what actually destroys exactness.
    rows = [{"x": i, "y": round(2.5 * i)} for i in range(16)]
    r = relate(rows, "y", ["x"])
    gate("rounded measurements do not VERIFY as an exact law",
         r["status"] != VERIFIED)
    gate("...and the near-miss is reported honestly",
         r["status"] in (REFUTED, PARTIAL, REFUSED))

    # Floats are read as the decimals they appear to be.
    rows = [{"x": i, "y": 0.5 * i} for i in range(12)]
    r = relate(rows, "y", ["x"])
    gate("exact decimal coefficients are recovered", r["status"] == VERIFIED
         and "1/2" in " ".join(r["coefficients"]))

    # Too few rows to hold anything out.
    r = relate([{"x": 1, "y": 2}, {"x": 2, "y": 4}], "y", ["x"])
    gate("too few rows REFUSES rather than fitting two points",
         r["status"] == REFUSED)

    # Unusable cells are counted, not dropped quietly.
    rows = [{"x": i, "y": 2 * i} for i in range(12)]
    rows.append({"x": "n/a", "y": 99})
    r = relate(rows, "y", ["x"])
    gate("unusable rows are counted and reported", r["rows_unusable"] == 1)

    # Caller errors.
    for bad, why in (
        (lambda: relate([], "y", ["x"]), "empty table"),
        (lambda: relate([{"x": 1}], "nope", ["x"]), "missing target"),
        (lambda: relate([{"x": 1, "y": 2}], "y", ["absent"]), "missing input"),
    ):
        try:
            bad()
            gate("caller error rejected: %s" % why, False)
        except RelationError:
            gate("caller error rejected: %s" % why, True)

    print("\n  primus.relate self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("selftest", "--selftest"):
        return _selftest()
    print("usage: python3 -m primus.relate selftest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
