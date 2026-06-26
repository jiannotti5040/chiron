#!/usr/bin/env python3
"""
projection_stack.py — project a finding through the P -> C -> E -> S substrates (E-2).

The core HCT claim: emotion, significance, and meaning are not primitive — they are
projections of one invariant through successive substrates (Physical -> Contextual ->
Emotive -> Semantic), and identity is preserved across the chain and recoverable from a
boundary. This bridges cert_engine's EmotiveSubstrateProjectionStack onto a Chiron finding:
it injects the surface's relational structure, runs the full projection pass, reads off the
significance / emotive / sentiment / action layers, and verifies that identity survived the
projection (the holographic recovery check).

    python3 projection_stack.py --demo
    python3 projection_stack.py 1 1 2 3 5 8 13 21
    python3 projection_stack.py --surface "5 10 15 20 25 30" --json

Framing dial — civilian: layered significance read-out + identity-preservation check.
Contractor: multi-substrate salience projection with provenance and recoverability.
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


def project(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    arr = np.array(vals, float)
    scale = np.max(np.abs(arr)) + 1e-9
    nv = arr / scale

    N = int(min(12, max(4, len(vals))))
    stack = ce.EmotiveSubstrateProjectionStack(N=N, D=4, context_dim=8)
    for i in range(min(N - 1, len(nv) - 1)):
        d = float(nv[i + 1] - nv[i])
        stack.inject_event(i, i + 1, np.array([d, abs(d), d * d, 1.0]))

    fp = stack.full_pass()
    idp = stack.verify_identity_preservation()
    return {
        "law": inv.model_class,
        "verified": bool(inv.verified),
        "substrates_P_to_S": {
            "emotive_significance": [round(float(e), 3) for e in fp["emotions"]],
            "mean_valence": round(float(fp["mean_emotion_valence"]), 4),
            "decision_gravity": round(float(fp["gravity_from_curvature"]), 4),
            "sentiment_vector": [round(float(x), 4) for x in fp["sentiment_vector"]],
            "selected_action": int(fp["action"]),
        },
        "identity_preserved": bool(idp["passes_identity_preservation"]),
        "holographic_relative_error": round(float(idp["holographic_relative_error"]), 4),
        "isometric_inner_product_error": float(idp["isometric_inner_product_error"]),
        "provenance_length": int(fp["provenance_length"]),
    }


def render(p):
    s = p["substrates_P_to_S"]
    L = ["=" * 62, "PROJECTION STACK — P -> C -> E -> S, identity preserved", "=" * 62]
    L.append(f"  law={p['law']}  verified={p['verified']}")
    L.append(f"  emotive significance (per entity): {s['emotive_significance']}")
    L.append(f"  mean valence ....... {s['mean_valence']}")
    L.append(f"  decision gravity ... {s['decision_gravity']}   (curvature -> what matters)")
    L.append(f"  sentiment .......... {s['sentiment_vector']}    action={s['selected_action']}")
    L.append(f"  IDENTITY PRESERVED . {p['identity_preserved']}  (holographic rel. error {p['holographic_relative_error']})")
    L.append(f"  provenance length .. {p['provenance_length']}")
    L.append("=" * 62)
    return "\n".join(L)


_DEMO = ["1 1 2 3 5 8 13 21 34", "5 10 15 20 25 30 35", "41 19 50 83 6 9 68 12"]


def _demo():
    for s in _DEMO:
        print(f"\n### {s}")
        print(render(project(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Project a finding through the HCT substrate stack.")
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
    p = project(surface)
    print(json.dumps(p, indent=2) if args.json else render(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
