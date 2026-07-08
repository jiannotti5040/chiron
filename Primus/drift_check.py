#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
drift_check.py — differential testing between the seed and the monolith.

The vault maintains two implementations of the invariant discipline: the
packaged seed (`primus.engine`) and the consolidated production engine
(`../Chiron/chiron.py`). History proved they can drift silently — the seed
once stamped repunits with wrong predictions while Chiron got them exactly
right. This check makes that class of divergence a build failure instead of
a latent embarrassment.

Policy, per surface (first 12 terms shown, both engines predict 4 more):

  CONTRADICTION  both stamp *verified* but predict different continuations
                 → at least one engine is wrong → **hard FAIL**.
  SEED-ONLY      seed stamps, Chiron abstains → **hard FAIL** unless the
                 case is in the documented capability ledger below (the
                 seed is allowed to be *ahead* only on purpose, in writing).
  CHIRON-ONLY    Chiron stamps, seed abstains → reported SKEW (the monolith
                 has more classes; expected), non-fatal.
  AGREE          same stamp decision and, if stamped, identical predictions.

Skips gracefully (exit 0) when ../Chiron/chiron.py is absent (standalone
package checkouts).

    python3 drift_check.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))
from primus.engine import collapse as seed_collapse  # noqa: E402

SHOW, GRADE = 12, 4

# The capability ledger: surfaces where the seed is INTENTIONALLY ahead of
# the monolith. Every entry must say why. Anything seed-only and not listed
# here fails the build.
SEED_AHEAD_LEDGER = {
    # Empty as of 2026-07-04 (later the same day the first entries were
    # written): the order-2 P-recursion margin fix was ported into
    # chiron.py, so Motzkin (A001006) and Schröder (A006318) verify in both
    # engines and their entries cleared. Historical note for honesty: the
    # original ledger text misdiagnosed Chiron's holonomic path as
    # float/SVD; it was already exact (Fraction nullspace) — only its
    # rows >= unknowns + 2 margin, unformable on 9-term holdout prefixes,
    # blocked verification. The ledger mechanism worked exactly as
    # intended either way: divergence went RED, got a written reason, and
    # the reason's repair path cleared it.
}

SYNTHETIC = {
    "fibonacci": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987],
    "squares": [n * n for n in range(16)],
    "cubes": [n ** 3 for n in range(16)],
    "pow2": [2 ** n for n in range(16)],
    "repunits": [(10 ** n - 1) // 9 for n in range(16)],      # the historical bug
    "tribonacci": [0, 0, 1, 1, 2, 4, 7, 13, 24, 44, 81, 149, 274, 504, 927, 1705],
    "neg_ratio_geometric": [5 * (-2) ** n for n in range(16)],
    "oblong": [n * (n + 1) for n in range(16)],
    # A002203 companion Pell — the 2026-07-07 holonomic-overfit false stamp:
    # the seed picked a float holonomic_r1_p2 (predicting 551612) over the exact
    # order-2 linear recurrence, while Chiron was correct. Now in the differential.
    "companion_pell": [2, 2, 6, 14, 34, 82, 198, 478, 1154, 2786, 6726, 16238,
                       39202, 94642, 228486, 551614],
    "random_control": [7, 2, 9, 4, 4, 8, 3, 1, 6, 5, 5, 9, 2, 7, 1, 8],
}


def _predict4(inv, shown_len):
    try:
        return [int(round(float(x))) for x in inv.predict(shown_len + GRADE)[shown_len:]]
    except Exception:
        return None


def main() -> int:
    chiron_dir = os.path.normpath(os.path.join(_HERE, os.pardir, "Chiron"))
    if not os.path.isfile(os.path.join(chiron_dir, "chiron.py")):
        print("drift_check: no sibling Chiron/ — skipping (standalone checkout)")
        return 0
    sys.path.insert(0, chiron_dir)
    import chiron  # noqa: E402

    battery = dict(SYNTHETIC)
    cache = os.path.join(_HERE, "oeis_corpus_cache.json")
    if os.path.isfile(cache):
        with open(cache) as f:
            for anum, meta in json.load(f)["sequences"].items():
                if len(meta["terms"]) >= SHOW + GRADE:
                    battery[anum] = meta["terms"]

    fails, skew, agree = [], [], 0
    for name, terms in sorted(battery.items()):
        shown = terms[:SHOW]
        try:
            s_inv = seed_collapse(shown)
            s_ver = bool(s_inv.verified)
        except Exception:
            s_inv, s_ver = None, False
        try:
            c_inv = chiron.collapse(shown)
            c_ver = bool(c_inv.verified)
        except Exception:
            c_inv, c_ver = None, False

        if s_ver and c_ver:
            sp, cp = _predict4(s_inv, SHOW), _predict4(c_inv, SHOW)
            if sp == cp and sp is not None:
                agree += 1
            else:
                fails.append((name, "CONTRADICTION",
                              f"seed {s_inv.model_class} -> {sp} | "
                              f"chiron {c_inv.model_class} -> {cp}"))
        elif s_ver and not c_ver:
            if name in SEED_AHEAD_LEDGER:
                skew.append((name, "SEED-AHEAD (ledgered)", SEED_AHEAD_LEDGER[name]))
            else:
                fails.append((name, "SEED-ONLY (unledgered)",
                              f"seed stamps {s_inv.model_class}; chiron abstains — "
                              "either the seed over-claims or the ledger needs an "
                              "entry with a reason"))
        elif c_ver and not s_ver:
            skew.append((name, "CHIRON-ONLY", getattr(c_inv, "model_class", "?")))
        else:
            agree += 1          # both abstain — agreement on refusal

    print(f"drift_check: {len(battery)} surfaces — {agree} agree, "
          f"{len(skew)} skew (non-fatal), {len(fails)} FAIL")
    for name, kind, detail in skew:
        print(f"  [SKEW] {name:24s} {kind}: {detail}")
    for name, kind, detail in fails:
        print(f"  [FAIL] {name:24s} {kind}: {detail}")
    if fails:
        print("drift_check: RED — the seed and the monolith disagree where "
              "they must not. Fix the engine or ledger the capability, in "
              "writing, before shipping.")
        return 1
    print("drift_check: GREEN — no contradictions, no unledgered seed claims.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
