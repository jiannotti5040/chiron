#!/usr/bin/env python3
"""
jurisdiction.py — the boundary geometry of the admissible, per domain (A-2, hardened).

The threshold for acceptable autonomous action is not universal — it moves with the domain,
and so does the body of law that binds it. A medical diagnosis has a tiny admissible region and
is governed by HIPAA, the FDA QSR, and the EU MDR; a use-of-force decision has the smallest
region of all and is governed by Additional Protocol I, the Geneva Conventions, and DoDD
3000.09; a creative draft has a large region and almost no binding instrument. jurisdiction
makes both explicit: each domain sets its own SoCPM threshold T and emphasis, AND pulls its
actual governing instruments from legal_corpus.py. The same scores yield different verdicts —
and different controlling law — under different jurisdictions.

    python3 jurisdiction.py selftest
    python3 jurisdiction.py compare --Cx 0.6 --Ar 0.7 --Hp 0.7 --Mc 0.6 --V 0.7
    python3 jurisdiction.py binding military
    python3 jurisdiction.py judge --domain medical --Cx 0.6 --Ar 0.7 --Hp 0.7 --Mc 0.6 --V 0.7

Framing dial — civilian: domain-specific duty-of-care threshold + controlling-law index.
Contractor: per-mission ROE envelope with the law-of-armed-conflict instruments attached.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import legal_corpus as law  # noqa: E402

KEYS = ("Cx", "Ar", "Hp", "Mc", "V")

# T = admissibility threshold (lower = stricter), emphasis = score multipliers, character note.
JURISDICTIONS = {
    "military":       {"T": 0.05, "emphasis": {"Hp": 1.5, "Ar": 1.2}, "note": "use of force — smallest admissible region"},
    "medical":        {"T": 0.10, "emphasis": {"Hp": 1.3, "Mc": 1.2}, "note": "diagnosis/treatment — very small region"},
    "law_enforcement": {"T": 0.12, "emphasis": {"Hp": 1.3}, "note": "policing/surveillance — small region, rights-sensitive"},
    "financial":      {"T": 0.20, "emphasis": {"Hp": 1.1}, "note": "trades/credit — moderate region"},
    "general":        {"T": 0.25, "emphasis": {}, "note": "baseline duty of care"},
    "creative":       {"T": 0.60, "emphasis": {}, "note": "writing/design — large admissible region"},
}


def _clamp(x):
    return max(0.0, min(1.0, x))


def binding(domain):
    """The actual governing instruments for a domain, from the hardcoded corpus."""
    provs = law.applicable(domain)
    return {
        "domain": domain,
        "provisions": len(provs),
        "critical": [p["id"] + " — " + p["citation"] for p in provs if p["severity"] == law.CRITICAL],
        "instruments": sorted({p["instrument"] for p in provs}),
    }


def judge(domain, Cx, Ar, Hp, Mc, V):
    cfg = JURISDICTIONS.get(domain, JURISDICTIONS["general"])
    em = cfg["emphasis"]
    raw = {"Cx": Cx, "Ar": Ar, "Hp": Hp, "Mc": Mc, "V": V}
    adj = {k: _clamp(raw[k] * em.get(k, 1.0)) for k in KEYS}
    lhs = adj["Cx"] * adj["Ar"] * adj["Hp"] - adj["Mc"] * (1.0 - adj["V"])
    redirect = lhs > cfg["T"]
    b = binding(domain)
    return {
        "domain": domain,
        "threshold_T": cfg["T"],
        "note": cfg["note"],
        "raw_scores": raw,
        "adjusted_scores": {k: round(adj[k], 3) for k in KEYS},
        "socpm_lhs": round(float(lhs), 4),
        "verdict": "ESCALATE / REDIRECT" if redirect else "PROCEED",
        "governing_instruments": b["instruments"],
        "critical_provisions": b["critical"],
    }


def compare(Cx, Ar, Hp, Mc, V):
    return [judge(d, Cx, Ar, Hp, Mc, V) for d in JURISDICTIONS]


def render_compare(rows):
    L = ["=" * 70, "JURISDICTION — same scores, different admissible regions + law", "=" * 70]
    L.append("  %-15s %6s %9s   %-20s %s" % ("domain", "T", "lhs", "verdict", "#critical-laws"))
    for r in rows:
        L.append("  %-15s %6s %9s   %-20s %d" % (
            r["domain"], r["threshold_T"], r["socpm_lhs"], r["verdict"], len(r["critical_provisions"])))
    L.append("=" * 70)
    return "\n".join(L)


def render(r):
    L = ["=" * 64, f"JURISDICTION — {r['domain']}", "=" * 64]
    L.append(f"  {r['note']}")
    L.append(f"  threshold T = {r['threshold_T']}   SoCPM lhs {r['socpm_lhs']}  ->  {r['verdict']}")
    L.append(f"  governing instruments ({len(r['governing_instruments'])}): {', '.join(r['governing_instruments'][:6])}…")
    if r["critical_provisions"]:
        L.append("  CRITICAL provisions in force:")
        for c in r["critical_provisions"][:6]:
            L.append(f"     - {c}")
    L.append("=" * 64)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    rows = compare(0.6, 0.7, 0.7, 0.6, 0.7)
    mil = next(r for r in rows if r["domain"] == "military")
    cre = next(r for r in rows if r["domain"] == "creative")
    ok("military ESCALATEs where creative PROCEEDs (same scores)",
       mil["verdict"].startswith("ESCALATE") and cre["verdict"] == "PROCEED")
    ok("military has more critical law than creative",
       len(mil["critical_provisions"]) > len(cre["critical_provisions"]))
    ok("military binds Additional Protocol I", any("Additional Protocol" in i for i in mil["governing_instruments"]))
    ok("medical binds HIPAA", any("HIPAA" in i for i in binding("medical")["instruments"]))
    ok("financial binds Market Abuse Regulation", any("Market Abuse" in i for i in binding("financial")["instruments"]))
    ok("threshold ordering military<medical<general<creative",
       JURISDICTIONS["military"]["T"] < JURISDICTIONS["medical"]["T"] < JURISDICTIONS["general"]["T"] < JURISDICTIONS["creative"]["T"])
    ok("creative binds no armed-conflict law", not any("Protocol" in i or "Geneva" in i for i in binding("creative")["instruments"]))
    ok("every jurisdiction has >=1 instrument", all(binding(d)["provisions"] >= 1 for d in JURISDICTIONS))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  jurisdiction.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render_compare(compare(0.6, 0.7, 0.7, 0.6, 0.7)))
    print()
    print(render(judge("military", 0.6, 0.7, 0.7, 0.6, 0.7)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Domain-scaled admissibility + controlling law.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    b = sub.add_parser("binding"); b.add_argument("domain")
    for name in ("compare", "judge"):
        c = sub.add_parser(name)
        c.add_argument("--domain", default="general")
        for k in KEYS:
            c.add_argument("--" + k, type=float, default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "binding":
        print(json.dumps(binding(args.domain), indent=2)); return 0
    vals = {k: getattr(args, k, None) for k in KEYS}
    if any(v is None for v in vals.values()):
        vals = {"Cx": 0.6, "Ar": 0.7, "Hp": 0.7, "Mc": 0.6, "V": 0.7}
    if args.cmd == "compare":
        rows = compare(**vals)
        print(json.dumps(rows, indent=2) if args.json else render_compare(rows))
        return 0
    r = judge(getattr(args, "domain", "general"), **vals)
    print(json.dumps(r, indent=2) if args.json else render(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
