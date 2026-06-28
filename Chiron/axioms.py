#!/usr/bin/env python3
"""
axioms.py — the axiomatic layer, executed not asserted (HCT A1-A12 / T1-T8).

Holographic Continuity Theory rests on twelve axioms and eight theorems. cert_engine.py encodes
the load-bearing ones as runnable checks. This exposes them: it does not *claim* the axioms hold
— it *runs* them and reports which pass. It also surfaces the machine-checkable Lean 4 proof
sketches the engine emits for its load-bearing mathematical claims, and can run a single named
axiom or theorem. The axiomatic layer is the foundation under the projection stack, the
operators, the significance geometry, the density emotion, and the holographic recovery.

    python3 axioms.py selftest
    python3 axioms.py run
    python3 axioms.py verify T5
    python3 axioms.py lean

Framing dial — civilian: foundational self-check of the theory the engines rest on. Contractor:
machine-checkable assurance that the substrate invariants hold before use.
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
    rest = name.split("_", 2)
    tag = rest[2] if len(rest) > 2 else name
    parts = tag.split("_", 1)
    code = parts[0].upper()
    words = parts[1].replace("_", " ") if len(parts) > 1 else ""
    return code, words


def _run_bucketed():
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
    a, t, p = _run_bucketed()
    def tally(rows):
        return sum(1 for _, ok in rows if ok), len(rows)
    return {
        "axioms": {"pass": tally(a)[0], "total": tally(a)[1],
                   "detail": [{"id": _label(n)[0], "claim": _label(n)[1], "holds": ok} for n, ok in a]},
        "theorems": {"pass": tally(t)[0], "total": tally(t)[1],
                     "detail": [{"id": _label(n)[0], "claim": _label(n)[1], "holds": ok} for n, ok in t]},
        "primitives": {"pass": tally(p)[0], "total": tally(p)[1]},
        "all_hold": all(ok for _, ok in a + t + p),
    }


def verify_named(code):
    """Run a single axiom/theorem by code, e.g. 'A3' or 'T5'."""
    code = code.upper()
    for name, fn in ce._TEST_REGISTRY:
        c, claim = _label(name)
        if (name.lower().startswith(AXIOM) or name.lower().startswith(THEOREM)) and c == code:
            with contextlib.redirect_stdout(io.StringIO()):
                ok = bool(fn())
            return {"id": code, "claim": claim, "holds": ok, "test": name}
    return {"id": code, "error": "no such axiom/theorem"}


def lean_sketches():
    """The machine-checkable Lean 4 proof sketches the engine emits for load-bearing claims."""
    out = {}
    try:
        out["lyapunov_bound"] = ce.lean4_proof_sketch_lyapunov(1.127)
    except Exception:
        pass
    try:
        out["socpm_rule"] = ce.lean4_proof_sketch_socpm(ce.SoCPMScores(0.8, 0.9, 0.9, 0.3, 0.5)
                                                        if hasattr(ce, "SoCPMScores") else None)
    except Exception:
        pass
    try:
        out["cone_aperture"] = ce.lean4_proof_sketch_cone_aperture(0.5)
    except Exception:
        pass
    return out


def render(s):
    L = ["=" * 62, "AXIOMATIC LAYER — HCT axioms & theorems, executed", "=" * 62]
    L.append(f"  AXIOMS    {s['axioms']['pass']}/{s['axioms']['total']}")
    for d in s["axioms"]["detail"]:
        L.append(f"     [{'✓' if d['holds'] else '✗'}] {d['id']} — {d['claim']}")
    L.append(f"  THEOREMS  {s['theorems']['pass']}/{s['theorems']['total']}")
    for d in s["theorems"]["detail"]:
        L.append(f"     [{'✓' if d['holds'] else '✗'}] {d['id']} — {d['claim']}")
    L.append(f"  PRIMITIVES {s['primitives']['pass']}/{s['primitives']['total']} HCT reference-implementation checks")
    L.append(f"  >> {'ALL FOUNDATIONS HOLD' if s['all_hold'] else 'SOME CHECKS FAILED — inspect above'}")
    L.append("=" * 62)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    s = summary()
    ok("axioms enumerated (>=8)", s["axioms"]["total"] >= 8)
    ok("all axioms hold", s["axioms"]["pass"] == s["axioms"]["total"])
    ok("theorems enumerated (>=5)", s["theorems"]["total"] >= 5)
    ok("all theorems hold", s["theorems"]["pass"] == s["theorems"]["total"])
    ok("primitives enumerated (>=10)", s["primitives"]["total"] >= 10)
    ok("all foundations hold", s["all_hold"])
    ok("verify A3 holds", verify_named("A3").get("holds"))
    ok("verify T5 holds", verify_named("T5").get("holds"))
    ok("unknown axiom reports error", "error" in verify_named("Z9"))
    ok("at least one lean sketch present", len(lean_sketches()) >= 1)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  axioms.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the HCT axiomatic layer.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("run")
    sub.add_parser("selftest")
    sub.add_parser("lean")
    v = sub.add_parser("verify"); v.add_argument("code")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "lean":
        print(json.dumps(lean_sketches(), indent=2)); return 0
    if args.cmd == "verify":
        print(json.dumps(verify_named(args.code), indent=2)); return 0
    s = summary()
    print(json.dumps(s, indent=2) if args.json else render(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
