#!/usr/bin/env python3
"""
Ontological primitives (B-6) — the Harmony Functional and V-Units, operationalized.

The Compendium and the five Calculus volumes introduce two primitives that recur
through the applied work: **V-Units** (a unit of value carried by a finding) and the
**Harmony Functional** (the coherence of a set of valued things). The source texts
are philosophy, not code; these are *operationalizations* defined over Chiron's own
measured quantities — clearly an interpretation, not a transcription.

  V-Units:  V(finding) in [0,1] = mean(verified, compression-saturation, 1 - residual)
            — how much proven, durable value a recovered structure carries.
  Harmony:  H(set) in [0,1] = 1 - normalized dispersion of the set's values
            — high when the parts agree / reinforce; low when they conflict.

    python3 ontological.py                       # demo: V of several findings + their harmony
    python3 ontological.py --v "1 1 2 3 5 8 13"  # V-Units of one finding
    python3 ontological.py --json

Framing dial — civilian: value/coherence scoring of evidence. Contractor: mission-
value and concordance scoring across a set of findings.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron  # noqa: E402


def _nums(s):
    parts = str(s).replace(",", " ").split()
    try:
        return [int(x) if float(x).is_integer() else float(x) for x in parts]
    except ValueError:
        return None


def v_units(surface):
    """Value carried by a recovered finding, in [0,1]."""
    nums = _nums(surface)
    inv = chiron.collapse(nums if nums else str(surface))
    d = inv.to_dict()
    verified = 1.0 if d["verified"] else 0.0
    cr = d.get("compression_ratio", 1.0) or 1.0
    compression_sat = max(0.0, 1.0 - 1.0 / cr) if cr > 0 else 0.0
    res = d.get("residual", []) or []
    residual_pen = min(1.0, len(res) / max(1, len(nums or [1]) + len(res)))
    V = round((verified + compression_sat + (1.0 - residual_pen)) / 3.0, 4)
    return {"surface": str(surface)[:40], "model_class": d["model_class"],
            "verified": d["verified"], "V_units": V}


def harmony(values):
    """Coherence of a set of scalar values in [0,1]: 1 - normalized dispersion."""
    xs = [float(v) for v in values]
    if len(xs) < 2:
        return 1.0
    mean = sum(xs) / len(xs)
    var = sum((x - mean) ** 2 for x in xs) / len(xs)
    sd = var ** 0.5
    denom = abs(mean) + 1e-9
    return round(max(0.0, 1.0 - sd / denom), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v", default=None, help="V-Units of one surface")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.v:
        out = v_units(args.v)
        print(json.dumps(out, indent=2) if args.json else
              "V-Units=%s  (%s, verified=%s)" % (out["V_units"], out["model_class"], out["verified"]))
        return 0
    findings = ["1 1 2 3 5 8 13 21", "2 4 8 16 32 64", "0 1 4 9 16 25 36", "2 3 5 7 11 13"]
    vs = [v_units(s) for s in findings]
    H = harmony([x["V_units"] for x in vs])
    if args.json:
        print(json.dumps({"findings": vs, "harmony": H}, indent=2)); return 0
    print("=" * 58)
    print("ONTOLOGICAL PRIMITIVES — V-Units + Harmony Functional")
    print("=" * 58)
    for x in vs:
        print("  V=%-6s  %-22s %s" % (x["V_units"], x["surface"], x["model_class"]))
    print("  ----------------------------------------------")
    print("  Harmony of the set ... %s  (1 = fully concordant)" % H)
    print("\n  Operationalization of the Compendium primitives over Chiron's measured")
    print("  quantities — an interpretation, not a transcription of the source texts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
