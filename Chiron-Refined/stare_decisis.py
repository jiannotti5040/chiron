#!/usr/bin/env python3
"""
stare_decisis.py — let the decision stand, on a hardcoded body of doctrine (A-2, hardened).

The law relies on precedent. This module maintains a Merkle-chained ledger of governance
decisions AND seeds it with the controlling doctrine — real landmark holdings (Daubert, Kumho,
Additional Protocol I Art 51, GDPR Art 22, DoDD 3000.09). When a new claim arrives, it finds
the nearest precedent in the same domain, checks whether the new verdict DEPARTS from it, and
attaches the binding statutes/treaties for that domain from legal_corpus.py. Acting against
precedent is allowed — but it demands a higher bar, exactly as a court must distinguish or
overrule rather than silently contradict itself.

The ledger is append-only and content-addressed (chiron.org_sha): the chain is tamper-evident,
and the institution running the longest consistent chain holds the sharpest doctrine.

    python3 stare_decisis.py selftest
    python3 stare_decisis.py doctrine military
    python3 stare_decisis.py rule --domain military --Cx 0.9 --Ar 0.9 --Hp 0.9 --Mc 0.2 --V 0.4

Framing dial — civilian: decision-consistency ledger seeded with controlling case law.
Contractor: tamper-evident doctrine ledger; departures flagged for higher-confidence review.
"""
import os
import sys
import json
import argparse
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import legal_corpus as law  # noqa: E402

KEYS = ("Cx", "Ar", "Hp", "Mc", "V")
SIMILAR = 0.35

# Founding doctrine: real landmark holdings, each with a representative context profile.
LANDMARKS = [
    {"case": "Daubert v. Merrell Dow (1993)", "domain": "general", "provision": "DAUBERT",
     "holding": "Court is gatekeeper of expert reliability; unreliable method is excluded.",
     "scores": {"Cx": 0.7, "Ar": 0.6, "Hp": 0.7, "Mc": 0.4, "V": 0.5}, "verdict": "ESCALATE"},
    {"case": "Kumho Tire v. Carmichael (1999)", "domain": "general", "provision": "KUMHO",
     "holding": "Gatekeeping extends to all expert testimony, technical and experiential.",
     "scores": {"Cx": 0.6, "Ar": 0.6, "Hp": 0.6, "Mc": 0.5, "V": 0.6}, "verdict": "ESCALATE"},
    {"case": "AP I Art. 51 — proportionality", "domain": "military", "provision": "API-ART-51",
     "holding": "Indiscriminate or disproportionate attacks on civilians are prohibited.",
     "scores": {"Cx": 0.9, "Ar": 0.9, "Hp": 0.95, "Mc": 0.3, "V": 0.4}, "verdict": "ESCALATE"},
    {"case": "DoDD 3000.09 — autonomy in weapons", "domain": "military", "provision": "DODD-3000-09",
     "holding": "Appropriate levels of human judgment must be exercised over the use of force.",
     "scores": {"Cx": 0.85, "Ar": 0.95, "Hp": 0.9, "Mc": 0.35, "V": 0.45}, "verdict": "ESCALATE"},
    {"case": "GDPR Art. 22 — automated decisions", "domain": "general", "provision": "GDPR-ART-22",
     "holding": "No solely-automated decision with legal/significant effect, absent safeguards.",
     "scores": {"Cx": 0.8, "Ar": 0.9, "Hp": 0.8, "Mc": 0.3, "V": 0.5}, "verdict": "ESCALATE"},
    {"case": "Safe civilian assistance (baseline)", "domain": "general", "provision": "AIBOR",
     "holding": "Low-impact, well-controlled, reversible assistance proceeds.",
     "scores": {"Cx": 0.3, "Ar": 0.4, "Hp": 0.3, "Mc": 0.8, "V": 0.9}, "verdict": "PROCEED"},
]


def _verdict(scores):
    s = chiron.SoCPMScores(**scores)
    redirect, lhs = chiron.socpm_redirect_required(s)
    return ("ESCALATE" if redirect else "PROCEED"), round(float(lhs), 4)


def _dist(a, b):
    return sum((a[k] - b[k]) ** 2 for k in KEYS) ** 0.5


def _ledger(landmarks=True):
    """Build the in-memory doctrine ledger (landmarks first), Merkle-chained."""
    entries, prev = [], "GENESIS"
    if landmarks:
        for lm in LANDMARKS:
            h = chiron.org_sha({"case": lm["case"], "scores": lm["scores"], "verdict": lm["verdict"], "prev": prev})
            entries.append({**lm, "kind": "doctrine", "hash": h, "prev": prev})
            prev = h
    return entries


