# External validation addendum — 2026-07-07: a live false verification (seed engine)

**Status: OPEN DEFECT in the seed engine. Not yet fixed. No source of truth was
modified to find it.** This file publishes the miss, per the project's rule that a
falsified-and-repaired story is worth more than an unblemished table.

## What happened

I extended the live-OEIS battery with 7 post-development probes (list fixed
before grading: 5 in-class targets + 2 out-of-class refusal controls), terms
fetched live from oeis.org b-files this session. Corpus:
`Primus/oeis_corpus_extended_2026-07-07.json` (the curated 28 are unchanged;
the 7 new ones are additive).

Grading all 35 through the real harness produced a **VERIFIED+WRONG** — a false
stamp — the invariant this project exists to never violate:

```
A002203 (Companion Pell / Pell-Lucas)   VERIFIED+WRONG   model: holonomic_r1_p2
   predicted [39202, 94642, 228486, 551612]   expected [39202, 94642, 228486, 551614]
n=35   VERIFIED+correct: 24   VERIFIED+WRONG: 1   declined: 9   recovered-unstamped: 1
RESULT: FAIL — the engine stamped a wrong rule
```

The other 6 new probes behaved correctly: pentagonal, Mersenne 2ⁿ−1, powers of 4,
and the √2-convergent numerators all VERIFIED+correct; the two controls σ(n) and
the digits of π were correctly **declined**. The single failure is companion Pell.

## Reproduction (deterministic)

```bash
cd Primus && PYTHONPATH=src python3 -c "from primus.engine import collapse; \
r=collapse([2,2,6,14,34,82,198,478,1154,2786,6726,16238]); \
print(r.model_class, r.structure.get('verified'), [round(float(x),3) for x in list(r.predict(16))[-4:]])"
# -> holonomic_r1_p2 True [39201.989, 94641.922, 228485.619, 551612.45]

cd Primus && PYTHONPATH=src python3 oeis_live.py --cache oeis_corpus_extended_2026-07-07.json
# -> RESULT: FAIL — the engine stamped a wrong rule
```

## Root cause (diagnosed by reading, not analogy)

The seed recovered companion Pell as a **holonomic** rule whose coefficients live
in **float64**. Its prediction carries fractional error (`551612.4498…`), which
*rounds* to an integer that matches the first 15 terms — and the holonomic
holdout **stamped it VERIFIED anyway**. This is the **same defect class as the
original repunit false stamp** (float drift + a holdout that doesn't demand exact
integer equality), but on a **different code path**: the linear-recurrence path
was hardened to exact-Fraction / exact-integer holdout after repunit; the
holonomic/P-recursion path was not fully brought to the same standard, and the
"refuse floats above 2⁵³" guard doesn't fire because these values (~5.5e5) are
small.

Two confirming facts:
- **More evidence fixes it:** with 16 terms the seed correctly **refuses**
  (`verified: False`). The false stamp exists only at the 12-term boundary where
  the spurious holonomic fit clears an insufficiently-exact holdout.
- **Chiron does not have the defect:** `chiron.collapse(same 12 terms)` recovers
  `linear_recurrence_order2` and predicts `551614` exactly. So the flagship is
  correct; the **seed silently drifted behind it** — exactly the repunit pattern
  ("the clean auditable seed drifted behind the monolith").

## Why the drift detector didn't catch it

`A002203` is **not among the drift surfaces**, so the seed-vs-Chiron differential
never compared them on this input. Drift is green (37/37) but blind here. This is
the structural risk the after-action named: two implementations held together only
by the surfaces you happened to list.

## Recommended fix (NOT yet applied — needs your go-ahead)

Mirror the repunit repair on the holonomic path:

1. **Exact-integer holdout on the holonomic/P-recursion stamping path.** Recover
   coefficients as Fractions; require the rule to reproduce the shown integer
   terms *exactly* and predict the held-out terms *exactly*; refuse otherwise.
   A float prediction that merely rounds to the surface must never earn a stamp.
2. **Close the drift blind spot:** add `A002203` (and a couple more
   linear-recurrence-vs-holonomic boundary cases) to the drift surfaces **and**
   to the standing OEIS battery, so this is permanently guarded in both engines.
3. Run the **full battery** (48 stress, certify, fuzz, MCP, `oeis_live`,
   `drift_check`, Chiron selftest) and confirm green before/after; ledger any
   intentional seed/Chiron divergence.

This is a stamping-path change to a public package, so it should be done under the
full gate discipline with your sign-off — not slipped in.

## Consequences for release / launch (updated advice)

- **Do not tag/publish v0.5.0 to PyPI until this is fixed.** Shipping a release
  with a known live false verification would contradict the one claim the project
  can't afford to break.
- **Hold the Show HN** until the fix lands — the draft is ready
  (`SHOW_HN_DRAFT.md`) and its entire hook is zero-false-verification.
- Everything else (Pages, playground, PySR) is unaffected.

---
This file is untracked — keep or fold into `Primus/EXTERNAL_VALIDATION.md` once the
fix lands, as the "falsified again, repaired again" entry.
