# OEIS novelty search — pre-registered protocol

**Author: Jacob Iannotti. Apache-2.0.**
Status: **pre-registration.** Written and committed *before* the sweep results
were read. The stage-1 pre-filter was running in the background as this file
was written; no candidate list had been inspected.

## Why this document exists

A previous attempt at this search produced a **false finding**. The novelty
detector read only OEIS's `formula` field. A279538 has no `formula` field at
all — its *name* is `a(n) = -n^3 + 70*n^2 - 939*n + 2393`. A fully documented,
sixty-year-curated entry was reported as an undocumented discovery.

The error was not the engine's. The engine did exactly what it claims to do:
recover an exact rule and refuse when it cannot. The error was mine, in the
layer that decides what the recovery *means*. Worse, I concluded the whole
direction was dead on the strength of my own broken filter.

So this protocol fixes the process, not the engine:

1. **The hypothesis and the falsification criteria are written before the run.**
2. **The detector is validated against known-documented entries before it is
   trusted** — and the run is abandoned if it fails.
3. **The expected result is stated in advance, and it is zero.**

## Hypothesis

> There exist OEIS sequences for which the engine recovers an exact rule that
> (a) reproduces **every term of a real b-file** and (b) is **not documented
> anywhere in the entry**.

## Pre-registered expectation: ZERO

OEIS has been curated by thousands of contributors for sixty years. That a
14-term recovery finds something genuinely new is a low-probability event.

**A zero result is a result and will be reported as one.** It is not a failure
to be worked around, and it is not a reason to loosen a filter until something
survives. If the honest answer is nothing, the honest report is nothing.

## What would falsify a claimed finding

Any survivor that, on human read, turns out to be documented anywhere in the
entry, or to be structurally trivial. A single such case invalidates the claim.

## Fixed constants — set before the run, never tuned afterward

| constant | value | rationale |
|---|---|---|
| `SHOWN_TERMS` | 14 | what the engine may see |
| `MIN_DATA_TERMS` | 25 | below this no defensible recovery claim exists |
| `MIN_BFILE_GAIN` | 20 | b-file must add real terms beyond `data` |
| `MIN_GROWTH_RATIO` | 10 | flat sequences are where coincidence lives |

## The two traps, both measured rather than assumed

### 1. Synthesized b-files

OEIS returns **HTTP 200** for `/A######/b######.txt` even when no b-file was
ever uploaded — it generates one from the entry's own `data`. In a 120-sequence
sample, **45% were synthetic**, and in **54/54** of those the line count equaled
the `data` term count exactly. **Zero information gain.**

Verifying a recovery against a synthesized b-file means checking the rule
against the same ~40 terms it was fit on, while believing 1000 were checked.
This is exactly how the previous attempt lost 27 of 46 candidates.

Detected two ways: the `synthesized from sequence entry` header, and line count
versus `data` length. Either trigger disqualifies the sequence.

### 2. Formulas outside the `formula` field

The `formula` field is **absent on ~51% of the database**. Among entries
lacking it, a strict formula statement still appears in `name` 8.6% of the
time, `program` 3.7%, `comment` 3.3%, plus `link`, `xref`, `mathematica`.

Checking only `formula` misses **at least ~15% of documented entries**,
concentrated in `name`. That is the A279538 bug, quantified.

## Filter 0 — the gate that makes the previous failure impossible

Before any candidate is examined, the detector must correctly classify a
control set of entries that are **all documented** and **all invisible to a
`formula`-field-only check**:

A279538, A024100, A173652, A162539, A193549, A103487, A353961, A335167,
A292202, A091253, A000045, A000108, A000195.

**Result: 13/13 correctly classified as documented.** Nine of the thirteen have
no `formula` field; the previous detector would have reported all nine as novel
discoveries.

If any control is missed, the run is abandoned and reported as abandoned.

## The filter chain

**Stage 1 — offline, full corpus** (`oeis_offline_prefilter.py`). Runs against
the bulk `stripped.gz` / `names.gz` dumps so no network request is spent on a
sequence that cannot survive. Requires ≥25 terms, growth ≥10, an engine stamp
from 14 terms, and exact reproduction of every bulk term. Drops any sequence
whose *name* states the rule.

**Stage 2 — network, survivors only** (`oeis_novelty.py sweep`):

- **Filter 3 — keyword exclusions.** `cons`/`cofr` (terms are digits of a
  constant), `fini`/`full` (finite; fitting is unfalsifiable), `base`
  (base-10 artifact), `dead` (the data itself is wrong), `bref`, `dumb`,
  `obsc`, `uned` (OEIS's own docs say formulas may be misfiled here, so
  field-position detection is invalid by construction), `frac`, `tabl`/`tabf`
  (a 1-D rule over a linearized triangle is an artifact of reading order),
  `word`.
- **Filter 2 — a real b-file**, per the trap above.
- **Exact recovery** — every b-file term, `==`, no tolerance.
- **Filter 5 — the documentation detector** across `name`, `formula`, `link`,
  `mathematica`, `comment`, `xref`, `example`, `maple`, `program`, in
  descending precision. Ambiguity resolves to *documented*: a false negative
  here becomes a false public claim.
- **Filter 6 — human read by the owner.** Nothing is published and nothing is
  submitted to OEIS without it.

## A note on `keyword:unkn`

OEIS has exactly **31** sequences keyworded `unkn`, defined verbatim as
*"Little is known; an unsolved problem; anyone who can find a formula or
recurrence is urged to add it to the entry."* This is the only keyword that
literally means "no known formula," and it was run as a separate targeted
probe — attractive because it moves the documentation judgment off my regex and
onto OEIS's editors.

**Result: zero survivors, for a structural reason worth recording.** Twenty of
the thirty-one have fewer than 25 terms, and the names explain why: *"The Lost
Numbers"*, *"My teacher gave this as a riddle"*, *"Found on geocaching.com,
can't find the answer"*, *"Sequence from an aptitude test that I cannot work
out!"* `unkn` is not a register of open mathematical problems — it is largely a
junk drawer of unexplained puzzle sequences with too little data to analyze.
Exactly one candidate reached the engine, and the engine refused it.

That is a negative result about the *keyword*, not about the engine, and it is
recorded here so nobody spends this search twice.

## Standing process change

Applied to every future claim in this project:

1. **Literature check first**, written down, before the word "novel" is used.
2. **Pre-register hypothesis and falsification criteria** before running.
3. **Validate the filter against known cases** before trusting its output.
   A279538 is now a permanent regression test.
4. **Default to "my rule is wrong."** Every dramatic result in the session that
   produced this document was my own error, caught late. That prior is now
   explicit.
