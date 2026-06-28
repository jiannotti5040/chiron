#!/usr/bin/env python3
"""
operator_calculus.py — the six epistemic operators over a Chiron finding.

HCT's Projection Calculus treats reasoning as operators acting on a Mystery Vector — the six
species of the unknown: ignorance, paradox, transcendence, emergence, subjectivity, infinity.
Six operators each reduce one species:

  Measure -> ignorance   Reframe  -> paradox       Invent -> transcendence
  Model   -> emergence    Dialogue -> subjectivity   Explore -> infinity

This is a complete diagnostic over cert_engine's EpistemicOperatorAlgebra. It reads a finding
into a Mystery Vector (from several independent signals), names the dominant unknown,
prescribes the operator that reduces it, runs an iterative REDUCTION TRAJECTORY (progressive
elimination of the unknown — how a discernment engine earns confidence), and reports the full
commutator matrix (which moves are order-dependent). It does not assert the algebra's
properties; it computes them.

    python3 operator_calculus.py selftest
    python3 operator_calculus.py profile 1 1 2 3 5 8 13 21
    python3 operator_calculus.py reduce 41 19 50 83 6 9
    python3 operator_calculus.py commutators

Framing dial — civilian: diagnose what KIND of unknown a finding carries and the move that
reduces it. Contractor: typed-uncertainty triage with a prescribed reduction operator.
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

OPS = ["Measure", "Reframe", "Invent", "Model", "Dialogue", "Explore"]
SPECIES = ["ignorance", "paradox", "transcendence", "emergence", "subjectivity", "infinity"]
TRANSCENDENT = ("incompressible", "general", "random")
COMPLEX = ("holonomic", "interleaved", "linear_recurrence_order2", "linear_recurrence_order3", "periodic")
INTERP = {
    "ignorance": "missing observation — apply Measure (gather more terms / evidence)",
    "paradox": "competing explanations of comparable cost — apply Reframe (re-conceptualise)",
    "transcendence": "beyond the current hypothesis classes — apply Invent (build a new class)",
    "emergence": "structure that only appears at the whole — apply Model (formalise it)",
    "subjectivity": "interpretation-dependent — apply Dialogue (resolve with stakeholders)",
    "infinity": "unbounded continuation — apply Explore (enumerate finite candidates)",
}


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def mystery_vector(inv, vals):
    """Read a collapse into the 6-species Mystery Vector from independent signals."""
    n = max(1, len(vals))
    resid = len(getattr(inv, "residual", []) or [])
    # ignorance = a MEASUREMENT gap. Incompressible-with-enough-data is NOT ignorance
    # (more terms won't recover a law that doesn't exist in the classes) — that is transcendence.
    if inv.verified:
        ig = 0.1
    elif inv.model_class in TRANSCENDENT:
        ig = 0.5 if n < 6 else 0.2
    else:
        ig = float(np.clip(0.4 + resid / n, 0.3, 0.9))

    try:
        cands = [c for c in chiron.top_generators(vals, k=3) if "mdl_cost_bits" in c]
    except Exception:
        cands = []
    # paradox = two comparably-good RIVAL generators. No-law-at-all is not paradox.
    if len(cands) >= 2 and inv.model_class not in TRANSCENDENT:
        gap = float(cands[1]["mdl_cost_bits"]) - float(cands[0]["mdl_cost_bits"])
        par = float(np.clip(1.0 / (1.0 + max(0.0, gap)), 0.0, 1.0))
    else:
        par = 0.05

    tr = 0.75 if inv.model_class in TRANSCENDENT else 0.1
    em = 0.4 if inv.model_class in COMPLEX else 0.15
    su = 0.05
    inf = 0.3 if inv.verified else 0.1
    return np.array([ig, par, tr, em, su, inf], float)


def reduction_trajectory(xi, max_steps=6, tol=0.05):
    """Iteratively apply the dominant-species operator; log the mystery norm shrinking."""
    alg = ce.EpistemicOperatorAlgebra()
    x = np.array(xi, float)
    traj = [{"step": 0, "operator": None, "norm": round(float(np.linalg.norm(x)), 4),
             "dominant": SPECIES[int(np.argmax(x))]}]
    for step in range(1, max_steps + 1):
        dom = int(np.argmax(x))
        if x[dom] < tol:
            break
        x = alg.apply(OPS[dom], x)
        traj.append({"step": step, "operator": OPS[dom],
                     "norm": round(float(np.linalg.norm(x)), 4),
                     "dominant": SPECIES[int(np.argmax(x))]})
    return traj


def commutator_matrix():
    """Full 15-pair commutator norms on a coupled probe vector (computes T4 directly)."""
    alg = ce.EpistemicOperatorAlgebra()
    probe = np.array([0.8, 0.6, 0.4, 0.5, 0.3, 0.2])
    out = {}
    for i in range(len(OPS)):
        for j in range(i + 1, len(OPS)):
            c = float(np.linalg.norm(alg.commutator(OPS[i], OPS[j], probe)))
            out[f"{OPS[i]}|{OPS[j]}"] = round(c, 6)
    nonzero = sum(1 for v in out.values() if v > 1e-9)
    return out, nonzero


def profile(surface):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    xi = mystery_vector(inv, vals)
    dom = int(np.argmax(xi))
    traj = reduction_trajectory(xi)
    _, nonzero = commutator_matrix()
    return {
        "law": inv.model_class, "verified": bool(inv.verified),
        "mystery_vector": {SPECIES[i]: round(float(xi[i]), 3) for i in range(6)},
        "dominant_unknown": SPECIES[dom],
        "recommended_operator": OPS[dom],
        "interpretation": INTERP[SPECIES[dom]],
        "mystery_norm_start": traj[0]["norm"],
        "mystery_norm_end": traj[-1]["norm"],
        "reduction_trajectory": traj,
        "noncommuting_pairs": nonzero,
        "noncommutativity_note": ("the linear algebra commutes on an uncoupled vector; "
                                  "genuine order-dependence (T4) arises once species are coupled "
                                  "and operators surface new unknowns"),
    }


def render(p):
    L = ["=" * 62, "EPISTEMIC OPERATOR CALCULUS — the six moves on a finding", "=" * 62]
    L.append(f"  law={p['law']}  verified={p['verified']}")
    L.append("  mystery vector (species of the unknown):")
    for k, v in p["mystery_vector"].items():
        L.append(f"     {k:<14} {v:<5} {'█' * int(round(v * 20))}")
    L.append(f"  dominant unknown ... {p['dominant_unknown']}")
    L.append(f"  prescription ....... {p['interpretation']}")
    L.append(f"  reduction .......... norm {p['mystery_norm_start']} -> {p['mystery_norm_end']} "
             f"over {len(p['reduction_trajectory']) - 1} steps")
    for t in p["reduction_trajectory"][1:]:
        L.append(f"       step {t['step']}: apply {t['operator']:<9} -> norm {t['norm']} (now dominant: {t['dominant']})")
    L.append(f"  commutator matrix .. {p['noncommuting_pairs']}/15 pairs order-dependent")
    L.append("=" * 62)
    return "\n".join(L)


_SUITE = {
    "fibonacci": "1 1 2 3 5 8 13 21 34",
    "arithmetic": "2 4 6 8 10 12 14",
    "incompressible": "41 19 50 83 6 9 68 12",
}


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    fib = profile(_SUITE["fibonacci"])
    noise = profile(_SUITE["incompressible"])
    ok("verified law -> low ignorance", fib["mystery_vector"]["ignorance"] <= 0.2)
    ok("incompressible -> high transcendence", noise["mystery_vector"]["transcendence"] >= 0.5)
    ok("incompressible dominant is transcendence", noise["dominant_unknown"] == "transcendence")
    ok("incompressible prescribes Invent", noise["recommended_operator"] == "Invent")
    ok("reduction shrinks the norm", fib["mystery_norm_end"] <= fib["mystery_norm_start"])
    ok("trajectory is monotone non-increasing",
       all(fib["reduction_trajectory"][i]["norm"] >= fib["reduction_trajectory"][i + 1]["norm"]
           for i in range(len(fib["reduction_trajectory"]) - 1)))
    mat, nz = commutator_matrix()
    ok("commutator matrix has 15 pairs", len(mat) == 15)
    ok("mystery vector sums into [0,6]", 0 <= sum(fib["mystery_vector"].values()) <= 6)
    ok("recommended op matches dominant species index",
       OPS[SPECIES.index(fib["dominant_unknown"])] == fib["recommended_operator"])

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  operator_calculus.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for label, s in _SUITE.items():
        print(f"\n### {label}: {s}")
        print(render(profile(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mystery-vector + epistemic-operator diagnosis.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    sub.add_parser("commutators")
    pr = sub.add_parser("profile"); pr.add_argument("values", nargs="+")
    rd = sub.add_parser("reduce"); rd.add_argument("values", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "commutators":
        mat, nz = commutator_matrix()
        print(json.dumps({"pairs": mat, "noncommuting": nz}, indent=2))
        return 0
    p = profile(" ".join(args.values))
    if args.cmd == "reduce":
        print(json.dumps(p["reduction_trajectory"], indent=2))
        return 0
    print(json.dumps(p, indent=2) if args.json else render(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
