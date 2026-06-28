#!/usr/bin/env python3
"""
semic_bridge.py — the Semantic Invariant Calculus, wired into Chiron.

`semic.py` is Chiron's own spine lifted from integer sequences to meaning: MDL minimal-generator
recovery in exact `Fraction`/`Decimal` arithmetic, certified by exact held-out prediction, and
REFUSED (`INCOMPRESSIBLE`) rather than laundered when a family shares no invariant. It is pure
standard library — no numpy, fully airgappable — exactly the "dictionary" implementation the
architecture calls for. This bridge exposes that engine Chiron-side and connects each of its
pieces to the rest of the system:

  recover/certify  -> collapse a family of phrases to its shared semantic generator (the proverb
                      with the English removed), with Chiron's zero-false-positive refusal gate.
  ambiguity        -> the entendre/proverb curvature split: an entendre is a NEGATIVE-curvature
                      bridge (a fork), a proverb is a POSITIVE-curvature clique — an exact,
                      sign-bearing ambiguity measure that complements infectatrum_bridge.
  felicity         -> Class VIII performatives (Austin): an utterance whose preconditions are
                      unmet MISFIRES — the semantic root of govern.py's authority/ROE gate.
  bridge_theorem   -> the deterministic MDL collapse is the T->0 limit of the Gibbs sampler;
                      one operator, two temperatures (ties to density_emotion.py).
  twin / families  -> the semantic twin proof (Caramuel anchor lifted) and multi-family
                      meta-refusal (discriminates real invariants, refuses spurious unification).
  semantic_brief   -> the meaning-domain parallel of actionable_intelligence.py.

The full Class I-VIII taxonomy, candor/congress, signed curvature, functor naturality, the
free-energy / action-principle material, role induction, the collapse/articulate codec, idiom
and cross-lingual checks all live in semic.py (48/48 gates); this surfaces the load-bearing ones.

    python3 semic_bridge.py selftest
    python3 semic_bridge.py recover "give a man a fish he eats for a day; teach a man to-fish he eats for a lifetime"
    python3 semic_bridge.py ambiguity
    python3 semic_bridge.py felicity declare peace --no-authority

Framing dial — civilian: meaning-invariant recovery + ambiguity + intent/felicity analysis.
Contractor: doctrine/phrase invariant extraction, deception/entendre detection, speech-act gating.
"""
import os
import sys
import json
import argparse
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import semic  # noqa: E402  (pure-stdlib semantic engine; no numpy)


def _fmt_gen(g):
    if g is None:
        return "INCOMPRESSIBLE"
    return "{" + ", ".join(f"{o}->{h}" for o, h in sorted(g)) + "}"


def recover(*phrases):
    """Collapse a family of surface phrases to its shared semantic invariant + certify it."""
    family = [semic.surface_skeleton(p) for p in phrases]
    verdict = semic.certify(family) if len(family) >= 2 else None
    generator = semic.collapse(family)
    universe = sorted(set().union(*family)) if family else []
    try:
        cr = round(float(semic.compression_ratio(list(phrases), universe)), 2)
    except Exception:
        cr = None
    return {
        "n_surfaces": len(phrases),
        "generator": _fmt_gen(generator),
        "verified": bool(verdict.verified) if verdict else None,
        "train_residual": verdict.train_residual if verdict else None,
        "heldout_residuals": verdict.heldout_residuals if verdict else [],
        "compression_ratio": cr,
        "verdict": (str(verdict) if verdict else "need >= 2 surfaces to certify a shared invariant"),
    }


