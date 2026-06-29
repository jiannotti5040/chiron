#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
judgment.py — The Chief Justice & the Principle of Earned Finality (Chiron Jurisprudence Suite).

The master execution module. It does no mathematics; it is pure structural jurisprudence. It
closes the constitutional loop by enforcing EARNED FINALITY: a conclusion is final only when
every admissible avenue for materially changing it has been exhausted. It polls the sovereign
courts in strict sequence, and the first court to object stops the proceeding with a verifiable
abstention — never a forced guess.

  COURT 1  EPISTEMIC      (chiron.collapse)        Did fact-finding extract a verified rule?
                                                   No  -> ABSTAIN (no justiciable question)
  COURT 2  DEFENSE        (cross_examine)          Did the adversary fail to find reasonable doubt?
                                                   Doubt -> ABSTAIN (injunction; finality blocked)
  COURT 3  ONTOLOGICAL    (uma_bridge)             Did the rule survive decoherence and chaos?
                                                   Shatters -> ABSTAIN (does not survive reality)
  COURT 4  CANDOR         (candor_bridge)          Was no self-deception used to inflate harmony?
                                                   Lied to self -> HALT (integrity breach)
  COURT 5  REGULATORY     (govern / SoCPM)         Did deployment clear the safety threshold?
                                                   Over T -> ESCALATE (human authority required)
                                                   Unlawful -> ABSTAIN (blocked by law)
  SEALING  ARCHIVES       (certify_finding)        All courts cleared, no injunction -> SEAL the
                                                   Daubert certificate. The judgment is FINAL.

The four constitutional constraints are enforced programmatically:
  - IMMUTABILITY OF EVIDENCE: the evidence is hashed on entry; every court receives a copy; the
    hash is re-checked on exit and reported. No court may alter the record.
  - JURISDICTIONAL ISOLATION: the rule is found once, in the Epistemic Court, and is never
    rewritten downstream. The Regulatory Court may only BLOCK or ESCALATE the action; it cannot
    touch the math. Each court returns only its own ruling.
  - HONEST ABSTENTION: the right to abstain is absolute. Any failed condition yields a structured,
    verifiable disposition (ABSTAIN / HALT / ESCALATE), not a guess.
  - ZERO DEPENDENCIES: this module is brutalist — standard library only; the courts it polls are
    the sovereign modules already in the pipeline.

    python3 judgment.py selftest
    python3 judgment.py try 1 1 2 3 5 8 13 21 --domain general
    python3 judgment.py try 2 4 6 8 10 12 --domain military --json

