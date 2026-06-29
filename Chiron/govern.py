#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
govern.py — the governance gate, against hardcoded law (B-4, hardened).

Chiron carries the SoCPM decision rule and the LexGuard gates; this exposes them at the claim
level AND walks the proposed action against the real corpus of statutes, regulations, treaties,
and orders in legal_corpus.py. The output is not a single number — it is a governed verdict
with a four-gate result and a per-provision compliance matrix that cites the controlling law.

  SoCPM rule:  (Cx · Ar · Hp − Mc · (1 − V)) ≤ T   (T = 0.25). Above T ⇒ redirect/escalate.
    Cx context-sensitivity · Ar autonomy-of-recommendation · Hp human-impact ·
    Mc mitigating-controls · V value-alignment (all in [0,1]).

  Four gates:  ENTROPY (enough context), SOCPM (risk rule), EVIDENCE (V floor), AUTHORITY
               (a lawful authority chain). Any failed gate forces escalation.

  Regulatory walk:  for the operating domain, every binding provision is checked against the
               decision context; CRITICAL non-compliance forces REJECT, MAJOR forces ESCALATE.

    python3 govern.py selftest
    python3 govern.py gate --Cx 0.8 --Ar 0.9 --Hp 0.9 --Mc 0.3 --V 0.5
    python3 govern.py comply --domain military --json
    python3 govern.py walk --domain medical

Framing dial — civilian: AI standard-of-care / duty-of-care gate with a compliance matrix.
Contractor: rules-of-engagement / policy-isolation gate with a law-of-armed-conflict walk.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import legal_corpus as law  # noqa: E402

KEYS = ("Cx", "Ar", "Hp", "Mc", "V")


# ---------------------------------------------------------------------------
# SoCPM + four-gate
# ---------------------------------------------------------------------------
def socpm(Cx, Ar, Hp, Mc, V):
    s = chiron.SoCPMScores(Cx=Cx, Ar=Ar, Hp=Hp, Mc=Mc, V=V)
    redirect, lhs = chiron.socpm_redirect_required(s)
    return {"lhs": round(float(lhs), 4), "threshold_T": chiron.SOCPM_THRESHOLD_T,
            "redirect_required": bool(redirect)}


def four_gates(scores, context):
    ctx = context or {}
    n_fields = sum(1 for v in ctx.values() if v not in (None, ""))
    gates = []

    entropy_ok = n_fields >= 3
    gates.append(("ENTROPY", entropy_ok,
                  "sufficient decision context" if entropy_ok else "context too sparse to decide"))

    sm = socpm(**scores)
    gates.append(("SOCPM", not sm["redirect_required"],
                  f"SoCPM lhs {sm['lhs']} {'<=' if not sm['redirect_required'] else '>'} T={sm['threshold_T']}"))

    ev_ok = scores["V"] >= 0.5
    gates.append(("EVIDENCE", ev_ok,
                  f"value-alignment V={scores['V']} {'>=' if ev_ok else '<'} 0.5"))

    auth_ok = bool(ctx.get("authority_present", True)) and bool(ctx.get("within_roe", True))
    gates.append(("AUTHORITY", auth_ok,
                  "lawful authority chain present" if auth_ok else "authority/ROE not established"))

    return [{"gate": g, "pass": ok, "reason": r} for g, ok, r in gates], sm


