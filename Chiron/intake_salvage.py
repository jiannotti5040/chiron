#!/usr/bin/env python3
"""
intake_salvage.py — fault-tolerant ingestion (Review 2: input rigidity).

intake.py is precise but strict: structured formats only, and it goes dead (not collapse-ready)
on raw, unstructured telemetry. This is an ADDITIVE wrapper that never alters a successful strict
parse, and only when the strict path produces a dead record does it salvage: it harvests every
numeric token from the raw input, in order, and attaches that as a collapse-ready series. The
salvage is deliberately honest — it harvests ALL numbers (timestamps and noise included) and lets
the downstream MDL collapse separate signal from noise; it does not pretend to know which numbers
are meaningful.

Public API: salvage(raw).

    python3 intake_salvage.py selftest
    python3 intake_salvage.py "ERR@node3 temps=20.1/20.5/21.0/22.3/19.8 ok"

Status: implemented & tested. Strict parses are never overwritten (gate-enforced).
"""
import os
import re
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import intake  # noqa: E402

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def harvest_numbers(raw):
    """Every numeric token in the raw input, in order. Pure stdlib, format-agnostic."""
    out = []
    for m in _NUM.findall(str(raw)):
        try:
            out.append(int(m) if "." not in m else float(m))
        except ValueError:
            pass
    return out


def salvage(raw, min_numbers=4):
    """Run strict intake; if it produced a collapse-ready record, return it UNCHANGED. Otherwise
    salvage a numeric series from the raw noise and mark the record salvaged (modest confidence)."""
    rec = intake.intake(raw)
    rec["salvaged"] = False
    if rec.get("collapse_ready"):
        return rec
    nums = harvest_numbers(raw)
    if len(nums) >= min_numbers:
        rec["salvaged"] = True
        rec["salvaged_series"] = nums
        rec["series"] = (rec.get("series") or []) + [nums]
        rec["collapse_ready"] = True
        rec["confidence"] = max(rec.get("confidence", 0.0), 0.4)
        if not rec.get("primary_series"):
            rec["primary_series"] = nums
        rec["note"] = ("strict parse found no structured series; salvaged all numeric tokens in "
                       "order (timestamps/noise included) for downstream MDL collapse")
    return rec


def _ordered_subseq(sub, seq):
    it = iter(seq)
    return all(any(x == y for y in it) for x in sub)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    clean_num = salvage("1 2 4 8 16 32")
    ok("clean numeric parse is not salvaged", clean_num["salvaged"] is False and clean_num["format"] == "numeric")
    clean_json = salvage('{"signal":[1,2,4,8,16]}')
    ok("clean json parse is not salvaged", clean_json["salvaged"] is False)
    ok("good parse keeps its verdict (collapse-ready)", clean_num["collapse_ready"])

    messy = salvage("ERR@node3 :: temps=20.1/20.5/21.0/22.3/19.8 ;; ok")
    ok("messy telemetry is salvaged", messy["salvaged"] is True)
    ok("salvage makes it collapse-ready", messy["collapse_ready"])
    ok("salvaged temps appear in order",
       _ordered_subseq([20.1, 20.5, 21.0, 22.3, 19.8], messy["salvaged_series"]))

    glued = salvage("rec#1 val=12.5|33|7|9|4 ;flag=on")
    ok("numbers harvested from glued noise", glued["salvaged"] and len(glued["salvaged_series"]) >= 4)

    ok("harvest is honest (timestamps included)",
       set([2024, 1, 1]).issubset(set(harvest_numbers("[2024-01-01] 1 1 2 3"))))
    ok("too-few-numbers stays dead", salvage("only one number 7 here").get("salvaged") is False)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  intake_salvage.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fault-tolerant ingestion over strict intake.")
    ap.add_argument("raw", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest or not args.raw:
        return 0 if _selftest() else 1
    rec = salvage(" ".join(args.raw))
    print(json.dumps(rec, indent=2, default=str) if args.json else
          f"format={rec['format']} salvaged={rec['salvaged']} collapse_ready={rec['collapse_ready']} "
          f"primary_series={rec.get('primary_series')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
