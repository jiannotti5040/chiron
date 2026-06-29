#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
actionable_intelligence.py — turn a recovered law into a decision-ready brief.

The generative property made useful. Chiron recovers the exact law beneath a codified surface;
this turns that law into ACTIONABLE INTELLIGENCE — what a person can act on:

  WHAT IT IS        the recovered law, in plain words
  WHAT'S NEXT       the law run forward — a forecast (only when the law verified)
  WHAT'S WRONG      the exact entries that violate the law (zero false positives)
  HOW SURE + WHY    held-out proof, compression, and what would falsify it
  WHERE FROM        the generator's identity fingerprint (origin / provenance)
  WHAT TO DO        a governed recommendation: PROCEED / ESCALATE / REJECT

The discipline that makes it trustworthy: when there is no law, it ABSTAINS instead of inventing
an alert. An alerting system with zero false positives is the thing analysts cannot get from
statistical tools.

Public API (consumed elsewhere): brief(surface).

    python3 actionable_intelligence.py selftest
    python3 actionable_intelligence.py brief 100 107 114 121 128 135 142
    python3 actionable_intelligence.py batch "2 4 6 8 10" "1 1 2 3 5 8 13 99 34 55"

Framing dial — civilian: anomaly + forecast + decision assurance over any structured stream.
Contractor: signal-law extraction, exact deviation/tamper detection, governed call.
"""
import os
import sys
import json
import argparse
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import govern as _governance  # noqa: E402

INCOMPRESSIBLE = ("incompressible", "general", "random")


def _clean(xs):
    out = []
    for x in xs:
        if isinstance(x, Fraction):
            out.append(int(x) if x.denominator == 1 else float(x))
        elif isinstance(x, float) and x.is_integer():
            out.append(int(x))
        else:
            out.append(x)
    return out


def _law_found(inv):
    return inv.model_class not in INCOMPRESSIBLE


def _reference_law(surface):
    n = len(surface)
    full = chiron.collapse(surface)
    if full.verified and not full.residual and _law_found(full):
        return full, n, True
    for w in range(n - 1, 3, -1):
        inv = chiron.collapse(surface[:w])
        if _law_found(inv):
            expected = _clean(inv.predict(w))
            if expected == list(surface[:w]):
                return inv, w, bool(inv.verified)
    return full, n, bool(full.verified)


def brief(surface, stakes=None, horizon=3, label=None, domain="general"):
    surface = list(surface)
    ref, window, verified = _reference_law(surface)
    found = _law_found(ref)

    out = {"label": label, "n": len(surface)}
    plain = ref.explanation.split(". ")[0].rstrip(".") + "." if ref.explanation else ""
    out["what_it_is"] = {"law": ref.model_class, "plain": plain,
                         "exact_arithmetic": bool(ref.exact), "verified_on_heldout": bool(verified)}

    expected = _clean(ref.predict(len(surface))) if found else []
    anomalies = [{"index": i, "observed": surface[i], "law_predicts": expected[i]}
                 for i in range(len(surface)) if found and i < len(expected) and surface[i] != expected[i]]
    out["whats_wrong"] = ({"anomalies": anomalies, "clean_window": window,
                           "method": "deviation from the law recovered on the clean leading window"}
                          if found else
                          {"anomalies": [], "note": "no law recovered — exact anomaly detection is not defined"})

    if found and not anomalies:
        fc = _clean(ref.predict(len(surface) + horizon))[len(surface):]
        out["whats_next"] = {"forecast": fc, "horizon": horizon}
    elif found and anomalies:
        out["whats_next"] = {"forecast_withheld": True,
                             "reason": "stream violates its own law; clear anomalies before forecasting"}
    else:
        out["whats_next"] = {"abstain": True,
                             "reason": "no law found; do not forecast (a general compressor is the right tool)"}

    out["confidence"] = {"verified_on_heldout": bool(verified),
                         "compression_ratio": round(float(ref.compression_ratio), 3),
                         "margin": round(float(ref.margin), 3) if ref.margin != 999.0 else "decisive",
                         "what_would_falsify": "a single held-out element the law fails to reproduce exactly"}
    out["provenance"] = {"generator_fingerprint": ref.generator_fingerprint[:16],
                         "note": "same-origin attribution across sources available via twins / origin-signatures"}

    V = 0.9 if verified else (0.6 if found else 0.25)
    st = {"Cx": 0.6, "Ar": 0.7, "Hp": 0.5, "Mc": 0.6}
    if stakes:
        st.update(stakes)
    g = _governance.govern(Cx=st["Cx"], Ar=st["Ar"], Hp=st["Hp"], Mc=st["Mc"], V=V, domain=domain,
                           context={"human_in_loop": True, "authority_present": True, "within_roe": True})
    if not found:
        verdict = "REJECT_INPUT — no structure; insufficient basis to act"
    elif anomalies:
        verdict = "ESCALATE — anomaly against the governing law"
    elif g["verdict"].startswith(("ESCALATE", "REJECT")):
        verdict = "ESCALATE — governance gate"
    else:
        verdict = "PROCEED — lawful, verified, in-policy"
    out["recommendation"] = {"verdict": verdict, "evidence_quality_V": V, "governance": g["verdict"]}
    return out


def batch(surfaces):
    rows = []
    for s in surfaces:
        vals = [int(x) if x.lstrip("-").isdigit() else float(x) for x in s.replace(",", " ").split()]
        b = brief(vals)
        rows.append({"surface": s, "law": b["what_it_is"]["law"],
                     "anomalies": len(b["whats_wrong"].get("anomalies", [])),
                     "verdict": b["recommendation"]["verdict"].split(" —")[0]})
    return rows


def render(b):
    L = ["=" * 64, "ACTIONABLE INTELLIGENCE BRIEF" + (f" — {b['label']}" if b.get("label") else ""), "=" * 64]
    w = b["what_it_is"]
    L.append("WHAT IT IS"); L.append(f"  {w['plain']}")
    L.append(f"  law={w['law']}  exact={w['exact_arithmetic']}  verified={w['verified_on_heldout']}")
    n = b["whats_next"]; L.append("WHAT'S NEXT")
    if "forecast" in n:
        L.append(f"  forecast (+{n['horizon']}): {n['forecast']}")
    elif n.get("forecast_withheld"):
        L.append(f"  withheld — {n['reason']}")
    else:
        L.append(f"  ABSTAIN — {n['reason']}")
    ww = b["whats_wrong"]; L.append("WHAT'S WRONG")
    if ww.get("anomalies"):
        for a in ww["anomalies"]:
            L.append(f"  ANOMALY @ index {a['index']}: observed {a['observed']}, law predicts {a['law_predicts']}")
    else:
        L.append("  none — every entry obeys the recovered law" if "note" not in ww else f"  {ww['note']}")
    c = b["confidence"]; L.append("HOW SURE + WHY")
    L.append(f"  verified={c['verified_on_heldout']}  compression={c['compression_ratio']}x  margin={c['margin']}")
    r = b["recommendation"]; L.append("WHAT TO DO"); L.append(f"  >> {r['verdict']}")
    L.append("=" * 64)
    return "\n".join(L)


_DEMOS = [
    ("operations — daily throughput, lawful", [100, 107, 114, 121, 128, 135, 142], {"Hp": 0.4, "Mc": 0.7}),
    ("audit — ledger with one tampered entry", [1, 1, 2, 3, 5, 8, 13, 99, 34, 55], {"Hp": 0.85, "Mc": 0.4}),
    ("intake — structureless feed", [41, 19, 50, 83, 6, 9, 68, 12, 46, 74], {"Hp": 0.7, "Mc": 0.5}),
]


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    lawful = brief([100, 107, 114, 121, 128, 135, 142])
    ok("lawful stream forecasts", "forecast" in lawful["whats_next"])
    ok("lawful forecast continues arithmetic", lawful["whats_next"]["forecast"][:1] == [149])
    ok("lawful -> PROCEED", lawful["recommendation"]["verdict"].startswith("PROCEED"))
    ok("lawful no anomalies", not lawful["whats_wrong"]["anomalies"])

    tamper = brief([1, 1, 2, 3, 5, 8, 13, 99, 34, 55])
    ok("tamper flags exactly one anomaly", len(tamper["whats_wrong"]["anomalies"]) == 1)
    ok("anomaly at index 7", tamper["whats_wrong"]["anomalies"][0]["index"] == 7)
    ok("tamper -> ESCALATE", tamper["recommendation"]["verdict"].startswith("ESCALATE"))
    ok("tamper withholds forecast", tamper["whats_next"].get("forecast_withheld"))

    noise = brief([41, 19, 50, 83, 6, 9, 68, 12, 46, 74])
    ok("noise abstains", noise["whats_next"].get("abstain"))
    ok("noise -> REJECT", noise["recommendation"]["verdict"].startswith("REJECT"))

    b = batch(["2 4 6 8 10", "1 1 2 3 5 8 13 99 34 55"])
    ok("batch returns rows", len(b) == 2 and b[1]["anomalies"] == 1)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  actionable_intelligence.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for label, surf, stakes in _DEMOS:
        print(render(brief(surf, stakes=stakes, label=label)))
        print()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Decision-ready intelligence brief over a structured stream.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    br = sub.add_parser("brief"); br.add_argument("values", nargs="+"); br.add_argument("--horizon", type=int, default=3)
    bt = sub.add_parser("batch"); bt.add_argument("surfaces", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "batch":
        print(json.dumps(batch(args.surfaces), indent=2)); return 0
    if args.cmd == "brief":
        vals = [int(x) if x.lstrip("-").isdigit() else float(x) for x in args.values]
        b = brief(vals, horizon=args.horizon)
        print(json.dumps(b, indent=2) if args.json else render(b)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
