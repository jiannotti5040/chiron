#!/usr/bin/env python3
"""
Collapse trace — show the whole reasoning path, not just the answer.

    python3 trace.py "1 1 2 3 5 8 13"        # a sequence
    python3 trace.py "WKLV LV D WHVW"        # a ciphertext
    python3 trace.py --json "2 4 8 16 32"

For a numeric surface it prints every candidate generator the engine considered,
ranked by description length, why the winner won, how it was verified against
held-out terms, and what residual (if any) it could not compress. For a string it
shows the ranked decodings the cipher solver weighed. The point is that you can
see the decision, disagree with it, and check it yourself.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import collapse, top_generators, solve_cipher  # noqa: E402


def _as_numbers(text):
    parts = str(text).replace(",", " ").split()
    try:
        vals = [float(p) for p in parts]
    except ValueError:
        return None
    if len(vals) < 3:
        return None
    return [int(v) if float(v).is_integer() else v for v in vals]


def _trace_sequence(seq):
    out = {"surface": "integer/rational sequence", "terms": len(seq)}
    cands = top_generators(seq, k=6)
    out["candidates"] = cands
    inv = collapse(seq)
    d = inv.to_dict()
    out["winner"] = {"model_class": d["model_class"], "verified": d["verified"],
                     "model_bits": d["model_bits"], "surface_bits": d["surface_bits"],
                     "compression_ratio": d["compression_ratio"],
                     "mdl_margin_bits": d["mdl_margin_bits"],
                     "explanation": d["explanation"]}
    # engine verdict on the full surface (its own internal held-out test)
    out["engine_verdict"] = "VERIFIED" if d["verified"] else "ABSTAINED"
    # independent re-test: hide the tail, retrain on the shorter prefix, predict it.
    # (A short prefix may be too small to re-verify on its own; what we report here
    # is purely whether the prediction of the hidden terms was correct.)
    h = max(1, min(3, len(seq) // 3))
    train = seq[:-h]
    held = _clean_terms(seq[-h:])
    check = {"held_out": held, "trained_on_count": len(train)}
    try:
        inv2 = collapse(train)
        pred = _clean_terms(inv2.predict(len(seq))[-h:])
        check["predicted"] = pred
        check["match"] = all(_eq(a, b) for a, b in zip(pred, held))
    except Exception as e:
        check["predicted"] = None
        check["match"] = False
        check["note"] = str(e)
    out["held_out_verification"] = check
    out["residual"] = _clean_terms(d["residual"])
    return out


def _clean_terms(xs):
    from fractions import Fraction
    out = []
    for x in xs:
        if isinstance(x, Fraction):
            out.append(x.numerator if x.denominator == 1 else float(x))
        else:
            out.append(x)
    return out


def _eq(a, b):
    try:
        from fractions import Fraction
        return Fraction(a) == Fraction(b)
    except Exception:
        return a == b


def _trace_string(text):
    out = {"surface": "string / ciphertext", "length": len(text)}
    sol = solve_cipher(text)
    out["decoding"] = sol
    inv = collapse(text)
    out["string_structure"] = {"model_class": inv.model_class,
                               "explanation": inv.explanation}
    return out


def _print_sequence(t):
    print("=" * 70)
    print("COLLAPSE TRACE")
    print("=" * 70)
    print("input parsed as: %s (%d terms)\n" % (t["surface"], t["terms"]))
    print("STEP 1 — candidate generators, ranked by description length")
    print("        (fewer bits = simpler explanation; the winner is the cheapest)")
    for i, c in enumerate(t["candidates"], 1):
        if "mdl_cost_bits" not in c:
            print("   #%d  %s  %s" % (i, c.get("model_class", "?"), c.get("note", "")))
            continue
        mark = "  <== WINNER" if c.get("is_winner") else ""
        print("   #%d  %-26s %8s bits   conf %.2f%s"
              % (i, c["model_class"], c["mdl_cost_bits"], c.get("confidence", 0.0), mark))
    w = t["winner"]
    print("\nSTEP 2 — why this winner")
    print("   model class ......... %s" % w["model_class"])
    print("   description length .. %s bits vs %s bits to list the raw terms"
          % (w["model_bits"], w["surface_bits"]))
    print("   compression ratio ... %sx" % w["compression_ratio"])
    margin = w["mdl_margin_bits"]
    print("   margin to runner-up . %s" % (
        "no competing model within the search" if margin and margin >= 999
        else "%s bits" % margin))
    c = t["held_out_verification"]
    print("\nSTEP 3 — verification (the honesty gate)")
    print("   engine verdict ...... %s" % t["engine_verdict"]
          + ("   (predicted its own held-out terms exactly)"
             if t["engine_verdict"] == "VERIFIED" else "   (no rule it could prove)"))
    print("   independent re-test:")
    print("      trained on ....... first %d terms" % c["trained_on_count"])
    print("      held out ......... %s" % c["held_out"])
    print("      predicted ........ %s" % c.get("predicted"))
    print("      result ........... %s" % ("predicted the hidden terms correctly"
                                           if c["match"] else "prediction missed -> would abstain"))
    print("\nSTEP 4 — residual (what it could not compress)")
    print("   %s" % ("none — fully explained" if not t["residual"] else t["residual"]))
    print("\nWHY:  %s" % w["explanation"])


def _print_string(t):
    print("=" * 70)
    print("COLLAPSE TRACE (string / ciphertext)")
    print("=" * 70)
    print("input length: %d\n" % t["length"])
    s = t["decoding"]
    print("STEP 1 — candidate decodings the solver weighed (by English-likeness)")
    print("   WINNER: %-14s  conf %.3f" % (s["method"], s["confidence"]))
    print("           -> %s" % s["plaintext"])
    for r in s.get("runners_up", []):
        print("   also:   %-14s  -> %s" % (r["method"], r["plaintext"]))
    print("\nSTEP 2 — string structure")
    print("   %s — %s" % (t["string_structure"]["model_class"],
                          t["string_structure"]["explanation"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surface", nargs="+", help="a sequence or a string/ciphertext")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    text = " ".join(args.surface)
    seq = _as_numbers(text)
    trace = _trace_sequence(seq) if seq is not None else _trace_string(text)
    if args.json:
        print(json.dumps(trace, indent=2, default=str))
        return 0
    (_print_sequence if seq is not None else _print_string)(trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
