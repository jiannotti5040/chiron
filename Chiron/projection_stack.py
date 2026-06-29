#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
projection_stack.py — project a finding through the P -> C -> E -> S substrates.

The central HCT claim made operational: emotion, significance, and meaning are not primitive —
they are projections of one invariant through successive substrates (Physical -> Contextual ->
Emotive -> Semantic), and identity is preserved across the chain and recoverable from a boundary.
This bridges cert_engine's EmotiveSubstrateProjectionStack onto a Chiron finding and exposes the
whole apparatus: the forward projection, the per-substrate read-outs, the holographic/isometric
RECOVERY path, the identity-preservation check, and the growing provenance chain.

Public API (consumed elsewhere): project(surface).

    python3 projection_stack.py selftest
    python3 projection_stack.py project 1 1 2 3 5 8 13 21
    python3 projection_stack.py recover 5 10 15 20 25 30 --json

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

SUBSTRATES = ["Physical", "Contextual", "Emotive", "Semantic"]


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _build_stack(vals):
    arr = np.array(vals, float)
    scale = np.max(np.abs(arr)) + 1e-9
    nv = arr / scale
    N = int(min(12, max(4, len(vals))))
    stack = ce.EmotiveSubstrateProjectionStack(N=N, D=4, context_dim=8)
    for i in range(min(N - 1, len(nv) - 1)):
        d = float(nv[i + 1] - nv[i])
        stack.inject_event(i, i + 1, np.array([d, abs(d), d * d, 1.0]))
    return stack, N


def project(surface):
    """Forward-project a finding through P->C->E->S and verify identity is preserved."""
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    stack, N = _build_stack(vals)
    fp = stack.full_pass()
    idp = stack.verify_identity_preservation()
    emotions = [float(e) for e in fp["emotions"]]
    return {
        "law": inv.model_class, "verified": bool(inv.verified), "entities": N,
        "substrates_P_to_S": {
            "emotive_significance": [round(e, 3) for e in emotions],
            "mean_valence": round(float(fp["mean_emotion_valence"]), 4),
            "max_significance": round(float(fp["max_abs_emotion"]), 4),
            "decision_gravity": round(float(fp["gravity_from_curvature"]), 4),
            "sentiment_vector": [round(float(x), 4) for x in fp["sentiment_vector"]],
            "selected_action": int(fp["action"]),
            "field_norm": round(float(fp["field_norm"]), 4),
        },
        "identity_preserved": bool(idp["passes_identity_preservation"]),
        "holographic_relative_error": round(float(idp["holographic_relative_error"]), 4),
        "isometric_inner_product_error": float(idp["isometric_inner_product_error"]),
        "provenance_length": int(fp["provenance_length"]),
    }


def recover(surface, n_evolve=5):
    """Demonstrate the recovery path: encode to boundary, lift back to context, evolve, and
    measure identity loss across the round-trip and across substrate evolution."""
    vals = _nums(surface)
    stack, N = _build_stack(vals)
    boundary = np.asarray(stack.encode_step())
    lifted = np.asarray(stack.lift_step(boundary))
    pre = stack.verify_identity_preservation()
    stack.evolve_step(dt=0.01, n_steps=n_evolve)
    post = stack.verify_identity_preservation()
    return {
        "entities": N,
        "boundary_dim": int(boundary.shape[-1]) if boundary.ndim else len(boundary),
        "lifted_dim": int(lifted.shape[-1]) if lifted.ndim else len(lifted),
        "identity_before_evolution": round(float(pre["holographic_relative_error"]), 4),
        "identity_after_evolution": round(float(post["holographic_relative_error"]), 4),
        "preserved_before": bool(pre["passes_identity_preservation"]),
        "preserved_after": bool(post["passes_identity_preservation"]),
        "isometric_error": float(post["isometric_inner_product_error"]),
    }


def render(p):
    s = p["substrates_P_to_S"]
    L = ["=" * 64, "PROJECTION STACK — P -> C -> E -> S, identity preserved", "=" * 64]
    L.append(f"  law={p['law']}  verified={p['verified']}  entities={p['entities']}")
    L.append(f"  emotive significance: {s['emotive_significance']}")
    L.append(f"  mean valence {s['mean_valence']}   max {s['max_significance']}   gravity {s['decision_gravity']}")
    L.append(f"  sentiment {s['sentiment_vector']}   action {s['selected_action']}   field_norm {s['field_norm']}")
    L.append(f"  IDENTITY PRESERVED {p['identity_preserved']}  (holo err {p['holographic_relative_error']}, iso err {p['isometric_inner_product_error']:.1e})")
    L.append(f"  provenance length {p['provenance_length']}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    fib = project("1 1 2 3 5 8 13 21 34")
    ok("project returns 4-substrate readout", "emotive_significance" in fib["substrates_P_to_S"])
    ok("entities in [4,12]", 4 <= fib["entities"] <= 12)
    ok("emotive significance has one value per entity", len(fib["substrates_P_to_S"]["emotive_significance"]) == fib["entities"])
    ok("identity preservation reported", isinstance(fib["identity_preserved"], bool))
    ok("provenance chain grew", fib["provenance_length"] >= 1)
    ok("decision gravity in [0,1]", 0 <= fib["substrates_P_to_S"]["decision_gravity"] <= 1)

    rec = recover("5 10 15 20 25 30 35")
    ok("recovery reports boundary + lifted dims", rec["boundary_dim"] > 0 and rec["lifted_dim"] > 0)
    ok("isometric error tiny (norm-preserving lift)", rec["isometric_error"] < 1e-6)
    ok("recovery identity errors are finite", rec["identity_before_evolution"] >= 0 and rec["identity_after_evolution"] >= 0)

    arith = project("2 4 6 8 10 12")
    ok("arithmetic projects with verified law", arith["verified"])

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  projection_stack.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34", "5 10 15 20 25 30 35", "41 19 50 83 6 9 68 12"]:
        print(f"\n### {s}")
        print(render(project(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Project a finding through the HCT substrate stack.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    pr = sub.add_parser("project"); pr.add_argument("values", nargs="+")
    rc = sub.add_parser("recover"); rc.add_argument("values", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "recover":
        r = recover(" ".join(args.values))
        print(json.dumps(r, indent=2)); return 0
    if args.cmd == "project":
        p = project(" ".join(args.values))
        print(json.dumps(p, indent=2) if args.json else render(p)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
