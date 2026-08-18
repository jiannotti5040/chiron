# The public eval build — verify zero-false yourself

**Author: Jacob Iannotti. Apache-2.0 (see [../LICENSE](../LICENSE)).**

This folder exists to let a skeptic check the headline property without
taking the author's word for anything — and, originally, without access to
the engine at all. The engine is now Apache-2.0 and you can simply read it
(`pip install primus-intelligence`), so this is no longer the *only* way in.
It remains the sharpest one: it ships the engine's **outputs** on a public
held-out suite, frozen and hash-bound, plus a stdlib-only grader that checks
them against ground truth the author does not control. *Zero false
verifications* is a property of outputs, and outputs can be checked by
someone who trusts neither the code nor the person who wrote it.

## What's here

| File | What it is |
|---|---|
| `frozen_predictions.json` | The seed engine's frozen outputs on 34 live-fetched OEIS sequences: engine saw the FIRST 12 terms of each; every stamp freezes exact predictions for terms **13..20** (eight held-out terms — twice the published protocol); refusals frozen as refusals. Carries engine version, freeze time, generating vault commit, and a payload sha256. |
| `grade.py` | Recomputes the tamper-evidence hash, fetches ground truth (**live from oeis.org** by default), and counts **false stamps** — stamped predictions external data contradicts. Exit 1 on any. |
| `challenge.py` | The buyer-chosen protocol: **you** pick any A-numbers; only their first 12 terms go to the author; returned answers are graded on your machine against live OEIS. |
| `oeis_snapshot_2026-07-07.json` | A pinned public snapshot (with fetch provenance) for offline/CI grading — the weaker mode; live is the point. |

## Run it (two minutes, no install, no engine)

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

What this folder does not do: it does not run the engine for you. It grades
outputs the engine already committed to. To run the engine on arbitrary input
of your own, install it and use the gate battery directly — the vault tiers
are described in [`../docs/BATTERIES.md`](../docs/BATTERIES.md):

```
pip install primus-intelligence
primus certify "2+2=5, 97 is prime"
primus collapse "1 1 2 3 5 8 13 21 34 55 89 144"
```

The same engine is also serveable over HTTP — request in, certificate out,
engine source never serialized — and [`remote.py`](remote.py) is the
stdlib client for it. Start one locally and point the client at it:

```
primus-serve --port 8790 &
python3 eval/remote.py --url http://127.0.0.1:8790 collapse "1 1 2 3 5 8 13 21 34 55 89 144"   # VERIFIED
python3 eval/remote.py --url http://127.0.0.1:8790 collapse "2 3 5 7 11 13 17 19 23 29 31 37"   # refuses
python3 eval/remote.py --url http://127.0.0.1:8790 certify "2+2=5, 97 is prime"
```

`remote.py` works against any deployment, so the mechanism outlives any one
URL. No hosted instance is published here: an endpoint this document cannot
name is an endpoint a reader cannot check, and an unverifiable claim is not
one this repository should make. The frozen evaluation above remains the
dated, hash-bound artifact supporting the 22-stamped claim.
