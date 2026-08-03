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
    print("  RESULT:", "PASS — invariant held across the entire grid" if ok
          else "FAIL — the invariant was violated")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