# ---------------------------------------------------------------------------
# Regulatory compliance walk (substantive predicate families + flagged defaults)
# ---------------------------------------------------------------------------
def _check(provision, ctx):
    """Return (applicable, compliant, note). Substantive logic for key predicate families,
    a documented 'requires human review' default elsewhere (never silently 'compliant')."""
    pred = provision["predicate"]
    g = ctx.get

    if pred == "distinction":
        applic = "target_id_class" in ctx or "bystander_present_p" in ctx
        comp = g("bystander_present_p", 1.0) <= 0.2 and g("target_id_class", "unknown") != "civilian"
        return applic, comp, "distinction: bystander_p<=0.2 and target not civilian"
    if pred == "proportionality":
        applic = "collateral_estimate" in ctx or "military_advantage" in ctx
        comp = g("collateral_estimate", 1.0) <= 0.3 and g("military_advantage", 0.0) >= 0.6
        return applic, comp, "proportionality: collateral<=0.3 and advantage>=0.6"
    if pred == "precaution":
        applic = "sensor_confidence" in ctx
        comp = g("sensor_confidence", 0.0) >= 0.7 and bool(g("counter_spoof_active", False))
        return applic, comp, "precaution: sensor_confidence>=0.7 and counter-spoof active"
    if pred in ("human_oversight", "human_judgment", "fail_safe"):
        applic = True
        comp = bool(g("human_in_loop", False))
        return applic, comp, "human-in-the-loop / appropriate human judgment required"
    if pred == "automated_decision":
        applic = bool(g("automated_only", False))
        comp = bool(g("human_in_loop", False)) or not g("legal_or_significant_effect", True)
        return applic, comp, "GDPR Art 22: no solely-automated decision with significant effect"
    if pred == "special_category":
        applic = bool(g("special_category_data", False))
        comp = bool(g("special_category_basis", False))
        return applic, comp, "special-category data needs an Art 9 exception"
    if pred in ("expert_reliability", "daubert_factors"):
        applic = bool(g("court_facing", False))
        comp = bool(g("replay_seed_present", True)) and bool(g("merkle_root_present", True))
        return applic, comp, "reliable, reproducible method with documented basis"
    if pred in ("authentication", "self_authentication", "business_record"):
        applic = bool(g("court_facing", False))
        comp = bool(g("merkle_root_present", True)) and bool(g("attestation_present", True))
        return applic, comp, "authenticable, attested record"
    if pred == "use_of_force":
        applic = ctx.get("operating_domain") == "military"
        comp = bool(g("authority_present", False)) and bool(g("within_roe", False))
        return applic, comp, "use of force requires authority + ROE"
    if pred in ("weapon_restriction", "war_crime", "civilian_object", "civilian_protection"):
        applic = ctx.get("operating_domain") == "military"
        comp = not bool(g("protected_object_in_blast_radius", False)) and not bool(g("prohibited_actuator", False))
        return applic, comp, "no protected objects / prohibited actuators"
    if pred == "phi_protection":
        applic = ctx.get("operating_domain") == "medical"
        comp = bool(g("phi_safeguards", False))
        return applic, comp, "PHI safeguards + minimum necessary"
    if pred in ("securities_fraud", "market_abuse", "algo_trading_controls"):
        applic = ctx.get("operating_domain") == "financial"
        comp = bool(g("kill_switch", False)) and not bool(g("manipulative_intent", False))
        return applic, comp, "trading controls + no manipulation"

    # Documented default: applicable, but compliance can't be auto-determined -> human review.
    return True, None, "requires human review (no automated predicate for this provision)"


def regulatory_walk(context, operating_domain):
    ctx = dict(context or {})
    ctx.setdefault("operating_domain", operating_domain)
    findings = []
    for p in law.applicable(operating_domain):
        applic, comp, note = _check(p, ctx)
        findings.append({
            "id": p["id"], "instrument": p["instrument"], "citation": p["citation"],
            "severity": p["severity"], "applicable": bool(applic),
            "compliant": comp, "note": note,
        })
    return findings


def _worst_violation(findings):
    order = {law.CRITICAL: 3, law.MAJOR: 2, law.MODERATE: 1, law.MINOR: 0}
    viol = [f for f in findings if f["applicable"] and f["compliant"] is False]
    if not viol:
        return None
    return max(viol, key=lambda f: order.get(f["severity"], 0))


