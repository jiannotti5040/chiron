#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
oeis_live.py — external validation against the live OEIS.

The internal benchmark (benchmark.py) grades the engine on sequences it
generated for itself. This harness removes that self-reference: the terms
come from oeis.org — data the engine's author did not produce — and the
grade is exact prediction of terms the engine never saw.

Protocol (identical spirit to benchmark.py, external data):
  1. The engine sees the first SHOW=12 terms of each sequence.
  2. `collapse` recovers a rule (with its own internal held-out check).
  3. The recovered rule predicts terms 13..16; they are compared EXACTLY
     against the OEIS values.
  4. Grades:  VERIFIED+correct   — stamped and externally right
              VERIFIED+WRONG     — stamped and externally wrong (false
                                   confidence; the one unacceptable cell)
              recovered-unstamped — right continuation, conservatively
                                   not stamped
              declined            — engine refused; correct behavior for
                                   sequences outside its hypothesis classes

Data source, in order of preference:
  --cache FILE   a corpus cache JSON (default: oeis_corpus_cache.json beside
                 this script — the live-fetched 2026-07-04 snapshot)
  --live         fetch fresh terms from oeis.org b-files (needs network);
                 polite UA, ~1 request/s. Use this on your own machine to
                 re-verify against today's OEIS.
  --keyword-core with --live: pull the full keyword:core corpus from the
                 OEIS search API instead of the fixed A-number list.

Usage:
  python3 oeis_live.py                # run against the cached live snapshot
  python3 oeis_live.py --live         # re-fetch every sequence, then run
  python3 oeis_live.py --live --keyword-core --limit 200
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse  # noqa: E402

SHOW = 12        # terms the engine is allowed to see (standard tier)
DEEP_SHOW = 24   # deep tier: parameter-rich rules (12-unknown P-recurrences)
                 # cannot even form on 12 terms — rows >= unknowns + 1 needs
                 # more evidence. Marked per-sequence via protocol: "deep".
GRADE = 4        # held-out terms it must predict exactly (both tiers)
UA = "primus-oeis-live-harness/0.1 (+https://github.com/jiannotti5040/Jacob-s-Portfolio-Vault; jiannotti5040@gmail.com)"


# ----------------------------------------------------------------- fetching
def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def fetch_bfile(anum: str) -> list:
    """First ~40 terms from the sequence's b-file (static, bot-friendly)."""
    txt = _get(f"https://oeis.org/{anum}/b{anum[1:]}.txt")
    terms = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                terms.append(int(parts[1]))
            except ValueError:
                continue
        if len(terms) >= 40:
            break
    return terms


def fetch_keyword_core(limit: int) -> dict:
    """Full keyword:core corpus via the OEIS search API (JSON, paged by 10)."""
    out, start = {}, 0
    while len(out) < limit:
        j = json.loads(_get(
            f"https://oeis.org/search?q=keyword:core&fmt=json&start={start}"))
        results = j.get("results") or []
        if not results:
            break
        for r in results:
            anum = f"A{r['number']:06d}"
            terms = [int(x) for x in r["data"].split(",")]
            out[anum] = {"name": r.get("name", ""), "terms": terms,
                         "class_prior": "unlabeled (keyword:core)"}
        start += len(results)
        time.sleep(1.0)  # be polite
    return out


# ------------------------------------------------------------------ grading
def grade_one(anum: str, meta: dict) -> dict:
    terms = meta["terms"]
    show = DEEP_SHOW if meta.get("protocol") == "deep" else SHOW
    if len(terms) < show + GRADE:
        return {"anum": anum, "grade": "skipped (too few terms)", **meta}
    shown, held = terms[:show], terms[show:show + GRADE]
    res = {"anum": anum, "name": meta.get("name", ""),
           "protocol": meta.get("protocol", "standard"),
           "class_prior": meta.get("class_prior", "")}
    try:
        inv = collapse(shown)
    except Exception as exc:
        res.update(grade="declined", detail=f"engine declined ({type(exc).__name__})")
        return res
    res["model_class"] = inv.model_class
    predicted = None
    try:
        raw_pred = inv.predict(show + GRADE)[show:]
        predicted = [x if isinstance(x, int) else round(float(x)) for x in raw_pred]
    except Exception:
        pass
    ext_correct = predicted == held
    if inv.verified:
        res["grade"] = "VERIFIED+correct" if ext_correct else "VERIFIED+WRONG"
    elif ext_correct:
        res["grade"] = "recovered-unstamped"
    else:
        res["grade"] = "declined"
    if predicted is not None and not ext_correct:
        res["predicted"] = predicted
        res["expected"] = held
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--cache", default=os.path.join(_HERE, "oeis_corpus_cache.json"))
    ap.add_argument("--live", action="store_true", help="fetch fresh from oeis.org")
    ap.add_argument("--keyword-core", action="store_true",
                    help="with --live: use the full keyword:core corpus")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--json", action="store_true", help="emit JSON results")
    args = ap.parse_args(argv)

    if args.live and args.keyword_core:
        corpus = fetch_keyword_core(args.limit)
    else:
        with open(args.cache, "r") as f:
            corpus = json.load(f)["sequences"]
        if args.live:
            for anum in corpus:
                corpus[anum]["terms"] = fetch_bfile(anum)
                time.sleep(1.0)

    results = [grade_one(a, m) for a, m in sorted(corpus.items())]
    graded = [r for r in results if not r["grade"].startswith("skipped")]
    n = len(graded)
    counts = {}
    for r in graded:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    stamped = counts.get("VERIFIED+correct", 0) + counts.get("VERIFIED+WRONG", 0)
    false_conf = counts.get("VERIFIED+WRONG", 0)

    if args.json:
        print(json.dumps({"protocol": {"show": SHOW, "grade": GRADE},
                          "counts": counts, "n": n, "results": results},
                         indent=2))
    else:
        print(f"OEIS LIVE VALIDATION — engine sees {SHOW} terms, "
              f"graded on exact prediction of the next {GRADE} (external data)\n")
        for r in graded:
            tag = ' [deep]' if r.get('protocol') == 'deep' else ''
            line = f"  {r['anum']}  {r['grade']:20s} {r.get('model_class','-'):28s} {r['name'][:40]}{tag}"
            print(line)
            if "predicted" in r:
                print(f"          predicted {r['predicted']} expected {r['expected']}")
        print(f"\n  n={n}   " + "   ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
        print(f"  stamped VERIFIED: {stamped}   false confidence (VERIFIED+WRONG): {false_conf}")
        print("  RESULT:", "PASS — zero false verifications"
              if false_conf == 0 else "FAIL — the engine stamped a wrong rule")
    return 1 if false_conf else 0


if __name__ == "__main__":
    raise SystemExit(main())
