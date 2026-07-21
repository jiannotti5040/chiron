#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
grade.py — verify the engine's zero-false-verification claim yourself,
without the engine.

This grader takes the FROZEN engine outputs shipped in this folder
(frozen_predictions.json: for each public OEIS sequence, either exact
predictions for terms 13..20 made from the first 12 terms only, or a
refusal), fetches ground truth, and counts FALSE STAMPS — stamped
predictions that external data contradicts. The claim under test: that
count is zero.

Ground truth, your choice:
  default          fetch b-files LIVE from oeis.org (needs network; polite,
                   ~1 request/second). oeis.org is not controlled by the
                   engine's author — this is the strong mode.
  --cache FILE     a pinned public snapshot (one ships in this folder with
                   its fetch date; useful offline/CI, weaker than live).

Buyer-challenge mode (see challenge.py — sequences YOU choose):
  python3 grade.py --challenge challenge.json --answers answers.json

Stdlib only. No engine code is present in this folder; zero-false is a
property of outputs, and outputs are what you are grading.

    python3 grade.py                 # live grade of the frozen predictions
    python3 grade.py --cache oeis_snapshot_2026-07-07.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
UA = "chiron-public-eval-grader/1.0 (+https://github.com/jiannotti5040/chiron)"


def fetch_bfile_terms(anum: str, limit: int = 40) -> list:
    url = f"https://oeis.org/{anum}/b{anum[1:]}.txt"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read().decode("utf-8", "replace")
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
        if len(terms) >= limit:
            break
    return terms


def load_truth(args, anums):
    if args.cache:
        with open(args.cache) as f:
            blob = json.load(f)
        prov = blob.get("_provenance", {})
        print(f"ground truth: pinned snapshot {os.path.basename(args.cache)}"
              + (f"  (provenance: {json.dumps(prov)[:100]})" if prov else ""))
        return {a: m["terms"] for a, m in blob["sequences"].items()}
    print("ground truth: LIVE from oeis.org (b-files, ~1 req/s — the strong mode)")
    truth = {}
    for i, anum in enumerate(anums):
        try:
            truth[anum] = fetch_bfile_terms(anum)
        except Exception as exc:
            print(f"  {anum}: fetch failed ({type(exc).__name__}) — row will be UNGRADED")
        if i + 1 < len(anums):
            time.sleep(1.0)
    return truth


def grade_frozen(args) -> int:
    with open(args.frozen) as f:
        frozen = json.load(f)
    payload = json.dumps(frozen["rows"], sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    ok_sha = digest == frozen["rows_sha256"]
    print(f"frozen file: engine {frozen['engine']['version']}  "
          f"frozen {frozen['frozen_utc']}  commit {frozen['generated_at_commit'][:10]}")
    print(f"tamper check: recomputed rows sha256 "
          f"{'MATCHES' if ok_sha else 'DOES NOT MATCH'} the recorded one")
    if not ok_sha:
        print("REFUSING to grade a tampered file.")
        return 2

    stamped_rows = [r for r in frozen["rows"] if r["status"] == "VERIFIED"]
    refused = sum(r["status"] == "REFUSED" for r in frozen["rows"])
    truth = load_truth(args, [r["anum"] for r in stamped_rows])

    correct = false_stamps = ungraded = 0
    print(f"\n{'A-number':10s} {'model class':26s} {'graded':>7s}  verdict")
    for r in stamped_rows:
        t = truth.get(r["anum"])
        if not t or len(t) <= 12:
            ungraded += 1
            print(f"{r['anum']:10s} {r.get('model_class','')[:26]:26s} {'-':>7s}  UNGRADED (no ground-truth tail)")
            continue
        shown = r["shown"]
        if t[:12] != shown:
            ungraded += 1
            print(f"{r['anum']:10s} {r.get('model_class','')[:26]:26s} {'-':>7s}  UNGRADED (offset mismatch vs truth source)")
            continue
        tail = t[12:12 + len(r["predicted"])]
        pred = r["predicted"][:len(tail)]
        if pred == tail:
            correct += 1
            print(f"{r['anum']:10s} {r.get('model_class','')[:26]:26s} {len(tail):>4d}/{len(tail):<2d}  externally CORRECT")
        else:
            false_stamps += 1
            k = next(i for i in range(len(tail)) if pred[i] != tail[i])
            print(f"{r['anum']:10s} {r.get('model_class','')[:26]:26s} {'':>7s}  FALSE STAMP at term {13+k}: "
                  f"predicted {pred[k]}, OEIS says {tail[k]}")

    print(f"\n  stamped {len(stamped_rows)}   externally correct {correct}   "
          f"ungraded {ungraded}   refused (honest abstentions) {refused}")
    print(f"  FALSE STAMPS: {false_stamps}   <- the number this eval exists to check")
    print("  RESULT:", "PASS — zero false verifications on external data"
          if false_stamps == 0 else "FAIL — the engine stamped a wrong prediction")
    return 1 if false_stamps else 0


def grade_challenge(args) -> int:
    """Grade author-returned answers to sequences YOU chose (challenge.py)."""
    with open(args.challenge) as f:
        challenge = json.load(f)
    with open(args.answers) as f:
        answers = json.load(f)
    correct = false_stamps = refused = ungraded = 0
    anums = sorted(challenge["sequences"])
    truth = load_truth(args, anums)
    for anum in anums:
        ans = answers.get("rows", {}).get(anum)
        if ans is None or ans.get("status") == "REFUSED":
            refused += 1
            print(f"{anum:10s} REFUSED (honest abstention)")
            continue
        t = truth.get(anum)
        if not t or len(t) < 16:
            ungraded += 1
            print(f"{anum:10s} UNGRADED (no ground truth)")
            continue
        pred = [int(x) for x in ans["predicted"]][:4]
        tail = t[12:16]
        if pred == tail:
            correct += 1
            print(f"{anum:10s} externally CORRECT ({ans.get('model_class','')})")
        else:
            false_stamps += 1
            print(f"{anum:10s} FALSE STAMP: predicted {pred}, OEIS says {tail}")
    print(f"\n  stamped correct {correct}   FALSE STAMPS {false_stamps}   "
          f"refused {refused}   ungraded {ungraded}")
    print("  RESULT:", "PASS" if false_stamps == 0 else "FAIL")
    return 1 if false_stamps else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frozen", default=os.path.join(_HERE, "frozen_predictions.json"))
    ap.add_argument("--cache", help="pinned snapshot instead of live oeis.org")
    ap.add_argument("--challenge", help="challenge file from challenge.py")
    ap.add_argument("--answers", help="author-returned answers for the challenge")
    args = ap.parse_args(argv)
    if args.challenge or args.answers:
        if not (args.challenge and args.answers):
            ap.error("--challenge and --answers go together")
        return grade_challenge(args)
    return grade_frozen(args)


if __name__ == "__main__":
    raise SystemExit(main())
