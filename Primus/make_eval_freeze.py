#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
make_eval_freeze.py — generate the public eval build's frozen-prediction file.

The enterprise gap, stated by the strongest outside review of the public
repo: "the proof of the thing being sold is behind the thing being sold."
This tool is the vault half of the answer. It runs the seed engine over the
live-fetched public OEIS corpus at the standard protocol (engine sees the
FIRST 12 terms only), and freezes, per sequence:

  VERIFIED  -> the recovered model class and the engine's exact predictions
               for terms 13..20 (EIGHT held-out terms — twice the published
               4-term protocol),
  REFUSED   -> the refusal, recorded as a first-class outcome.

The frozen file ships in the PUBLIC repo (eval/frozen_predictions.json)
with a stdlib-only grader that re-fetches ground truth from oeis.org LIVE
and counts false stamps. The engine never ships; its outputs do — and
zero-false is a property of outputs. Provenance fields (generating commit,
UTC time, payload sha256) make the freeze tamper-evident and datable, so
"the predictions predate the grading" is checkable from git history, and
any sequence OEIS extends after the freeze date is untainted evidence.

    python3 make_eval_freeze.py                # writes eval_freeze.json here
    python3 make_eval_freeze.py --corpus oeis_corpus_extended_2026-07-07.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse  # noqa: E402

SHOW = 12          # terms the engine sees (identical to oeis_live.py)
PREDICT = 8        # frozen held-out predictions: terms 13..20


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=_HERE,
                              capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def freeze_one(anum: str, meta: dict) -> dict:
    terms = meta["terms"]
    row = {"anum": anum, "name": meta.get("name", "")[:60], "shown": terms[:SHOW]}
    if len(terms) < SHOW:
        row.update(status="SKIPPED", reason="fewer than 12 cached terms")
        return row
    try:
        inv = collapse(terms[:SHOW])
    except Exception as exc:
        row.update(status="REFUSED",
                   reason=f"engine declined ({type(exc).__name__})")
        return row
    if not inv.verified:
        row.update(status="REFUSED", model_class=inv.model_class,
                   reason="no exactly-verified generator at 12 shown terms; "
                          "refusing rather than guessing")
        return row
    try:
        raw = inv.predict(SHOW + PREDICT)[SHOW:]
        predicted = [x if isinstance(x, int) else int(round(float(x)))
                     for x in raw]
    except Exception as exc:
        row.update(status="REFUSED",
                   reason=f"stamped rule failed to extend ({type(exc).__name__}); "
                          "refusing the stamp for the freeze")
        return row
    row.update(status="VERIFIED", model_class=inv.model_class,
               predicted_from_term=SHOW + 1, predicted=predicted)
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus",
                    default=os.path.join(_HERE, "oeis_corpus_extended_2026-07-07.json"))
    ap.add_argument("--out", default=os.path.join(_HERE, "eval_freeze.json"))
    args = ap.parse_args(argv)

    with open(args.corpus) as f:
        blob = json.load(f)
    corpus = blob["sequences"]
    provenance = blob.get("_provenance", {})

    rows = []
    for anum, meta in sorted(corpus.items()):
        if not re.fullmatch(r"A\d{6}", anum):
            continue        # protocol-variant pseudo-rows are not gradeable A-numbers
        rows.append(freeze_one(anum, meta))

    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    from primus import __version__
    out = {
        "schema": "primus.eval-freeze/1",
        "engine": {"name": "primus", "version": __version__},
        "protocol": {
            "shown_terms": SHOW,
            "frozen_predictions_per_stamp": PREDICT,
            "statement": ("the engine saw ONLY the first 12 terms of each "
                          "sequence; every stamped row freezes its exact "
                          "predictions for terms 13..20; refusals are frozen "
                          "as refusals"),
        },
        "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_at_commit": _commit(),
        "corpus_provenance": provenance,
        "rows_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "rows": rows,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    stamped = sum(r["status"] == "VERIFIED" for r in rows)
    refused = sum(r["status"] == "REFUSED" for r in rows)
    print(f"froze {len(rows)} rows -> {os.path.relpath(args.out, _HERE)}   "
          f"stamped {stamped}, refused {refused}, "
          f"sha256 {out['rows_sha256'][:16]}…  commit {out['generated_at_commit'][:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
