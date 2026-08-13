#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
test_certify_property.py — the certify kernel's core invariant, checked
EXHAUSTIVELY over a bounded domain rather than by hand-picked examples.

The one property the certificate must never break:

    certify() never stamps VERIFIED on a false checkable claim,
    and never stamps REFUTED on a true one.

Example-based tests show the property holds *here*. This shows it holds across a
whole grid at once — every arithmetic claim `a ∘ b = c` for `a, b` in a range and
`∘ ∈ {+, −, ×}`, in both its true form and a wrong form. It is not a proof
assistant, but it is the honest intermediate: an exhaustive check over a bounded
space is far stronger than a handful of cases, and it is the step this project
takes toward the machine-checked certify kernel named in HORIZON.md.

    python3 test_certify_property.py           # run the sweep, print the tally
    python3 test_certify_property.py --wide    # a larger grid (slower)

Exit code is non-zero if the invariant is violated even once.
"""
import sys

try:
    from primus import certify
except Exception:  # allow running from a source checkout without install
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
    from primus import certify

OPS = [("+", lambda a, b: a + b), ("-", lambda a, b: a - b), ("*", lambda a, b: a * b)]


def _status(text, needle):
    """The status certify assigns to the claim whose text matches `needle`
    (whitespace-insensitive), or None if it extracted no such claim."""
    c = certify(text)
    for cl in c.get("claims", []):
        if needle.replace(" ", "") in cl.get("text", "").replace(" ", ""):
            return cl.get("status")
    return None


def sweep(lo, hi):
    """Every a∘b=c over [lo,hi]², in true and wrong forms. Returns the tally and
    the first few violations (there must be none)."""
    total = extracted = 0
    false_verify = []     # a false claim stamped VERIFIED — the cardinal sin
    true_refute = []      # a true claim stamped REFUTED — soundness the other way
    for sym, fn in OPS:
        for a in range(lo, hi + 1):
            for b in range(lo, hi + 1):
                truth = fn(a, b)
                # 1 · the TRUE claim must never be REFUTED
                expr = f"{a}{sym}{b}={truth}"
                total += 1
                st = _status(expr, expr)
                if st is not None:
                    extracted += 1
                    if st == "REFUTED":
                        true_refute.append(expr)
                # 2 · a WRONG claim (off by one) must never be VERIFIED
                wrong = f"{a}{sym}{b}={truth + 1}"
                total += 1
                st2 = _status(wrong, wrong)
                if st2 is not None:
                    extracted += 1
                    if st2 == "VERIFIED":
                        false_verify.append(wrong)
    return total, extracted, false_verify, true_refute


def chain_sweep(lo, hi):
    """The same invariant over CHAINED expressions.

    The binary regex matches `a op b = c` and its lookbehind rejects only a
    preceding digit, not a preceding operator — so `2 * 3 / 6 = 1` had the
    fragment `3 / 6 = 1` lifted out and stamped REFUTED, on a true statement.
    A false REFUTED is the same class of error as a false VERIFIED: a gate
    that invents errors is worth no more than one that misses them.

    Chains are refused now, so this checks both that no true chain is refuted
    and that no false chain is verified. Prose-embedded and parenthesised
    forms are included because that is where the fragment lifting happened.
    """
    false_verify, true_refute = [], []
    total = 0
    for a in range(lo, hi + 1):
        for b in range(lo, hi + 1):
            for c in range(lo, hi + 1):
                forms = [
                    (f"{a} + {b} * {c} = {a + b * c}", a + b * c),
                    (f"{a} * {b} + {c} = {a * b + c}", a * b + c),
                    (f"{a} * {b} * {c} = {a * b * c}", a * b * c),
                    (f"{a} - {b} + {c} = {a - b + c}", a - b + c),
                    (f"({a} + {b}) * {c} = {(a + b) * c}", (a + b) * c),
                    (f"we get {a} * {b} * {c} = {a * b * c} here", a * b * c),
                ]
                for text, truth in forms:
                    total += 2
                    for cl in certify(text).get("claims", []):
                        if cl.get("status") == "REFUTED":
                            true_refute.append(text)
                    wrong = text.replace(f"= {truth}", f"= {truth + 1}")
                    for cl in certify(wrong).get("claims", []):
                        if cl.get("status") == "VERIFIED":
                            false_verify.append(wrong)
    return total, false_verify, true_refute


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    lo, hi = (-15, 15) if "--wide" in argv else (-10, 10)
    print(f"certify property sweep — grid [{lo},{hi}]², ops {{+,-,*}}, true & wrong forms")
    total, extracted, false_verify, true_refute = sweep(lo, hi)
    print(f"  claims presented : {total}")
    print(f"  claims extracted : {extracted}")
    print(f"  false VERIFIED   : {len(false_verify)}   (must be 0 — the cardinal invariant)")
    print(f"  true  REFUTED    : {len(true_refute)}   (must be 0 — soundness the other way)")
    ok = not false_verify and not true_refute and extracted > 0
    if false_verify:
        print("  FIRST FALSE STAMPS:", false_verify[:5])
    if true_refute:
        print("  FIRST TRUE REFUTES:", true_refute[:5])

    clo, chi = (-4, 4) if "--wide" in argv else (-3, 3)
    print(f"\nchained-expression sweep — grid [{clo},{chi}]³, 6 forms, true & wrong")
    ctotal, cfalse, ctrue = chain_sweep(clo, chi)
    print(f"  claims presented : {ctotal}")
    print(f"  false VERIFIED   : {len(cfalse)}   (must be 0)")
    print(f"  true  REFUTED    : {len(ctrue)}   (must be 0 — the fragment bug)")
    if cfalse:
        print("  FIRST FALSE STAMPS:", cfalse[:5])
    if ctrue:
        print("  FIRST TRUE REFUTES:", ctrue[:5])
    ok = ok and not cfalse and not ctrue

    print("\n  RESULT:", "PASS — invariant held across both grids" if ok
          else "FAIL — the invariant was violated")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
