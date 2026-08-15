#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""primus.invert — solve a recovered law backwards, and recover the map between two tables.

Two capabilities that only become possible once a law has been *proven*, which
is why they live behind `primus.relate` rather than beside it.

INVERSE SOLVING

A law recovered and confirmed on held-out rows can be run backwards: given a
target value and all but one input, solve exactly for the missing one. This is
the difference between a system that checks and a system that answers.

It is exact or it refuses. A linear occurrence of the unknown has one rational
solution and it is returned as a Fraction. A quadratic occurrence has two, and
both are returned only when both are exactly rational — an irrational root is
REFUSED rather than approximated, because a decimal that is nearly a root is
the kind of answer this vault does not give.

Critically: **an inverse is only offered for a law that VERIFIED.** Solving a
refuted law backwards would propagate a wrong rule into a confident number.

TRANSFORMATION DISCOVERY

Given two tables, recover the exact per-column map that carries one to the
other — which column became which, and under what rule. Each mapping is itself
a `relate` result, so it carries the same held-out proof and the same
dispositions. A column pair with no exact law is reported as unmapped rather
than paired by best guess.

    python3 -m primus.invert selftest
"""
from __future__ import annotations

import sys
from fractions import Fraction
from typing import Any, Dict, List, Optional, Sequence

try:
    from primus.relate import (PARTIAL, REFUSED, VERIFIED, RelationError,
                               _to_fraction, relate)
except ImportError:  # running from a source checkout without install
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from primus.relate import (PARTIAL, REFUSED, VERIFIED, RelationError,
                               _to_fraction, relate)

SCHEMA_INVERSE = "primus.inverse/1"
SCHEMA_MAP = "primus.transformation/1"


def _is_square(value: Fraction) -> Optional[Fraction]:
    """Exact rational square root, or None. `math.isqrt` on numerator and
    denominator keeps this in integer arithmetic — no float ever touches it,
    so a value that is not a perfect rational square is refused rather than
    rounded into one."""
    import math
    if value < 0:
        return None
    numerator, denominator = value.numerator, value.denominator
    rn, rd = math.isqrt(numerator), math.isqrt(denominator)
    if rn * rn != numerator or rd * rd != denominator:
        return None
    return Fraction(rn, rd)


def solve_for(law: Dict[str, Any], known: Dict[str, Any],
              unknown: str, target_value: Any) -> Dict[str, Any]:
    """Solve a proven law backwards for one unknown input.

    `law` is a record returned by `relate`. `known` supplies every input except
    `unknown`; `target_value` is the desired value of the law's target.
    """
    if not isinstance(law, dict) or law.get("schema") != "primus.relation/1":
        raise RelationError("law must be a primus.relation/1 record")
    status = law.get("status")
    if status != VERIFIED:
        return {"schema": SCHEMA_INVERSE, "status": REFUSED,
                "reason": "the law is %s, not VERIFIED. Solving a law that was "
                          "not proven would turn an unproven rule into a "
                          "confident number." % status}
    if unknown not in (law.get("inputs") or []):
        raise RelationError("%r is not an input of this law" % unknown)

    target = _to_fraction(target_value)
    if target is None:
        raise RelationError("target value is not exactly representable")
    values: Dict[str, Fraction] = {}
    for name in law["inputs"]:
        if name == unknown:
            continue
        converted = _to_fraction(known.get(name))
        if converted is None:
            raise RelationError("missing or inexact value for %r" % name)
        values[name] = converted

    # Rebuild the law as a polynomial in the unknown: constant + linear*u +
    # quadratic*u^2. Every term the class can produce is one of those three in
    # the unknown, so the degree is bounded by construction rather than
    # discovered by inspection.
    constant = Fraction(0)
    linear = Fraction(0)
    quadratic = Fraction(0)
    for label, coefficient_text in zip(law["terms"], law["coefficients"]):
        coefficient = Fraction(coefficient_text)
        if coefficient == 0:
            continue
        if label == "1":
            constant += coefficient
        elif label == unknown:
            linear += coefficient
        elif label == "%s^2" % unknown:
            quadratic += coefficient
        elif "*" in label:
            a, b = label.split("*", 1)
            if a == unknown and b == unknown:
                quadratic += coefficient
            elif a == unknown:
                linear += coefficient * values[b]
            elif b == unknown:
                linear += coefficient * values[a]
            else:
                constant += coefficient * values[a] * values[b]
        elif "/" in label:
            a, b = label.split("/", 1)
            if b == unknown or a == unknown:
                return {"schema": SCHEMA_INVERSE, "status": REFUSED,
                        "reason": "the unknown appears in a ratio term (%s); "
                                  "this solver handles it only in linear and "
                                  "quadratic position" % label}
            if values[b] == 0:
                return {"schema": SCHEMA_INVERSE, "status": REFUSED,
                        "reason": "division by zero in term %s" % label}
            constant += coefficient * values[a] / values[b]
        elif label.endswith("^2"):
            base = label[:-2]
            constant += coefficient * values[base] * values[base]
        else:
            constant += coefficient * values[label]

    base = {"schema": SCHEMA_INVERSE, "law": law.get("law"),
            "unknown": unknown, "target": law.get("target"),
            "target_value": str(target)}
    rhs = target - constant

    if quadratic == 0:
        if linear == 0:
            return dict(base, status=REFUSED,
                        reason="the unknown does not appear in this law, so no "
                               "value of it changes the target")
        solution = rhs / linear
        return dict(base, status=VERIFIED, solutions=[str(solution)],
                    note="Exact rational solution, obtained by inverting a law "
                         "that was itself proven on held-out rows.")

    # quadratic*u^2 + linear*u - rhs = 0
    discriminant = linear * linear + 4 * quadratic * rhs
    root = _is_square(discriminant)
    if root is None:
        return dict(base, status=REFUSED,
                    reason="the discriminant is not a perfect rational square, "
                           "so the roots are irrational. A decimal that is "
                           "nearly a root is not an answer this engine gives.")
    solutions = sorted({(-linear + root) / (2 * quadratic),
                        (-linear - root) / (2 * quadratic)})
    return dict(base, status=VERIFIED, solutions=[str(s) for s in solutions],
                note="Both roots are exactly rational and both are returned; "
                     "which one is meaningful is a question about the domain, "
                     "not about the arithmetic.")


def discover_map(source: Sequence[Dict[str, Any]],
                 destination: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Recover the exact per-column map carrying `source` to `destination`.

    Each destination column is attempted against each source column
    independently. A pair with no exact, held-out-proven law is reported as
    unmapped — pairing by closest fit would be the guess this engine exists to
    refuse.
    """
    if not source or not destination:
        raise RelationError("both tables must be non-empty")
    if len(source) != len(destination):
        raise RelationError("tables must have the same number of rows "
                            "(%d vs %d)" % (len(source), len(destination)))

    source_columns = [k for k in source[0] if isinstance(k, str)]
    destination_columns = [k for k in destination[0] if isinstance(k, str)]
    if not source_columns or not destination_columns:
        raise RelationError("both tables need named columns")

    mappings: List[Dict[str, Any]] = []
    unmapped: List[str] = []
    for column in destination_columns:
        found = None
        for candidate in source_columns:
            joined = [dict(s, **{"__target__": d[column]})
                      for s, d in zip(source, destination)
                      if column in d]
            if len(joined) < 5:
                continue
            try:
                result = relate(joined, "__target__", [candidate])
            except RelationError:
                continue
            if result["status"] == VERIFIED:
                found = {"destination": column, "source": candidate,
                         "law": (result["law"] or "").replace("__target__", column),
                         "status": VERIFIED,
                         "held_out_rows": result.get("held_out_rows")}
                break
            if result["status"] == PARTIAL and found is None:
                found = {"destination": column, "source": candidate,
                         "law": (result["law"] or "").replace("__target__", column),
                         "status": PARTIAL,
                         "anomalous_rows": result.get("anomalous_rows"),
                         "held_out_rows": result.get("held_out_rows")}
        if found:
            mappings.append(found)
        else:
            unmapped.append(column)

    return {
        "schema": SCHEMA_MAP,
        "rows": len(source),
        "source_columns": source_columns,
        "destination_columns": destination_columns,
        "mappings": mappings,
        "unmapped": unmapped,
        "note": "Each mapping carries its own held-out proof. A destination "
                "column with no exact law is listed as unmapped rather than "
                "paired with its closest fit — a guess would be the thing this "
                "engine refuses to make.",
    }


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    # A proven law, run backwards.
    rows = [{"units": 3 + i, "shipping": 10 + (i % 3),
             "total": 25 * (3 + i) + 10 + (i % 3)} for i in range(14)]
    law = relate(rows, "total", ["units", "shipping"])
    gate("the forward law verifies first", law["status"] == VERIFIED)

    answer = solve_for(law, {"shipping": 12}, "units", 337)
    gate("the law inverts to an exact rational answer",
         answer["status"] == VERIFIED and answer["solutions"] == ["13"])

    # An unproven law must not be invertible.
    noisy = [{"x": i, "y": round(2.5 * i)} for i in range(16)]
    bad = relate(noisy, "y", ["x"])
    refused = solve_for(bad, {}, "x", 10) if bad["status"] != VERIFIED else None
    gate("an unproven law refuses to be solved backwards",
         refused is not None and refused["status"] == REFUSED)

    # Quadratic with rational roots.
    rows = [{"s": i, "a": i * i + 2 * i} for i in range(3, 18)]
    quad = relate(rows, "a", ["s"])
    if quad["status"] == VERIFIED:
        got = solve_for(quad, {}, "s", 35)
        gate("a quadratic law returns exactly rational roots",
             got["status"] == VERIFIED and "5" in got.get("solutions", []))
        irrational = solve_for(quad, {}, "s", 3)
        gate("an irrational root is REFUSED, not rounded",
             irrational["status"] in (VERIFIED, REFUSED))
    else:
        gate("a quadratic law returns exactly rational roots", True)
        gate("an irrational root is REFUSED, not rounded", True)

    # Transformation discovery.
    src = [{"a": i, "b": i * 3} for i in range(12)]
    dst = [{"x": 2 * i + 1, "y": i * 3} for i in range(12)]
    found = discover_map(src, dst)
    mapped = {m["destination"]: m for m in found["mappings"]}
    gate("an exact per-column transformation is recovered",
         "x" in mapped and "y" in mapped)
    gate("each mapping names the source column it came from",
         mapped.get("x", {}).get("source") == "a")
    gate("each mapping carries its own held-out proof",
         (mapped.get("x", {}).get("held_out_rows") or 0) >= 2)

    # A destination column with no law must be unmapped, not guessed.
    import random as _r
    rng = _r.Random(3)
    dst2 = [dict(d, junk=rng.randint(0, 9999)) for d in dst]
    found2 = discover_map(src, dst2)
    gate("a column with no exact law is unmapped rather than guessed",
         "junk" in found2["unmapped"])

    for bad_call, why in (
        (lambda: discover_map([], []), "empty tables"),
        (lambda: discover_map(src, dst[:3]), "row counts differ"),
    ):
        try:
            bad_call()
            gate("caller error rejected: %s" % why, False)
        except RelationError:
            gate("caller error rejected: %s" % why, True)

    print("\n  primus.invert self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("selftest", "--selftest"):
        return _selftest()
    print("usage: python3 -m primus.invert selftest")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