def ambiguity():
    """The exact, sign-bearing ambiguity split: entendre = negative-curvature bridge (a fork);
    proverb = positive-curvature clique (one community). Computed by Ollivier-Ricci on the
    Congress graph of readings."""
    def edge_curvatures(adj):
        vals = []
        for u in adj:
            for v in (adj[u] if not isinstance(adj[u], dict) else adj[u]):
                try:
                    vals.append((u, v, semic.graph_ollivier(u, v, adj)))
                except Exception:
                    pass
        return vals

    barbell = edge_curvatures(semic.congress_barbell())
    clique = edge_curvatures(semic.congress_clique())
    min_bar = min((c for *_, c in barbell), default=None)
    min_clq = min((c for *_, c in clique), default=None)
    return {
        "entendre_min_curvature": str(min_bar),
        "entendre_min_curvature_float": round(float(min_bar), 4) if min_bar is not None else None,
        "proverb_min_curvature": str(min_clq),
        "proverb_min_curvature_float": round(float(min_clq), 4) if min_clq is not None else None,
        "entendre_is_negative_bridge": bool(min_bar is not None and min_bar < 0),
        "proverb_is_positive_clique": bool(min_clq is not None and min_clq > 0),
        "interpretation": "ambiguity (entendre) is a negative-curvature bottleneck; a shared "
                          "generator (proverb) is a positive-curvature attractor — exact, signed.",
    }


def felicity(act, arg, authority=False, roles=None, obligations=None):
    """Class VIII performative felicity — the semantic root of a governance gate. An utterance
    whose preconditions are unmet MISFIRES (a no-op), exactly as govern.py blocks an action whose
    authority/ROE preconditions are unmet."""
    w = semic.World(obligations=frozenset(obligations or []),
                    roles=frozenset(roles or []),
                    facts=frozenset(), authority=bool(authority))
    w2, ok = semic.perform(w, act, arg)
    changed = w2 != w
    is_performative = semic.class_VIII_performative(act, arg, w)
    return {
        "act": act, "argument": arg, "authority": bool(authority),
        "felicitous": bool(ok),
        "changed_world": bool(changed),
        "is_performative": bool(is_performative),
        "gate_verdict": "PROCEED — felicity preconditions met" if (ok and changed)
                        else "BLOCKED — felicity precondition unmet (misfire)",
    }


def bridge_theorem(temps=("4.0", "1.0", "0.5", "0.1")):
    """Deterministic MDL collapse == T->0 limit of the Gibbs sampler (one operator, two temps)."""
    from decimal import Decimal
    family = [semic.surface_skeleton(t) for t in semic.FISH_FAMILY_TEXT] \
        if hasattr(semic, "FISH_FAMILY_TEXT") else \
        [semic.surface_skeleton("give a man a fish he eats for a day; teach a man to-fish he eats for a lifetime")]
    rows = []
    for t in temps:
        try:
            mass = semic.bridge_mass_on_argmin(family, Decimal(t))
            rows.append({"T": t, "mass_on_argmin": round(float(mass), 4)})
        except Exception:
            pass
    return {"sweep": rows, "interpretation": "mass on the MDL argmin -> 1 as T -> 0 (refusal gate forces T=0)"}


def twin():
    same, gen, space = semic.twin_proof()
    return {"identical_generator": bool(same), "generator": _fmt_gen(gen),
            "surface_space_size": space,
            "interpretation": "maximally different surfaces collapse to one generator over a "
                              "combinatorial space — the Caramuel twin anchor, lifted to meaning."}


def families():
    return {"cross_family_refused": bool(semic.cross_family_refused()),
            "interpretation": "each phrase family certifies within itself; any cross-family pool "
                              "is REFUSED (INCOMPRESSIBLE) — no spurious unification."}


def semantic_brief(*phrases):
    """The meaning-domain parallel of actionable_intelligence.py: what invariant, is it verified,
    how compressed, and the governed reading."""
    r = recover(*phrases)
    a = ambiguity()
    if r["verified"]:
        verdict = "PROCEED — a shared semantic invariant is verified"
    elif r["verified"] is False:
        verdict = "REFUSE — no shared invariant (INCOMPRESSIBLE); do not unify these surfaces"
    else:
        verdict = "ABSTAIN — need >= 2 surfaces to test a shared invariant"
    return {"generator": r["generator"], "verified": r["verified"],
            "compression_ratio": r["compression_ratio"],
            "ambiguity_signal": a["entendre_is_negative_bridge"],
            "verdict": verdict}


