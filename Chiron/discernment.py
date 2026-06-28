#!/usr/bin/env python3
"""
discernment.py — confidence from convergence, not authority.

The discernment engine, assembled. A finding is examined by independent witnesses, each blind to
the others' reasoning, each answering one question and SHOWING the measurement that drove its
vote. Confidence is the CONVERGENCE of the witnesses — not the verdict of any one of them. When a
witness dissents, that disagreement is diagnostic: it names exactly where reality, value, or
honesty pushed back.

  EPISTEMIC    does it appear true?        (chiron — a verified law)
  ONTOLOGICAL  could it survive?           (uma_bridge — robustness under perturbation)
  ADVERSARIAL  survive challenge?          (cross_examine — no peer generator)
  AXIOLOGICAL  is it elegant?              (aesthetics — beauty / parsimony)
  AXIOLOGICAL  worth preserving?           (ontological — V-Units value)
  CANDOR       explanation honest?         (candor — anti-patronization)

Where judgment.py is sequential veto (Earned Finality), discernment is parallel convergence: it
reports HOW MUCH the witnesses agree and exactly which one dissents.

Public API (consumed elsewhere): discern(surface).

    python3 discernment.py selftest
    python3 discernment.py assess 1 1 2 3 5 8 13 21
    python3 discernment.py batch "1 1 2 3 5 8" "41 19 50 83 6 9"

Framing dial — civilian: multi-witness confidence with a named point of failure. Contractor:
independent-cross-check fusion; convergence score + dissent localization + governed call.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import uma_bridge      # noqa: E402
import cross_examine   # noqa: E402
import aesthetics      # noqa: E402
import ontological     # noqa: E402
import govern          # noqa: E402
import candor_bridge   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def discern(surface, stakes=None):
    vals = _nums(surface)
    surface_str = " ".join(str(v) for v in vals)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])

    witnesses = []

    witnesses.append(("epistemic", "appears true (verified law)", bool(inv.verified),
                      f"model={inv.model_class}, verified={inv.verified}"))

    rob = _safe(lambda: uma_bridge.robustness(surface_str), {}) or {}
    witnesses.append(("ontological:robustness", "survives perturbation",
                      bool(rob.get("structure_persisted_after_evolution")),
                      f"persisted={rob.get('structure_persisted_after_evolution')}, lyapunov={rob.get('lyapunov_forecast')}"))

    xe = _safe(lambda: cross_examine.cross_examine(surface_str), {}) or {}
    witnesses.append(("adversarial", "survives cross-examination",
                      str(xe.get("verdict", "")).startswith("SURVIVES"),
                      xe.get("verdict", "n/a")[:48]))

    aes = _safe(lambda: aesthetics.aesthetic(surface_str), {}) or {}
    witnesses.append(("axiological:aesthetic", "elegant / parsimonious",
                      float(aes.get("beauty", 0)) >= 0.5, f"beauty={aes.get('beauty')}"))

    val = _safe(lambda: ontological.v_units(surface_str), {}) or {}
    Vval = float(val.get("V_units", 0.0))
    witnesses.append(("axiological:value", "worth preserving", Vval >= 0.5, f"V_units={round(Vval, 3)}"))

    cand = _safe(lambda: candor_bridge.audit_finding(surface_str), {}) or {}
    cscore = float(cand.get("candor_score", 0))
    witnesses.append(("candor", "explanation is honest", cscore >= 0.6, f"candor={round(cscore, 3)}"))

    affirm = sum(1 for w in witnesses if w[2])
    total = len(witnesses)
    confidence = round(affirm / total, 3)
    dissent = [w[0] for w in witnesses if not w[2]]

    Hp = float((stakes or {}).get("Hp", 0.5))
    g = govern.govern(0.6, 0.7, Hp, 0.6, (Vval if inv.verified else 0.3),
                      (stakes or {}).get("domain", "general"),
                      {"human_in_loop": True, "authority_present": True, "within_roe": True})

    if affirm == total and not g["verdict"].startswith(("ESCALATE", "REJECT")):
        verdict = "CONFIRM — all witnesses converge"
    elif affirm == 0:
        verdict = "REJECT — no witness affirms"
    elif affirm >= total - 1:
        verdict = "QUALIFIED — near-consensus" + (f"; dissent: {', '.join(dissent)}" if dissent else "; governance hold")
    else:
        verdict = "SPLIT — witnesses disagree (diagnostic)"

    return {
        "law": inv.model_class, "verified": bool(inv.verified),
        "witnesses": [{"witness": w[0], "asks": w[1], "affirms": w[2], "evidence": w[3]} for w in witnesses],
        "convergence_confidence": confidence,
        "affirming": affirm, "of": total,
        "dissent": dissent,
        "flip_to_change": max(0, (total // 2 + 1) - affirm) if affirm <= total // 2 else 0,
        "governance": {"verdict": g["verdict"].split(" —")[0], "socpm_lhs": g["socpm"]["lhs"]},
        "verdict": verdict,
    }


def batch(surfaces):
    return [{"surface": s, "confidence": discern(s)["convergence_confidence"],
             "verdict": discern(s)["verdict"].split(" —")[0]} for s in surfaces]


def render(d):
    L = ["=" * 64, "DISCERNMENT — independent witnesses, confidence by convergence", "=" * 64]
    L.append(f"  finding: {d['law']}  (verified={d['verified']})")
    for w in d["witnesses"]:
        mark = "✓" if w["affirms"] else "✗"
        L.append(f"     [{mark}] {w['witness']:<24} {w['asks']:<28} {w['evidence']}")
    L.append(f"  convergence confidence ... {d['convergence_confidence']}  ({d['affirming']}/{d['of']})")
    if d["dissent"]:
        L.append(f"  dissent (diagnostic) ..... {', '.join(d['dissent'])}")
    L.append(f"  governance ............... {d['governance']['verdict']} (SoCPM lhs {d['governance']['socpm_lhs']})")
    L.append(f"  >> {d['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    fib = discern("1 1 2 3 5 8 13 21 34 55")
    ok("clean law -> high convergence", fib["convergence_confidence"] >= 0.8)
    ok("clean law -> CONFIRM or QUALIFIED", fib["verdict"].split()[0] in ("CONFIRM", "QUALIFIED"))
    ok("six witnesses", len(fib["witnesses"]) == 6)
    ok("each witness shows evidence", all(w["evidence"] for w in fib["witnesses"]))

    noise = discern("41 19 50 83 6 9 68 12")
    ok("noise -> low convergence", noise["convergence_confidence"] <= 0.5)
    ok("noise -> SPLIT or REJECT", noise["verdict"].split()[0] in ("SPLIT", "REJECT"))
    ok("noise names dissent", len(noise["dissent"]) >= 3)
    ok("noise > clean dissent count", len(noise["dissent"]) > len(fib["dissent"]))

    b = batch(["1 1 2 3 5 8 13 21", "41 19 50 83 6 9"])
    ok("batch returns per-surface confidence", len(b) == 2 and all("confidence" in x for x in b))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  discernment.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 1 2 3 5 8 13 21 34 55", "41 19 50 83 6 9 68 12"]:
        print(f"\n### {s}")
        print(render(discern(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Multi-witness discernment over a finding.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    a = sub.add_parser("assess"); a.add_argument("values", nargs="+")
    bt = sub.add_parser("batch"); bt.add_argument("surfaces", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "batch":
        print(json.dumps(batch(args.surfaces), indent=2)); return 0
    if args.cmd == "assess":
        d = discern(" ".join(args.values))
        print(json.dumps(d, indent=2) if args.json else render(d)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
