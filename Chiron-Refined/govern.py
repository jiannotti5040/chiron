#!/usr/bin/env python3
"""
Governance gate (B-4) — LexGuard / SoCPM on any claim, standalone.

Chiron already carries the governance machinery inside its certifier; this exposes
the claim-level gate — the SoCPM decision rule and its LexGuard gate — so you can run
it on ANY recommendation, not only a full decision context.

SoCPM rule:  (Cx · Ar · Hp − Mc · (1 − V)) ≤ T   (T = 0.25). Above T ⇒ redirect/escalate.
  Cx context-sensitivity · Ar autonomy-of-recommendation · Hp human-impact ·
  Mc mitigating-controls · V value-alignment (all in [0,1]).

    python3 govern.py --Cx 0.8 --Ar 0.9 --Hp 0.9 --Mc 0.3 --V 0.5
    python3 govern.py --json --Cx ...

Framing dial — civilian: AI standard-of-care / duty-of-care gate. Contractor: rules-of-
engagement / policy-isolation compliance gate with an escalation path.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron  # noqa: E402


def govern(Cx, Ar, Hp, Mc, V):
    s = chiron.SoCPMScores(Cx=Cx, Ar=Ar, Hp=Hp, Mc=Mc, V=V)
    redirect, lhs = chiron.socpm_redirect_required(s)
    gate = chiron.LexGuardFourGate().check_socpm_gate(s)
    return {
        "scores": {"Cx": Cx, "Ar": Ar, "Hp": Hp, "Mc": Mc, "V": V},
        "socpm_lhs": round(lhs, 4),
        "threshold_T": chiron.SOCPM_THRESHOLD_T,
        "redirect_or_escalate_required": bool(redirect),
        "lexguard_socpm_gate": gate.result.value,
        "reason": gate.reason,
    }


def main():
    ap = argparse.ArgumentParser()
    for k in ("Cx", "Ar", "Hp", "Mc", "V"):
        ap.add_argument("--" + k, type=float, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    vals = {k: getattr(args, k) for k in ("Cx", "Ar", "Hp", "Mc", "V")}
    if any(v is None for v in vals.values()):
        # a worked default: a high-impact, weakly-controlled recommendation
        vals = {"Cx": 0.8, "Ar": 0.9, "Hp": 0.9, "Mc": 0.3, "V": 0.5}
    out = govern(**vals)
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    print("=" * 58)
    print("GOVERNANCE GATE — SoCPM / LexGuard on a claim")
    print("=" * 58)
    print("  scores ......... %s" % out["scores"])
    print("  SoCPM lhs ...... %.4f   (threshold T = %s)" % (out["socpm_lhs"], out["threshold_T"]))
    print("  gate ........... %s" % out["lexguard_socpm_gate"].upper())
    print("  verdict ........ %s" % ("REDIRECT / ESCALATE TO HUMAN"
                                     if out["redirect_or_escalate_required"] else "PROCEED"))
    print("  reason ......... %s" % out["reason"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