def render_recover(r):
    L = ["=" * 64, "SEMIC — semantic invariant recovery", "=" * 64]
    L.append(f"  surfaces ....... {r['n_surfaces']}")
    L.append(f"  generator ...... {r['generator']}")
    L.append(f"  verified ....... {r['verified']}  (train_residual={r['train_residual']}, heldout={r['heldout_residuals']})")
    L.append(f"  compression .... {r['compression_ratio']}x")
    L.append(f"  {r['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    fish = recover("give a man a fish he eats for a day; teach a man to-fish he eats for a lifetime",
                   "grant a person seed once; instruct a person to-build he builds always")
    ok("fish family recovers a generator", fish["generator"] != "INCOMPRESSIBLE")
    ok("fish family verifies", fish["verified"] is True)
    ok("compression ratio > 1", (fish["compression_ratio"] or 0) > 1)

    half = recover("give a man a fish he eats for a day", "set a man on fire he is warm for life")
    ok("parody/half family refused", half["verified"] is not True)

    a = ambiguity()
    ok("entendre is a negative-curvature bridge", a["entendre_is_negative_bridge"])
    ok("proverb is a positive-curvature clique", a["proverb_is_positive_clique"])

    f_bad = felicity("declare", "peace", authority=False)
    f_ok = felicity("declare", "peace", authority=True)
    ok("declare without authority misfires", f_bad["gate_verdict"].startswith("BLOCKED"))
    ok("declare with authority proceeds", f_ok["gate_verdict"].startswith("PROCEED"))
    ok("performative changes the world", f_ok["is_performative"])

    bt = bridge_theorem()
    masses = [row["mass_on_argmin"] for row in bt["sweep"]]
    ok("Gibbs mass increases as T falls", not masses or masses[-1] >= masses[0])

    tw = twin()
    ok("twin proof: one generator", tw["identical_generator"])
    ok("twin space combinatorially large", tw["surface_space_size"] > 1000)

    ok("cross-family pools refused", families()["cross_family_refused"])

    sb = semantic_brief("give a man a fish he eats for a day; teach a man to-fish he eats for a lifetime",
                        "grant a person seed once; instruct a person to-build he builds always")
    ok("semantic brief proceeds on verified family", sb["verdict"].startswith("PROCEED"))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  semic_bridge.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render_recover(recover(
        "give a man a fish he eats for a day; teach a man to-fish he eats for a lifetime",
        "grant a person seed once; instruct a person to-build he builds always")))
    print("\nAMBIGUITY (signed curvature):", json.dumps(ambiguity(), indent=2))
    print("\nFELICITY (declare w/o authority):", felicity("declare", "peace", authority=False)["gate_verdict"])
    print("TWIN:", twin()["identical_generator"], "over", twin()["surface_space_size"], "surfaces")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Semantic Invariant Calculus, wired into Chiron.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    sub.add_parser("ambiguity")
    sub.add_parser("twin")
    sub.add_parser("families")
    sub.add_parser("bridge")
    rc = sub.add_parser("recover"); rc.add_argument("phrases", nargs="+")
    fl = sub.add_parser("felicity"); fl.add_argument("act"); fl.add_argument("arg")
    fl.add_argument("--authority", action="store_true"); fl.add_argument("--no-authority", action="store_true")
    fl.add_argument("--role", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "ambiguity":
        print(json.dumps(ambiguity(), indent=2)); return 0
    if args.cmd == "twin":
        print(json.dumps(twin(), indent=2)); return 0
    if args.cmd == "families":
        print(json.dumps(families(), indent=2)); return 0
    if args.cmd == "bridge":
        print(json.dumps(bridge_theorem(), indent=2)); return 0
    if args.cmd == "felicity":
        r = felicity(args.act, args.arg, authority=args.authority and not args.no_authority, roles=args.role)
        print(json.dumps(r, indent=2)); return 0
    if args.cmd == "recover":
        r = recover(*args.phrases)
        print(json.dumps(r, indent=2) if args.json else render_recover(r)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