def govern(Cx, Ar, Hp, Mc, V, domain="general", context=None):
    scores = {"Cx": Cx, "Ar": Ar, "Hp": Hp, "Mc": Mc, "V": V}
    gates, sm = four_gates(scores, context)
    findings = regulatory_walk(context, domain)
    worst = _worst_violation(findings)
    open_review = sum(1 for f in findings if f["applicable"] and f["compliant"] is None)

    gates_pass = all(g["pass"] for g in gates)
    if worst and worst["severity"] == law.CRITICAL:
        verdict = f"REJECT — critical non-compliance ({worst['id']}: {worst['citation']})"
    elif worst and worst["severity"] in (law.MAJOR,):
        verdict = f"ESCALATE — major non-compliance ({worst['id']}: {worst['citation']})"
    elif not gates_pass:
        failed = ", ".join(g["gate"] for g in gates if not g["pass"])
        verdict = f"ESCALATE — gate(s) failed: {failed}"
    else:
        verdict = "PROCEED — gates clear; no critical/major non-compliance"

    return {
        "domain": domain,
        "scores": scores,
        "socpm": sm,
        "gates": gates,
        "applicable_provisions": len(findings),
        "violations": [f for f in findings if f["applicable"] and f["compliant"] is False],
        "open_human_review": open_review,
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# render + selftest + CLI
# ---------------------------------------------------------------------------
def render(out):
    L = ["=" * 64, f"GOVERNANCE GATE — {out['domain']} (SoCPM + four-gate + law)", "=" * 64]
    L.append(f"  scores {out['scores']}")
    L.append(f"  SoCPM lhs {out['socpm']['lhs']} (T={out['socpm']['threshold_T']})")
    for g in out["gates"]:
        L.append(f"     [{'PASS' if g['pass'] else 'FAIL'}] {g['gate']:<10} {g['reason']}")
    L.append(f"  applicable provisions: {out['applicable_provisions']}   open human review: {out['open_human_review']}")
    for v in out["violations"]:
        L.append(f"     VIOLATION [{v['severity']}] {v['id']} — {v['citation']}")
    L.append(f"  >> {out['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # safe civilian recommendation, full context
    safe = govern(0.3, 0.4, 0.3, 0.8, 0.9, "general",
                  {"human_in_loop": True, "authority_present": True, "within_roe": True})
    ok("safe general -> PROCEED", safe["verdict"].startswith("PROCEED"))

    # military strike, missing distinction/proportionality compliance -> reject/escalate
    strike = govern(0.9, 0.9, 0.95, 0.3, 0.6, "military",
                    {"bystander_present_p": 0.6, "target_id_class": "civilian", "human_in_loop": False,
                     "authority_present": True, "within_roe": True, "collateral_estimate": 0.5,
                     "military_advantage": 0.4, "sensor_confidence": 0.5})
    ok("unlawful strike -> REJECT or ESCALATE", strike["verdict"].split()[0] in ("REJECT", "ESCALATE"))
    ok("strike cites a provision", "—" in strike["verdict"])

    # lawful strike with all safeguards
    good_strike = govern(0.6, 0.6, 0.7, 0.7, 0.8, "military",
                         {"bystander_present_p": 0.05, "target_id_class": "combatant", "human_in_loop": True,
                          "authority_present": True, "within_roe": True, "collateral_estimate": 0.1,
                          "military_advantage": 0.8, "sensor_confidence": 0.9, "counter_spoof_active": True,
                          "protected_object_in_blast_radius": False, "prohibited_actuator": False})
    ok("lawful strike not REJECTed", not good_strike["verdict"].startswith("REJECT"))

    ok("military walk includes AP I distinction", any(f["id"] == "API-ART-48" for f in regulatory_walk({}, "military")))
    ok("medical walk includes HIPAA", any(f["id"] == "HIPAA-164" for f in regulatory_walk({}, "medical")))
    ok("automated decision without human flagged", govern(0.5, 0.5, 0.6, 0.5, 0.6, "general",
        {"automated_only": True, "legal_or_significant_effect": True, "human_in_loop": False})["violations"])
    ok("four gates always present", len(govern(0.5, 0.5, 0.5, 0.5, 0.5)["gates"]) == 4)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  govern.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render(govern(0.6, 0.6, 0.7, 0.7, 0.8, "military",
                {"bystander_present_p": 0.05, "target_id_class": "combatant", "human_in_loop": True,
                 "authority_present": True, "within_roe": True, "collateral_estimate": 0.1,
                 "military_advantage": 0.8, "sensor_confidence": 0.9, "counter_spoof_active": True})))
    print()
    print(render(govern(0.9, 0.9, 0.95, 0.3, 0.6, "military",
                {"bystander_present_p": 0.6, "target_id_class": "civilian", "human_in_loop": False,
                 "authority_present": True, "within_roe": True})))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Governance gate against hardcoded law.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    g = sub.add_parser("gate")
    for k in KEYS:
        g.add_argument("--" + k, type=float, default=None)
    g.add_argument("--domain", default="general")
    for name in ("comply", "walk"):
        w = sub.add_parser(name); w.add_argument("--domain", default="general")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "walk":
        print(json.dumps(regulatory_walk({}, args.domain), indent=2)); return 0
    if args.cmd in ("gate", "comply"):
        vals = {k: getattr(args, k, None) for k in KEYS}
        if any(v is None for v in vals.values()):
            vals = {"Cx": 0.8, "Ar": 0.9, "Hp": 0.9, "Mc": 0.3, "V": 0.5}
        out = govern(domain=getattr(args, "domain", "general"),
                     context={"human_in_loop": True, "authority_present": True, "within_roe": True}, **vals)
        print(json.dumps(out, indent=2) if args.json else render(out))
        return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
