#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
answer_challenge.py — answer a buyer's eval challenge (the vault half of
the public repo's eval/challenge.py protocol).

A buyer sends challenge.json containing ONLY the first 12 terms of
sequences THEY chose. This tool runs the seed engine on exactly those 12
terms and emits answers.json: VERIFIED + exact predictions for terms
13..16, or REFUSED. Nothing else is consulted — the engine cannot peek,
because 12 terms per sequence is all this file ever reads.

    python3 answer_challenge.py challenge.json          # -> answers.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse  # noqa: E402

SHOW, GRADE = 12, 4


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("challenge")
    ap.add_argument("--out", default="answers.json")
    args = ap.parse_args(argv)

    with open(args.challenge) as f:
        challenge = json.load(f)
    rows = {}
    for anum, terms in sorted(challenge["sequences"].items()):
        shown = [int(t) for t in terms][:SHOW]
        try:
            inv = collapse(shown)
        except Exception as exc:
            rows[anum] = {"status": "REFUSED",
                          "reason": f"engine declined ({type(exc).__name__})"}
            continue
        if not inv.verified:
            rows[anum] = {"status": "REFUSED", "model_class": inv.model_class,
                          "reason": "no exactly-verified generator; refusing "
                                    "rather than guessing"}
            continue
        try:
            raw = inv.predict(SHOW + GRADE)[SHOW:]
            pred = [x if isinstance(x, int) else int(round(float(x)))
                    for x in raw]
        except Exception as exc:
            rows[anum] = {"status": "REFUSED",
                          "reason": f"stamped rule failed to extend "
                                    f"({type(exc).__name__})"}
            continue
        rows[anum] = {"status": "VERIFIED", "model_class": inv.model_class,
                      "predicted": pred}

    from primus import __version__
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    out = {
        "schema": "chiron.eval-answers/1",
        "engine": {"name": "primus", "version": __version__},
        "answered_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "challenge_sha256": hashlib.sha256(
            json.dumps(challenge, sort_keys=True).encode()).hexdigest(),
        "rows_sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "rows": rows,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    stamped = sum(r["status"] == "VERIFIED" for r in rows.values())
    print(f"answered {len(rows)} sequences -> {args.out}   "
          f"stamped {stamped}, refused {len(rows) - stamped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