Dispositions: CERTIFY (final) | ABSTAIN | ESCALATE | HALT.
"""
import os
import sys
import json
import hashlib
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron            # noqa: E402  Epistemic Court
import cross_examine     # noqa: E402  Defense
import uma_bridge        # noqa: E402  Ontological Court
import candor_bridge     # noqa: E402  Candor Review
import govern            # noqa: E402  Regulatory Court
import certify_finding   # noqa: E402  Archives

ABSTAIN_CLASSES = ("incompressible", "general", "random")
CANDOR_FLOOR = 0.5


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _seal(vals):
    return hashlib.sha256(repr(tuple(vals)).encode()).hexdigest()[:16]


def judge(surface, domain="general", context=None):
    vals = _nums(surface)
    entry_seal = _seal(vals)
    docket = []

    def ruling(court, jurisdiction, cleared, finding, disposition):
        docket.append({"court": court, "jurisdiction": jurisdiction, "cleared": bool(cleared),
                       "finding": finding, "disposition": disposition})

    def close(disposition, opinion, certificate=None):
        return {
            "disposition": disposition,           # CERTIFY | ABSTAIN | ESCALATE | HALT
            "opinion": opinion,
            "docket": docket,
            "courts_polled": len(docket),
            "evidence_hash": entry_seal,
            "evidence_immutable": entry_seal == _seal(vals),
            "final": disposition == "CERTIFY",
            "certificate": certificate,
        }

    # ----- COURT 1: EPISTEMIC (fact-finding) -----
    inv = chiron.collapse(list(vals))
    if not inv.verified or inv.model_class in ABSTAIN_CLASSES:
        ruling("Epistemic Court", "fact-finding", False,
               f"no verified generator (class={inv.model_class})", "ABSTAIN")
        return close("ABSTAIN", "Epistemic Court: no verified rule was extracted; there is no "
                                "justiciable question. The court abstains.")
    ruling("Epistemic Court", "fact-finding", True, f"verified generator: {inv.model_class}", "ADMITTED")

    # ----- COURT 2: DEFENSE (reasonable doubt) -----
    xe = cross_examine.cross_examine(list(vals))
    if xe.get("injunction", {}).get("active"):
        ruling("Defense (Cross-Examination)", "reasonable-doubt", False,
               xe["injunction"]["reason"], "INJUNCTION")
        return close("ABSTAIN", "Defense: a peer explanation survives — reasonable doubt is "
                                "established and finality is blocked. The court abstains.")
    ruling("Defense (Cross-Examination)", "reasonable-doubt", True,
           "search space exhausted; no peer generator", "CLEARED")

    # ----- COURT 3: ONTOLOGICAL (physical survival) -----
    rob = uma_bridge.robustness(" ".join(str(v) for v in vals))
    survived = bool(rob.get("structure_persisted_after_evolution"))
    if not survived:
        ruling("Ontological Court", "physical-survival", False,
               f"rule shattered under decoherence (lyapunov={rob.get('lyapunov_forecast')})", "ABSTAIN")
        return close("ABSTAIN", "Ontological Court: the rule did not survive physical reality "
                                "(decoherence / Lyapunov chaos). The court abstains.")
    ruling("Ontological Court", "physical-survival", True,
           f"survived decoherence; lyapunov={rob.get('lyapunov_forecast')}", "UPHELD")

    # ----- COURT 4: CANDOR (no self-deception) -----
    cand = candor_bridge.audit_finding(list(vals))
    candor_score = float(cand.get("candor_score", 0.0))
    if candor_score < CANDOR_FLOOR:
        ruling("Candor Review", "self-honesty", False,
               f"explanation failed the candor audit (score={candor_score})", "HALT")
        return close("HALT", "Candor Review: the engine's own account fails the honesty audit — "
                             "evidence of self-deception to inflate harmony. The proceeding halts.")
    ruling("Candor Review", "self-honesty", True, f"candor score {candor_score}", "CLEAN")

    # ----- COURT 5: REGULATORY (deployment gate) -----
    ctx = context or {"human_in_loop": True, "authority_present": True, "within_roe": True,
                      "court_facing": True, "merkle_root_present": True,
                      "attestation_present": True, "replay_seed_present": True}
    gov = govern.govern(0.6, 0.7, 0.7, 0.6, 0.9, domain, ctx)
    head = gov["verdict"].split()[0]
    if head == "REJECT":
        ruling("Regulatory Court", "deployment-gate", False, gov["verdict"], "BLOCKED")
        return close("ABSTAIN", f"Regulatory Court: the action is blocked by law — {gov['verdict']}. "
                                "The court abstains from deployment.")
    if head == "ESCALATE":
        ruling("Regulatory Court", "deployment-gate", False, gov["verdict"], "ESCALATED")
        return close("ESCALATE", f"Regulatory Court: {gov['verdict']}. The SoCPM threshold is not "
                                 "cleared for autonomous action; human authorization is required.")
    ruling("Regulatory Court", "deployment-gate", True, gov["verdict"], "CLEARED")

    # ----- EARNED FINALITY: all courts cleared, no injunction -> SEAL -----
    cert = certify_finding.certify_finding(list(vals), domain=domain)
    ruling("Archives", "sealing", True, f"Daubert {cert['admissibility']}", "SEALED")
    return close("CERTIFY",
                 "Earned Finality: every admissible avenue to change the conclusion has been "
                 "exhausted and no court holds an active injunction. The certificate is sealed.",
                 certificate={"admissibility": cert["admissibility"],
                              "merkle_root": cert["merkle_root"],
                              "court_deployable": cert["court_deployable"]})


def render(j):
    L = ["=" * 68, "JUDGMENT — Chief Justice, Earned Finality", "=" * 68]
    for r in j["docket"]:
        mark = "✓" if r["cleared"] else "✗"
        L.append(f"  [{mark}] {r['court']:<26} {r['disposition']:<11} {r['finding'][:40]}")
    L.append("-" * 68)
    L.append(f"  evidence immutable: {j['evidence_immutable']}   courts polled: {j['courts_polled']}")
    L.append(f"  >> DISPOSITION: {j['disposition']}")
    L.append(f"     {j['opinion']}")
    if j["certificate"]:
        L.append(f"     sealed: {j['certificate']['admissibility']} (merkle {j['certificate']['merkle_root'][:16]}…)")
    L.append("=" * 68)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    # a clean, low-stakes verified rule should reach Earned Finality
    fib = judge("1 1 2 3 5 8 13 21 34 55", "general")
    ok("fibonacci (general) -> CERTIFY", fib["disposition"] == "CERTIFY")
    ok("certify is final", fib["final"])
    ok("certify sealed a certificate", fib["certificate"] is not None)
    ok("all courts polled on certify", fib["courts_polled"] >= 5)
    ok("evidence immutable through judgment", fib["evidence_immutable"])

    # no verified rule -> abstain at the first court
    noise = judge("41 19 50 83 6 9 68 12", "general")
    ok("noise -> ABSTAIN", noise["disposition"] == "ABSTAIN")
    ok("noise stopped at Epistemic Court", noise["courts_polled"] == 1)

    # high-stakes military deployment without safeguards -> not certified (escalate/abstain)
    mil = judge("2 4 6 8 10 12 14 16", "military",
                {"human_in_loop": False, "authority_present": True, "within_roe": True})
    ok("unsafeguarded military -> not CERTIFY", mil["disposition"] != "CERTIFY")
    ok("military disposition is ESCALATE or ABSTAIN", mil["disposition"] in ("ESCALATE", "ABSTAIN"))

    # immutability: caller's list never mutated across the whole proceeding
    data = [1, 1, 2, 3, 5, 8, 13, 21]
    snap = list(data)
    judge(data, "general")
    ok("evidence immutability across judgment", data == snap)

    # jurisdictional isolation: the disposition vocabulary is closed
    ok("disposition is a closed vocabulary",
       fib["disposition"] in ("CERTIFY", "ABSTAIN", "ESCALATE", "HALT"))
    ok("docket records each court's own ruling only",
       all(set(r.keys()) == {"court", "jurisdiction", "cleared", "finding", "disposition"} for r in fib["docket"]))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  judgment.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render(judge("1 1 2 3 5 8 13 21 34 55", "general")))
    print()
    print(render(judge("41 19 50 83 6 9 68 12", "general")))
    print()
    print(render(judge("2 4 6 8 10 12 14 16", "military",
                       {"human_in_loop": False, "authority_present": True, "within_roe": True})))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="The Chief Justice: Earned Finality over the sovereign courts.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    t = sub.add_parser("try"); t.add_argument("values", nargs="+"); t.add_argument("--domain", default="general")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "try":
        j = judge(" ".join(args.values), domain=args.domain)
        print(json.dumps(j, indent=2) if args.json else render(j))
        return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
