#!/usr/bin/env python3
"""
axioms.py — the axiomatic layer, executed not asserted (HCT A1-A12 / T1-T8).

Holographic Continuity Theory rests on twelve axioms and eight theorems. cert_engine.py
encodes the load-bearing ones as runnable checks. This exposes them: it does not *claim* the
axioms hold — it *runs* them and reports which pass. That is the honest form of an axiomatic
layer in executable code — the foundation under the projection stack, the operators, the
significance geometry, the density emotion, and the holographic recovery.

    python3 axioms.py            # run the axioms + theorems + primitives
    python3 axioms.py --json

Framing dial — civilian: foundational self-check of the theory the engines rest on.
Contractor: machine-checkable assurance that the substrate invariants hold before use.
"""
import os
import io
import sys
import json
import argparse
import contextlib

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "JDICert"))
import cert_engine as ce   # noqa: E402

AXIOM = "pc_axiom_"
THEOREM = "pc_theorem_"
PRIMITIVE = ("hct_", "density_emotion_lindblad", "holographic_encoder", "holographic_qec",
             "projection_stack_", "provenance_dag", "gravity_from_curvature", "density_significance")


def _label(name):
    # PC_axiom_A1_invariant_exists... -> "A1 — invariant exists..."
    rest = name.split("_", 2)
    tag = rest[2] if len(rest) > 2 else name
    parts = tag.split("_", 1)
    code = parts[0].upper()
    words = parts[1].replace("_", " ") if len(parts) > 1 else ""
    return f"{code} — {words}".strip(" —")


def run():
    axioms, theorems, primitives = [], [], []
    for name, fn in ce._TEST_REGISTRY:
        low = name.lower()
        bucket = (axioms if low.startswith(AXIOM)
                  else theorems if low.startswith(THEOREM)
                  else primitives if any(p in low for p in PRIMITIVE)
                  else None)
        if bucket is not None:
            with contextlib.redirect_stdout(io.StringIO()):
                ok = bool(fn())
            bucket.append((name, ok))
    return axioms, theorems, primitives


def summary():
    a, t, p = run()
    def tally(rows):
        return sum(1 for _, ok in rows if ok), len(rows)
    return {
        "axioms": {"pass": tally(a)[0], "total": tally(a)[1],
                   "detail": [{"id": _label(n), "holds": ok} for n, ok in a]},
        "theorems": {"pass": tally(t)[0], "total": tally(t)[1],
                     "detail": [{"id": _label(n), "holds": ok} for n, ok in t]},
        "primitives": {"pass": tally(p)[0], "total": tally(p)[1]},
        "all_hold": all(ok for _, ok in a + t + p),
    }


def render(s):
    L = ["=" * 62, "AXIOMATIC LAYER — HCT axioms & theorems, executed", "=" * 62]
    L.append(f"  AXIOMS    {s['axioms']['pass']}/{s['axioms']['total']}")
    for d in s["axioms"]["detail"]:
        L.append(f"     [{'✓' if d['holds'] else '✗'}] {d['id']}")
    L.append(f"  THEOREMS  {s['theorems']['pass']}/{s['theorems']['total']}")
    for d in s["theorems"]["detail"]:
        L.append(f"     [{'✓' if d['holds'] else '✗'}] {d['id']}")
    L.append(f"  PRIMITIVES {s['primitives']['pass']}/{s['primitives']['total']} HCT reference-implementation checks")
    L.append(f"  >> {'ALL FOUNDATIONS HOLD' if s['all_hold'] else 'SOME CHECKS FAILED — inspect above'}")
    L.append("=" * 62)
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the HCT axiomatic layer.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    s = summary()
    print(json.dumps(s, indent=2) if args.json else render(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
