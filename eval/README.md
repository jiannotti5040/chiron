# The public eval build — verify zero-false before you pay

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see ../LICENSE.md).**

The strongest outside review of this repo said, correctly: *"the proof of
the thing being sold is behind the thing being sold."* This folder is the
answer. It does not ship the engine. It ships the engine's **outputs** on
a public held-out suite, plus a stdlib-only grader that checks them
against ground truth the author does not control — because *zero false
verifications* is a property of outputs, and outputs can be verified
without source.

## What's here

| File | What it is |
|---|---|
| `frozen_predictions.json` | The seed engine's frozen outputs on 34 live-fetched OEIS sequences: engine saw the FIRST 12 terms of each; every stamp freezes exact predictions for terms **13..20** (eight held-out terms — twice the published protocol); refusals frozen as refusals. Carries engine version, freeze time, generating vault commit, and a payload sha256. |
| `grade.py` | Recomputes the tamper-evidence hash, fetches ground truth (**live from oeis.org** by default), and counts **false stamps** — stamped predictions external data contradicts. Exit 1 on any. |
| `challenge.py` | The buyer-chosen protocol: **you** pick any A-numbers; only their first 12 terms go to the author; returned answers are graded on your machine against live OEIS. |
| `oeis_snapshot_2026-07-07.json` | A pinned public snapshot (with fetch provenance) for offline/CI grading — the weaker mode; live is the point. |

## Run it (two minutes, no purchase, no engine)

```
python3 eval/grade.py                                      # live oeis.org
python3 eval/grade.py --cache eval/oeis_snapshot_2026-07-07.json   # offline
```

Current frozen build (engine 0.6.0, frozen 2026-07-21): **22 stamped,
22 externally correct, 0 false stamps, 12 honest refusals** against both
pinned snapshots. Run the live mode yourself — that sentence is a claim
until you do.

## What this proves, and the one assumption it still carries — stated, not hidden

The freeze is dated and hash-bound to a vault commit, and grading is
against oeis.org, which the author does not control. What a skeptic can
still say: *the author chose the frozen corpus, and b-files are public,
so the tails were knowable before the freeze.* True. Three answers, in
increasing strength:

1. **Breadth of exposure:** every stamp commits to eight consecutive
   held-out terms; a single wrong digit anywhere is a public FAIL baked
   into this repo forever.
2. **Time:** any sequence OEIS extends or corrects after the freeze date
   grades the freeze on data that did not exist when it was made.
3. **`challenge.py` — the assumption remover:** you choose sequences the
   author never named; only 12 terms leave your machine; you grade the
   answers live. A single false stamp on your own chosen sequence
   falsifies the claim outright.

What refusals mean here: the engine refuses sequences outside its
hypothesis classes (primes, partitions, Bell, Thue–Morse...) instead of
guessing. Refusal is the designed behavior — the falsifiable claim is
that **what is stamped is never externally wrong**, not that everything
gets stamped.

What this folder still does not do: it does not let you run the engine on
arbitrary input yourself before licensing. The engine's own gate battery
(the vault tiers in [`../docs/BATTERIES.md`](../docs/BATTERIES.md)) still
runs post-purchase. This eval reduces the pre-purchase gap from "trust
the philosophy" to "verify the headline property on data you choose."
