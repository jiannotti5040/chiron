#!/usr/bin/env python3
"""
significance.py — where meaning concentrates: curvature as significance (O-1).

HCT Theorem T5: significance is a geometric observable — a bounded function of the
Ollivier-Ricci curvature of the relational manifold, and emotion is its saturated
projection (valence = tanh(alpha * curvature)). High curvature marks ambiguity,
instability, contradiction; low curvature marks coherence and recoverability.

This bridges cert_engine's SignificanceField + SignificanceGeometry onto a Chiron finding:
it builds a relational field from the surface, computes per-entity curvature and emotive
valence, and reports where decision-gravity concentrates — the spots an analyst should look
at first.

    python3 significance.py --demo
    python3 significance.py 1 1 2 3 5 8 13 99 34 55
    python3 significance.py --surface "5 10 15 20 25 30" --json

Framing dial — civilian: salience / where-to-look scoring over structured data. Contractor:
decision-gravity localization across a relational field.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "JDICert"))
import chiron          # noqa: E402
import numpy as np     # noqa: E402
import cert_engine as ce   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def significance(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    arr = np.array(vals, float)
    scale = np.max(np.abs(arr)) + 1e-9
    nv = arr / scale

    N = int(min(10, max(4, len(vals))))
    sf = ce.SignificanceField(N=N, D=4)
    for i in range(min(N - 1, len(nv) - 1)):
        d = float(nv[i + 1] - nv[i])
        sf.apply_event(i, i + 1, np.array([d, abs(d), d * d, 1.0]))
    sg = ce.SignificanceGeometry(sf, alpha=0.5)

    curv = [round(float(sg.scalar_curvature(i)), 4) for i in range(N)]
    valence = [round(float(sg.emotion_valence(i)), 4) for i in range(N)]
    peak = int(np.argmax(np.abs(np.array(curv))))
    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "entities": N,
        "scalar_curvature": curv,
        "significance_valence": valence,
        "peak_significance_index": peak,
        "gravity": round(float(sg.gravity_from_curvature(list(range(N)))), 4),
        "interpretation": "high curvature -> ambiguity / decision-gravity; low -> coherent, recoverable",
    }


def render(s):
    L = ["=" * 60, "SIGNIFICANCE GEOMETRY — curvature is what matters", "=" * 60]
    L.append(f"  law={s['law']}  verified={s['verified']}  entities={s['entities']}")
    L.append(f"  peak significance at index {s['peak_significance_index']}   gravity={s['gravity']}")
    for i, (c, v) in enumerate(zip(s["scalar_curvature"], s["significance_valence"])):
        mark = "  <-- peak" if i == s["peak_significance_index"] else ""
        L.append(f"     [{i}] curvature {c:<8} valence {v:<8}{mark}")
    L.append("=" * 60)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34", "5 10 15 20 25 30 35", "1 1 2 3 5 8 13 99 34 55"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(significance(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Curvature-as-significance over a finding.")
    ap.add_argument("values", nargs="*")
    ap.add_argument("--surface", default=None)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.demo:
        return _demo()
    surface = args.surface or (" ".join(args.values) if args.values else None)
    if not surface:
        return _demo()
    print(json.dumps(significance(surface), indent=2) if args.json else render(significance(surface)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
