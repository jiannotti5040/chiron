#!/usr/bin/env python3
"""
Structured intake (B-5b) — a general front door that normalizes a raw input into a
common, collapse/certify-ready record. A civilian generalization of JDICert's primer:
JSON, delimited numeric rows, or free text (with embedded-sequence extraction).

    python3 intake.py '{"signal":[1,2,4,8,16]}'
    python3 intake.py "1 2 4 8 16 32"
    python3 intake.py "the series 1 1 2 3 5 8 13 appears in the report"
    python3 intake.py --json "..."

Framing dial — civilian: multi-source data standardizer. Contractor: multi-feed
standardizer to a common decision schema.
"""
import os
import sys
import re
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron  # noqa: E402


def intake(raw):
    raw = str(raw).strip()
    rec = {"source": "intake", "format": None, "fields": {}, "series": [],
           "text": None, "embedded_sequences": []}
    # 1) JSON
    try:
        obj = json.loads(raw)
        rec["format"] = "json"
        if isinstance(obj, dict):
            rec["fields"] = obj
            for v in obj.values():
                if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v):
                    rec["series"].append(v)
        elif isinstance(obj, list) and all(isinstance(x, (int, float)) for x in obj):
            rec["series"].append(obj)
    except Exception:
        # 2) delimited numeric rows
        rows = [r for r in raw.splitlines() if r.strip()]
        numeric_rows = []
        for r in rows:
            toks = re.split(r"[,\s]+", r.strip())
            try:
                numeric_rows.append([float(t) for t in toks])
            except ValueError:
                numeric_rows = None
                break
        if numeric_rows:
            rec["format"] = "numeric"
            rec["series"] = numeric_rows
        else:
            # 3) free text — extract embedded sequences with the engine
            rec["format"] = "text"
            rec["text"] = raw
            try:
                ts = chiron.text_structure(raw)
                rec["embedded_sequences"] = ts.get("embedded_sequences", [])
            except Exception:
                pass
    rec["collapse_ready"] = bool(rec["series"]) or bool(rec["embedded_sequences"])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rec = intake(" ".join(args.raw))
    if args.json:
        print(json.dumps(rec, indent=2, default=str)); return 0
    print("intake format ...... %s" % rec["format"])
    print("collapse-ready ..... %s" % rec["collapse_ready"])
    if rec["series"]:
        print("series ............. %s" % (rec["series"][0][:10]))
    if rec["embedded_sequences"]:
        for e in rec["embedded_sequences"]:
            print("embedded ........... %s -> %s (verified=%s)"
                  % (e["sequence"], e["model_class"], e["verified"]))
    if rec["fields"]:
        print("fields ............. %s" % list(rec["fields"].keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
