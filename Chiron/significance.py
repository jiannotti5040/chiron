#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
significance.py — where meaning concentrates: curvature as significance.

HCT Theorem T5: significance is a geometric observable — a bounded function of the Ollivier-
Ricci curvature of the relational manifold, and emotion is its saturated projection
(valence = tanh(alpha * curvature)). High curvature marks ambiguity, instability, contradiction;
low curvature marks coherence and recoverability. This bridges cert_engine's SignificanceField +
SignificanceGeometry onto a Chiron finding, exposes per-entity curvature and valence, locates
the decision-gravity peak, and runs curvature-driven flow to show significance concentrating.

Public API (consumed elsewhere): significance(surface).

    python3 significance.py selftest
    python3 significance.py map 1 1 2 3 5 8 13 99 34 55
    python3 significance.py flow 5 10 15 20 25 30 --json

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


def _field(vals, N):
    arr = np.array(vals, float)
    nv = arr / (np.max(np.abs(arr)) + 1e-9)
    sf = ce.SignificanceField(N=N, D=4)
    for i in range(min(N - 1, len(nv) - 1)):
        d = float(nv[i + 1] - nv[i])
        sf.apply_event(i, i + 1, np.array([d, abs(d), d * d, 1.0]))
    return sf


def significance(surface, alpha=0.5):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    N = int(min(10, max(4, len(vals))))
    sg = ce.SignificanceGeometry(_field(vals, N), alpha=alpha)
    curv = [round(float(sg.scalar_curvature(i)), 4) for i in range(N)]
    valence = [round(float(sg.emotion_valence(i)), 4) for i in range(N)]
    peak = int(np.argmax(np.abs(np.array(curv))))
    return {
        "law": inv.model_class, "verified": bool(inv.verified), "entities": N, "alpha": alpha,
        "scalar_curvature": curv,
        "significance_valence": valence,
        "peak_significance_index": peak,
        "peak_curvature": curv[peak],
        "mean_curvature": round(float(np.mean(curv)), 4),
        "curvature_dispersion": round(float(np.std(curv)), 4),
        "gravity": round(float(sg.gravity_from_curvature(list(range(N)))), 4),
        "interpretation": "high curvature -> ambiguity / decision-gravity; low -> coherent, recoverable",
    }


def flow(surface, steps=3, alpha=0.5):
    """Curvature-driven flow: where does significance concentrate as the field relaxes?"""
    vals = _nums(surface)
    N = int(min(10, max(4, len(vals))))
    sf = _field(vals, N)
    trail = []
    for k in range(steps + 1):
        sg = ce.SignificanceGeometry(sf, alpha=alpha)
        curv = [float(sg.scalar_curvature(i)) for i in range(N)]
        peak = int(np.argmax(np.abs(np.array(curv))))
        trail.append({"step": k, "peak_index": peak, "peak_curvature": round(curv[peak], 4),
                      "total_curvature": round(float(np.sum(np.abs(curv))), 4)})
        if k < steps:
            try:
                lap = sf.laplacian()
                vec = sf.to_vector() + 0.05 * np.asarray(lap).reshape(sf.to_vector().shape)
                sf = ce.SignificanceField.from_vector(N, 4, vec)
            except Exception:
                break
    return {"entities": N, "flow": trail}


def render(s):
    L = ["=" * 60, "SIGNIFICANCE GEOMETRY — curvature is what matters", "=" * 60]
    L.append(f"  law={s['law']}  verified={s['verified']}  entities={s['entities']}")
    L.append(f"  peak at index {s['peak_significance_index']} (curv {s['peak_curvature']})  gravity {s['gravity']}")
    L.append(f"  mean curvature {s['mean_curvature']}  dispersion {s['curvature_dispersion']}")
    for i, (c, v) in enumerate(zip(s["scalar_curvature"], s["significance_valence"])):
        mark = "  <-- peak" if i == s["peak_significance_index"] else ""
        L.append(f"     [{i}] curvature {c:<8} valence {v:<8}{mark}")
    L.append("=" * 60)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    s = significance("1 1 2 3 5 8 13 21 34")
    ok("one curvature per entity", len(s["scalar_curvature"]) == s["entities"])
    ok("valence is tanh-bounded", all(-1 <= v <= 1 for v in s["significance_valence"]))
    ok("peak index valid", 0 <= s["peak_significance_index"] < s["entities"])
    ok("gravity in [0,1]", 0 <= s["gravity"] <= 1)

    # tampered and clean series both yield a finite curvature field
    tamper = significance("1 1 2 3 5 8 13 99 34 55")
    ok("tampered series yields a finite curvature map",
       tamper["curvature_dispersion"] >= 0 and np.isfinite(tamper["curvature_dispersion"]))

    fl = flow("5 10 15 20 25 30", steps=3)
    ok("flow runs multiple steps", len(fl["flow"]) >= 2)
    ok("flow records a peak each step", all("peak_index" in f for f in fl["flow"]))

    ok("alpha changes valence scale",
       significance("2 4 6 8 10 12", alpha=0.1)["significance_valence"]
       != significance("2 4 6 8 10 12", alpha=0.9)["significance_valence"])

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  significance.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34", "1 1 2 3 5 8 13 99 34 55"]:
        print(f"\n### {s}")
        print(render(significance(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Curvature-as-significance over a finding.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    mp = sub.add_parser("map"); mp.add_argument("values", nargs="+")
    fp = sub.add_parser("flow"); fp.add_argument("values", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "flow":
        print(json.dumps(flow(" ".join(args.values)), indent=2)); return 0
    if args.cmd == "map":
        s = significance(" ".join(args.values))
        print(json.dumps(s, indent=2) if args.json else render(s)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
