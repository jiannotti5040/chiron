#!/usr/bin/env python3
"""
oeis_offline_prefilter.py — stage 1 of the novelty search.

Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0.

Fetching every OEIS entry over the network at OEIS's requested politeness delay
would take ~18 days. This stage runs entirely against the bulk `stripped.gz` and
`names.gz` dumps, so the only sequences that ever cost a network request are the
ones that already survived the engine and the offline documentation checks.

What it does NOT do: decide novelty. A sequence surviving this stage is a
CANDIDATE, not a finding. Stage 2 (oeis_novelty.py sweep) re-fetches the full
entry, demands a REAL b-file (not one OEIS synthesized from `data`), and runs
the full documentation detector over every formula-bearing field.

The holdout here is honest but weak: `stripped` carries a median of ~40 terms,
so showing the engine 14 leaves ~26 held out. That is enough to kill
coincidences, not enough to claim anything -- which is precisely why the real
b-file is mandatory in stage 2.
"""

from __future__ import annotations

import gzip
import re
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "Primus" / "src"))

from oeis_novelty import (  # noqa: E402
    MIN_DATA_TERMS, MIN_GROWTH_RATIO, SHOWN_TERMS, documented, growth_ratio,
)

CACHE = HERE / ".oeis_cache"


# Keywords are not in the bulk dumps, so the keyword gate runs in stage 2.
# What IS available offline is the name -- and the name is exactly where the
# previous attempt was blind, so it is checked here, for free, corpus-wide.
#
# This calls the SAME documented() that Filter 0/0b validated, restricted to
# the name field, rather than a second hand-written regex. That matters: a
# separately-tuned pre-filter could silently drop a sequence stage 2 would
# have kept, and no gate would ever catch it. By construction this drops only
# what stage 2 would drop on name evidence alone.
def name_states_rule(nm):
    return documented({"name": nm})[0]

# Names that mark a structurally trivial class, catchable without keywords.
TRIVIAL_NAME_RE = re.compile(
    r"^\s*(Decimal expansion|Continued fraction|Digits of|Number of digits|"
    r"Triangle read by rows|Array read by|Table read by|Erroneous version|"
    r"Duplicate of|A\d{6} written in base|Numbers in base)", re.I)


def load_names():
    names = {}
    with gzip.open(CACHE / "names.gz", "rt", errors="replace") as fh:
        for line in fh:
            if not line.startswith("A"):
                continue
            a, _, rest = line.partition(" ")
            try:
                names[int(a[1:])] = rest.strip()
            except ValueError:
                continue
    return names


def load_terms():
    out = []
    with gzip.open(CACHE / "stripped.gz", "rt", errors="replace") as fh:
        for line in fh:
            if not line.startswith("A"):
                continue
            a, _, rest = line.partition(",")
            try:
                num = int(a[1:])
                terms = [int(x) for x in rest.split(",") if x.strip()]
            except ValueError:
                continue
            if len(terms) >= MIN_DATA_TERMS:
                out.append((num, terms))
    return out


def probe(item):
    """Run the engine on one sequence. Returns (num, model_class) or None."""
    num, terms = item
    if growth_ratio(terms) < MIN_GROWTH_RATIO:
        return None
    from primus.engine import collapse_numeric
    try:
        inv = collapse_numeric(terms[:SHOWN_TERMS])
    except Exception:
        return None
    if not getattr(inv, "verified", False):
        return None
    try:
        pred = inv.predict(len(terms))
    except Exception:
        return None
    # Must reproduce EVERY term in the bulk record, not just the shown prefix.
    if len(pred) != len(terms) or any(a != b for a, b in zip(pred, terms)):
        return None
    return num, getattr(inv, "model_class", "?")


def main():
    print("=" * 74)
    print("STAGE 1 -- offline pre-filter over the full OEIS bulk corpus")
    print("=" * 74)

    names = load_names()
    print(f"  names.gz      {len(names):,} entries")
    seqs = load_terms()
    print(f"  stripped.gz   {len(seqs):,} entries with >= {MIN_DATA_TERMS} terms")

    print(f"\n  running the engine (show {SHOWN_TERMS}, require exact on all)...")
    with Pool() as pool:
        hits = [r for r in pool.imap_unordered(probe, seqs, chunksize=200) if r]
    print(f"  engine stamped + held out exactly: {len(hits):,}")

    kept, by_name, by_trivial = [], 0, 0
    for num, mc in sorted(hits):
        nm = names.get(num, "")
        if TRIVIAL_NAME_RE.search(nm):
            by_trivial += 1
            continue
        if name_states_rule(nm):
            by_name += 1
            continue
        kept.append((num, mc, nm))

    print(f"  dropped -- name states the rule:      {by_name:,}")
    print(f"  dropped -- structurally trivial name: {by_trivial:,}")
    print(f"\n  CANDIDATES for stage 2: {len(kept):,}")

    out = CACHE / "candidates.txt"
    out.write_text("".join(f"A{n:06d}\n" for n, _, _ in kept))
    (CACHE / "candidates_detail.txt").write_text(
        "".join(f"A{n:06d}\t{mc}\t{nm}\n" for n, mc, nm in kept))
    print(f"  written: {out}")

    from collections import Counter
    print("\n  by recovered family:")
    for mc, c in Counter(mc for _, mc, _ in kept).most_common():
        print(f"    {mc:28s} {c:6,}")


if __name__ == "__main__":
    main()
