#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
challenge.py — the buyer-chosen half of the eval protocol.

The frozen-prediction grade (grade.py) carries one residual trust
assumption: the author froze predictions on sequences the author selected,
and OEIS b-files are public, so a determined faker could have peeked at
the tails before freezing. THIS tool removes that assumption: YOU pick the
sequences — any OEIS A-numbers, ones the author has never named — and only
the first 12 terms leave your machine.

Protocol:
  1. python3 challenge.py A007318 A054735 ...      # any A-numbers you like
     -> writes challenge.json containing ONLY {anum: first 12 terms}.
  2. Send challenge.json to the author (email in the repo). The engine
     answers each with VERIFIED + exact predictions for terms 13..16, or
     REFUSED. You get answers.json back. The author never sees more than
     the 12 terms you already chose to send.
  3. python3 grade.py --challenge challenge.json --answers answers.json
     -> grades the stamps against oeis.org LIVE, on your machine.

A false stamp on even one sequence you chose yourself is the claim
falsified. Refusals are not failures — refusal on out-of-class sequences
is the designed behavior; the falsifiable claim is that what IS stamped
is never externally wrong.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone

from grade import fetch_bfile_terms  # same folder, stdlib fetcher


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("anums", nargs="+", help="OEIS A-numbers, e.g. A007318")
    ap.add_argument("--out", default="challenge.json")
    args = ap.parse_args(argv)

    seqs = {}
    for raw in args.anums:
        anum = raw.strip().upper()
        if not re.fullmatch(r"A\d{1,6}", anum):
            print(f"  {raw}: not an A-number — skipped")
            continue
        anum = "A" + anum[1:].zfill(6)
        try:
            terms = fetch_bfile_terms(anum, limit=12)
        except Exception as exc:
            print(f"  {anum}: fetch failed ({type(exc).__name__}) — skipped")
            continue
        if len(terms) < 12:
            print(f"  {anum}: fewer than 12 published terms — skipped")
            continue
        seqs[anum] = terms
        print(f"  {anum}: first 12 terms captured")
        time.sleep(1.0)

    if not seqs:
        print("no usable sequences; nothing written")
        return 1
    out = {
        "schema": "chiron.eval-challenge/1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "protocol": "engine may see ONLY these 12 terms per sequence; "
                    "answers are VERIFIED + predicted terms 13..16, or REFUSED",
        "sequences": seqs,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nwrote {args.out} ({len(seqs)} sequences). Send it to the author; "
          f"grade the returned answers.json with:\n"
          f"  python3 grade.py --challenge {args.out} --answers answers.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
