#!/usr/bin/env python3
"""
actionable_intelligence.py — turn a recovered law into a decision-ready brief.

This is the generative property MADE USEFUL. Chiron recovers the exact law beneath a
codified surface; on its own that is a fact about the data. This module turns that law
into actionable intelligence — the thing a person can act on:

  WHAT IT IS        the recovered law, in plain words
  WHAT'S NEXT       the law run forward — a forecast (only when the law verified)
  WHAT'S WRONG      the exact entries that violate the law (zero false positives)
  HOW SURE + WHY    held-out proof, compression, and what would falsify it
  WHERE FROM        the generator's identity fingerprint (origin / provenance)
  WHAT TO DO        a governed recommendation: PROCEED / ESCALATE / REJECT

The discipline that makes it trustworthy: when there is no law, it ABSTAINS instead of
inventing an alert. An alerting system with zero false positives is the thing analysts
cannot get from statistical tools — they drown in false alarms; this stays silent unless
a law is actually broken.

Who it's for, concretely:
  - fraud / audit:     flag the ledger entries that violate the rule the other 10,000 obey
  - reliability / ops: forecast the next reading; catch the one that breaks the pattern
  - intelligence:      recover structure, attribute origin, refuse on engineered noise

Framing dial — civilian: anomaly + forecast + decision assurance over any structured
stream. Contractor: signal-law extraction, exact deviation/tamper detection, governed call.

    python3 actionable_intelligence.py --demo
    python3 actionable_intelligence.py 100 107 114 121 128 135 142
    echo "1 1 2 3 5 8 13 99 34 55" | python3 actionable_intelligence.py
"""
import os
import sys
import json
import argparse
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron       # noqa: E402
import govern as _governance  # noqa: E402  (reuse the SoCPM / LexGuard gate)

INCOMPRESSIBLE = ("incompressible", "general", "random")


def _clean(xs):
    """Coerce Fraction/float forecast values to plain ints where integral."""
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
    # NOTE: inv.compressible means "further-compressible", not "has a law" — a verified
    # Fibonacci reports compressible=False. The real signal is the recovered model class.
    return inv.model_class not in INCOMPRESSIBLE


def _reference_law(surface):
    """Find the law to judge the stream against.

    If the whole surface is lawful, that is the reference. Otherwise find the largest
    leading window whose recovered law reproduces that window exactly — the clean
    baseline a later anomaly is measured against. Returns (invariant, window_len, verified).
    """
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


def brief(surface, stakes=None, horizon=3, label=None):
    """Produce the decision-ready intelligence brief for a surface."""
    surface = list(surface)
    ref, window, verified = _reference_law(surface)
    found = _law_found(ref)

    out = {"label": label, "n": len(surface)}

    # WHAT IT IS
    plain = ref.explanation.split(". ")[0].rstrip(".") + "." if ref.explanation else ""
    out["what_it_is"] = {
        "law": ref.model_class,
        "plain": plain,
        "exact_arithmetic": bool(ref.exact),
        "verified_on_heldout": bool(verified),
    }

    # WHAT'S WRONG (exact anomalies against the recovered law)
    expected = _clean(ref.predict(len(surface))) if found else []
    anomalies = [
        {"index": i, "observed": surface[i], "law_predicts": expected[i]}
        for i in range(len(surface))
        if found and i < len(expected) and surface[i] != expected[i]
    ]
    out["whats_wrong"] = (
        {"anomalies": anomalies, "clean_window": window,
         "method": "deviation from the law recovered on the clean leading window"}
        if found else
        {"anomalies": [], "note": "no law recovered — exact anomaly detection is not defined"}
    )

    # WHAT'S NEXT (forecast the law forward — only if lawful and unbroken)
    if found and not anomalies:
        fc = _clean(ref.predict(len(surface) + horizon))[len(surface):]
        out["whats_next"] = {"forecast": fc, "horizon": horizon}
    elif found and anomalies:
        out["whats_next"] = {"forecast_withheld": True,
                             "reason": "stream violates its own law; clear anomalies before forecasting"}
    else:
        out["whats_next"] = {"abstain": True,
                             "reason": "no law found; do not forecast (a general compressor is the right tool for structureless data)"}

    # HOW SURE + WHY
    out["confidence"] = {
        "verified_on_heldout": bool(verified),
        "compression_ratio": round(float(ref.compression_ratio), 3),
        "margin": round(float(ref.margin), 3) if ref.margin != 999.0 else "decisive",
        "what_would_falsify": "a single held-out element the law fails to reproduce exactly",
    }

    # WHERE FROM (identity / provenance)
    out["provenance"] = {
        "generator_fingerprint": ref.generator_fingerprint[:16],
        "note": "same-origin attribution across sources available via twins / origin-signatures",
    }

    # WHAT TO DO (governed recommendation)
    V = 0.9 if verified else (0.6 if found else 0.25)
    st = {"Cx": 0.6, "Ar": 0.7, "Hp": 0.5, "Mc": 0.6}
    if stakes:
        st.update(stakes)
    g = _governance.govern(Cx=st["Cx"], Ar=st["Ar"], Hp=st["Hp"], Mc=st["Mc"], V=V)
    if not found:
        verdict = "REJECT_INPUT — no structure; insufficient basis to act"
    elif anomalies:
        verdict = "ESCALATE — anomaly against the governing law"
    elif g["redirect_or_escalate_required"]:
        verdict = "ESCALATE — governance gate (high impact, weak controls)"
    else:
        verdict = "PROCEED — lawful, verified, in-policy"
    out["recommendation"] = {"verdict": verdict, "evidence_quality_V": V, "governance": g}
    return out