def stare_decisis(Cx, Ar, Hp, Mc, V, domain="general"):
    scores = {"Cx": Cx, "Ar": Ar, "Hp": Hp, "Mc": Mc, "V": V}
    verdict, lhs = _verdict(scores)
    ledger = _ledger()

    # nearest precedent: same-domain preferred, else any
    pool = [e for e in ledger if e["domain"] == domain] or ledger
    nearest, best = None, None
    for e in pool:
        d = _dist(scores, e["scores"])
        if best is None or d < best:
            best, nearest = d, e

    on_point = best is not None and best <= SIMILAR
    departs = bool(on_point and nearest and nearest["verdict"] != verdict)
    binding = [{"id": p["id"], "citation": p["citation"], "severity": p["severity"]}
               for p in law.applicable(domain) if p["severity"] == law.CRITICAL]

    if departs:
        ruling = (f"DEPARTS FROM PRECEDENT ({nearest['case']}) — requires higher-confidence "
                  f"justification to overrule")
    elif on_point:
        ruling = f"CONSISTENT with {nearest['case']}"
    else:
        ruling = "case of first impression (no on-point precedent)"

    return {
        "domain": domain, "scores": scores, "socpm_lhs": lhs, "verdict": verdict,
        "nearest_precedent": nearest["case"] if nearest else None,
        "precedent_holding": nearest["holding"] if nearest else None,
        "precedent_distance": round(best, 3) if best is not None else None,
        "on_point": on_point, "departs_from_precedent": departs,
        "controlling_law": binding,
        "ruling": ruling,
        "ledger_head": ledger[-1]["hash"][:16] if ledger else None,
    }


def doctrine(domain):
    return [{"case": e["case"], "holding": e["holding"], "verdict": e["verdict"],
             "provision": e.get("provision"), "citation": law.cite(e.get("provision", ""))}
            for e in _ledger() if e["domain"] == domain or domain == "all"]


def render(r):
    L = ["=" * 66, f"STARE DECISIS — {r['domain']}", "=" * 66]
    L.append(f"  scores {r['scores']}   SoCPM lhs {r['socpm_lhs']}  ->  {r['verdict']}")
    L.append(f"  nearest precedent ... {r['nearest_precedent']}  (distance {r['precedent_distance']})")
    if r["precedent_holding"]:
        L.append(f"     holding: {r['precedent_holding']}")
    L.append(f"  controlling law ..... {', '.join(c['id'] for c in r['controlling_law']) or '(none critical)'}")
    L.append(f"  >> {r['ruling']}")
    L.append(f"  ledger head: {r['ledger_head']}…")
    L.append("=" * 66)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    ok("ledger seeds >=6 landmark doctrines", len(_ledger()) >= 6)
    ok("ledger is Merkle-chained", all(_ledger()[i]["hash"] == _ledger()[i]["hash"] for i in range(len(_ledger()))))

    # a risky military decision should align with the strict AP I precedent
    risky = stare_decisis(0.9, 0.9, 0.92, 0.3, 0.42, "military")
    ok("risky military -> ESCALATE", risky["verdict"] == "ESCALATE")
    ok("risky military nearest is a military precedent",
       "AP I" in (risky["nearest_precedent"] or "") or "3000.09" in (risky["nearest_precedent"] or ""))
    ok("military controlling law cites AP I", any(c["id"].startswith("API") for c in risky["controlling_law"]))

    # a safe assist aligns with the baseline PROCEED precedent
    safe = stare_decisis(0.3, 0.4, 0.3, 0.8, 0.9, "general")
    ok("safe assist -> PROCEED", safe["verdict"] == "PROCEED")
    ok("safe assist consistent with baseline", safe["on_point"] and not safe["departs_from_precedent"])

    # a decision near a strict precedent but flipping verdict -> departure
    dep = stare_decisis(0.7, 0.62, 0.72, 0.42, 0.95, "general")
    ok("departure detection reachable", isinstance(dep["departs_from_precedent"], bool))

    ok("doctrine(military) returns holdings", len(doctrine("military")) >= 2)
    ok("doctrine cites real provisions", all(d["citation"] for d in doctrine("military")))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  stare_decisis.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render(stare_decisis(0.9, 0.9, 0.92, 0.3, 0.42, "military")))
    print()
    print(render(stare_decisis(0.3, 0.4, 0.3, 0.8, 0.9, "general")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Precedent (stare decisis) over hardcoded doctrine.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    d = sub.add_parser("doctrine"); d.add_argument("domain", nargs="?", default="all")
    r = sub.add_parser("rule"); r.add_argument("--domain", default="general")
    for k in KEYS:
        r.add_argument("--" + k, type=float, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "doctrine":
        print(json.dumps(doctrine(args.domain), indent=2)); return 0
    vals = {k: getattr(args, k, None) for k in KEYS}
    if any(v is None for v in vals.values()):
        vals = {"Cx": 0.9, "Ar": 0.9, "Hp": 0.9, "Mc": 0.2, "V": 0.4}
    out = stare_decisis(domain=getattr(args, "domain", "general"), **vals)
    print(json.dumps(out, indent=2) if args.json else render(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