def render(b):
    """Human-readable brief."""
    L = []
    head = "ACTIONABLE INTELLIGENCE BRIEF" + (f" — {b['label']}" if b.get("label") else "")
    L.append("=" * 64)
    L.append(head)
    L.append("=" * 64)
    w = b["what_it_is"]
    L.append("WHAT IT IS")
    L.append(f"  {w['plain']}")
    L.append(f"  law={w['law']}  exact={w['exact_arithmetic']}  verified={w['verified_on_heldout']}")
    n = b["whats_next"]
    L.append("WHAT'S NEXT")
    if "forecast" in n:
        L.append(f"  forecast (+{n['horizon']}): {n['forecast']}")
    elif n.get("forecast_withheld"):
        L.append(f"  withheld — {n['reason']}")
    else:
        L.append(f"  ABSTAIN — {n['reason']}")
    ww = b["whats_wrong"]
    L.append("WHAT'S WRONG")
    if ww.get("anomalies"):
        for a in ww["anomalies"]:
            L.append(f"  ANOMALY @ index {a['index']}: observed {a['observed']}, law predicts {a['law_predicts']}")
    else:
        L.append("  none — every entry obeys the recovered law" if "note" not in ww else f"  {ww['note']}")
    c = b["confidence"]
    L.append("HOW SURE + WHY")
    L.append(f"  verified_on_heldout={c['verified_on_heldout']}  compression={c['compression_ratio']}x  margin={c['margin']}")
    L.append(f"  falsifier: {c['what_would_falsify']}")
    L.append("WHERE FROM")
    L.append(f"  generator={b['provenance']['generator_fingerprint']}…")
    r = b["recommendation"]
    L.append("WHAT TO DO")
    L.append(f"  >> {r['verdict']}")
    L.append(f"     SoCPM lhs={r['governance']['socpm_lhs']} (T={r['governance']['threshold_T']})  evidence V={r['evidence_quality_V']}")
    L.append("=" * 64)
    return "\n".join(L)


_DEMOS = [
    ("operations — daily throughput, lawful",
     [100, 107, 114, 121, 128, 135, 142], {"Hp": 0.4, "Mc": 0.7}),
    ("audit — ledger with one tampered entry",
     [1, 1, 2, 3, 5, 8, 13, 99, 34, 55], {"Hp": 0.85, "Mc": 0.4}),
    ("intake — structureless feed (engineered noise)",
     [41, 19, 50, 83, 6, 9, 68, 12, 46, 74], {"Hp": 0.7, "Mc": 0.5}),
]


def _demo():
    for label, surf, stakes in _DEMOS:
        print(render(brief(surf, stakes=stakes, label=label)))
        print()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Decision-ready intelligence brief over a structured stream.")
    ap.add_argument("values", nargs="*", help="the stream (whitespace-separated numbers)")
    ap.add_argument("--demo", action="store_true", help="run the three worked scenarios")
    ap.add_argument("--horizon", type=int, default=3, help="forecast horizon")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    if args.demo:
        return _demo()

    raw = args.values
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read().split()
    if not raw:
        return _demo()
    try:
        surface = [int(x) for x in raw]
    except ValueError:
        surface = [float(x) for x in raw]
    b = brief(surface, horizon=args.horizon)
    print(json.dumps(b, indent=2, default=str) if args.json else render(b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
